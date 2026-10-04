"""Claude als Skript-Autor - ueber das Claude-Abo des Nutzers (kein API-Geld).

GEMELDET 04.10.2026: „Ich zahle fuer Claude - wenn es sinnvoll ist, nutz es in
der Pipeline." GEMESSEN: Die Story-Noten mit Gemini Flash blieben meist bei
5-7/10. GEPRUEFT (code.claude.com/docs/en/github-actions): Ein mit
`claude setup-token` erzeugter Token (CLAUDE_CODE_OAUTH_TOKEN) laeuft auch in
zeitgesteuerten GitHub-Laeufen und zaehlt gegen das Abo-Limit, nicht gegen
API-Guthaben. Darum nur fuer das Schreiben (wenige Aufrufe); Pruefen und
Bildauswahl bleiben bei Gemini/Groq.

Faellt Claude aus (Limit, Token abgelehnt, nicht installiert): None - der
Aufrufer schreibt dann wie bisher mit Gemini. Es kommt immer ein Video.
"""
import json, os, re, shutil, subprocess

MODELL = os.environ.get('CLAUDE_MODELL', 'claude-sonnet-5')


def verfuegbar():
    return bool(os.environ.get('CLAUDE_CODE_OAUTH_TOKEN')) and bool(shutil.which('claude'))


def json_aus(text):
    """Das erste vollstaendige JSON-Objekt aus der Antwort (Claude setzt es manchmal in ```json)."""
    m = re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, re.S)
    roh = m.group(1) if m else text[text.find('{'):text.rfind('}') + 1]
    return json.loads(roh)


def schreiben(prompt, schema, zeit=300):
    """Gibt (daten, modell) oder (None, grund) zurueck."""
    if not verfuegbar():
        return None, 'Claude nicht eingerichtet'
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
