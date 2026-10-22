"""Claude als Skript-Autor - ueber das Claude-Abo des Nutzers (kein API-Geld).

GEMELDET 04.10.2026: „Ich zahle fuer Claude - wenn es sinnvoll ist, nutz es in
der Pipeline." GEMESSEN: Die Story-Noten mit Gemini Flash blieben meist bei
5-7/10. GEPRUEFT (code.claude.com/docs/en/github-actions): Ein mit
`claude setup-token` erzeugter Token (CLAUDE_CODE_OAUTH_TOKEN) laeuft auch in
zeitgesteuerten GitHub-Laeufen und zaehlt gegen das Abo-Limit, nicht gegen
API-Guthaben. Darum nur fuer das Schreiben (wenige Aufrufe); Pruefen und
Bildauswahl bleiben bei Gemini/Groq.

Faellt Claude aus (Limit, Token abgelehnt, nicht installiert): None - der
Aufrufer versucht dann Gemini/Groq. Alle Fakten- und Qualitaetspruefungen bleiben bestehen.
"""
import datetime, json, os, re, shutil, subprocess
from pathlib import Path

# GEMESSEN 07.10.2026 mit CLI 2.1.292: 'claude-sonnet-5' antwortet zwar, ist aber das
# aeltere Modell; der Alias 'sonnet' loest auf das neueste Sonnet auf (claude-sonnet-5-5).
MODELL = os.environ.get('CLAUDE_MODELL', 'sonnet')
# Ein Fehlschlag (Abo-Limit, Token, Zeitlimit) wiederholt sich im selben Lauf fast
# immer. Ohne Sperre kostete jeder der bis zu 4 Schreibversuche erneut bis zu 240 s -
# genau die Zeitfalle, an der am 07.10. das AI-Budget ohne Video verbraucht wurde.
_gesperrt = None
LIMIT = Path('verlauf/claude-limit.json')


def pause(jetzt=None):
    """Bekanntes Abo-Limit prozessuebergreifend beachten; nach Ablauf wieder versuchen."""
    try:
        if not LIMIT.exists():
            return None
        d = json.loads(LIMIT.read_text(encoding='utf-8'))
        ende = datetime.datetime.fromisoformat(d['gesperrt_bis_utc'].replace('Z', '+00:00'))
        if ende.tzinfo is None:
            raise ValueError('Zeitzone fehlt')
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return 'Claude-Limitdatei ungueltig; anderer Autor wird verwendet'
    jetzt = jetzt or datetime.datetime.now(datetime.timezone.utc)
    return 'Claude wegen bekanntem Abo-Limit pausiert bis ' + ende.isoformat() if jetzt < ende else None


def verfuegbar():
    return _gesperrt is None and pause() is None and bool(os.environ.get('CLAUDE_CODE_OAUTH_TOKEN')) and bool(shutil.which('claude'))


def json_aus(text):
    """Das erste vollstaendige JSON-Objekt aus der Antwort (Claude setzt es manchmal in ```json)."""
    m = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.S)
    roh = m.group(1) if m else text[text.find('{'):text.rfind('}') + 1]
    return json.loads(roh)


def schreiben(prompt, schema, zeit=300):
    """Gibt (daten, modell) oder (None, grund) zurueck."""
    if _gesperrt:
        return None, _gesperrt
    grund = pause()
    if grund:
        import stoerung
        stoerung.melden('claude', f'Claude schreibt gerade keine Skripte ({grund}).',
                        'Gemini/Groq schreiben als Reserve; alle Pruefungen bleiben gleich.')
        return None, grund
    if not verfuegbar():
        return None, 'Claude nicht eingerichtet'
    daten, grund = _schreiben(prompt, schema, zeit)
    if daten is None:
        sperren(grund)
        limit_merken(grund)
    return daten, grund


LIMIT_TEXT = re.compile(r'usage limit|limit reached|rate limit|weekly limit|5-hour limit|out of (?:extra )?usage', re.I)


def limit_ende(grund, jetzt=None):
    """Ruecksetzzeit aus der Claude-Limitmeldung (UTC) oder eine vorsichtige Schaetzung; None ohne Limit.
    Formate: „Claude AI usage limit reached|1760457600" (Unix-Zeit) oder „... resets Oct 14, 5pm (UTC)"."""
    if not LIMIT_TEXT.search(grund or ''):
        return None
    jetzt = jetzt or datetime.datetime.now(datetime.timezone.utc)
    m = re.search(r'\|(\d{10})\b', grund)
    if m:
        ende = datetime.datetime.fromtimestamp(int(m.group(1)), datetime.timezone.utc)
        if jetzt < ende <= jetzt + datetime.timedelta(days=8):
            return ende
    # Ohne lesbare Zeit: Wochenlimit eine Stunde, 5-Stunden-Limit 30 Min. pausieren, dann neu versuchen -
    # lieber ein kurzer Fehlversuch mehr als einen Tag lang auf Claude verzichten.
    return jetzt + datetime.timedelta(minutes=60 if re.search(r'week', grund, re.I) else 30)


def limit_merken(grund, jetzt=None):
    """GEMESSEN 11.-14.10.2026: Wochenlimit erreicht, aber nichts merkte es - jeder Lauf versuchte Claude erneut,
    und der Nutzer erfuhr nicht, dass auch seine eigenen Claude-Sitzungen betroffen sind. Jetzt: Pause in
    verlauf/claude-limit.json (wird mit dem Verlauf gesichert) und eine Telegram-Warnung."""
    ende = limit_ende(grund, jetzt)
    if ende is None:
        return None
    LIMIT.parent.mkdir(parents=True, exist_ok=True)
    LIMIT.write_text(json.dumps({'gesperrt_bis_utc': ende.strftime('%Y-%m-%dT%H:%M:%SZ'),
                                 'grund': 'Claude-Abo-Limit gemeldet: ' + (grund or '')[:160]},
                                ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    try:
        import stoerung
        berlin = ende.astimezone(datetime.timezone(datetime.timedelta(hours=1 if ende.month in (11, 12, 1, 2, 3)
                                                                       else 2)))
        stoerung.melden('claude-limit', f'Claude-Abo-Limit erreicht (frei ab ca. {berlin:%d.%m. %H:%M} Uhr).',
                        'Gemini/Groq schreiben die Skripte, alle Pruefungen bleiben. Auch deine eigenen '
                        'Claude-Sitzungen teilen dieses Limit.')
    except Exception:
        pass
    return ende


def sperren(grund):
    """Fuer den Rest dieses Prozesses abschalten (auch bei unbrauchbarer Antwort)."""
    global _gesperrt
    _gesperrt = f'Claude in diesem Lauf abgeschaltet nach: {grund}'


def _schreiben(prompt, schema, zeit):
    auftrag = (prompt + '\n\nAnswer with ONLY one JSON object (no explanation, no markdown) that matches this '
               'JSON schema (Gemini notation, types in capitals):\n' + json.dumps(schema, ensure_ascii=False))
    try:
        r = subprocess.run([shutil.which('claude'), '-p', '--model', MODELL, '--output-format', 'json', '--max-turns', '1'],
                           input=auftrag, capture_output=True, text=True, encoding='utf-8', timeout=zeit,
                           # Nur der Abo-Token, nie ein evtl. gesetzter API-Schluessel (der kostet Geld)
                           env={**os.environ, 'ANTHROPIC_API_KEY': ''})
        d = json.loads(r.stdout)
        if d.get('is_error'):
            return None, f"Claude-Fehler: {str(d.get('result'))[:160]}"
        return json_aus(d['result']), MODELL
    except Exception as e:
        return None, f'Claude nicht nutzbar: {str(e)[:160]}'
