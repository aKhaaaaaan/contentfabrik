"""Skript-Baustein: Kanal-Einstellung -> Thema -> Skript -> Faktenpruefung.

Schreibt ein Skript im Format, das fabrik/bauen.py versteht.
KI: Google Gemini, kostenloses Kontingent (Schluessel GEMINI_API_KEY).

Aufruf:  python fabrik/skript.py kanaele/ai-tools-explained.json skripte/heute.json [thema]
"""
import json, os, re, sys, time, urllib.error, urllib.request, datetime
from pathlib import Path
import prompts
import dramaturgie
import ki_speicher
from qualitaet import skript_gruende, redaktion, rang, STORY_KATEGORIEN

# GEPRUEFT 02.10.2026: gemini-2.5-flash ist fuer neue Konten gesperrt (404);
# gemini-3.8-flash und gemini-flash-latest antworten (200).
# Bei Ueberlastung (503, gemessen bei 3.8-flash) sofort das naechste Modell.
# GEMESSEN 04.10.2026 im konkreten Projekt: mehrere Tageslimits bei 20,
# einige Modelle nicht freigeschaltet. Keine allgemeine Gratis-Grenze:
# Quoten gelten pro Projekt; Aliase sind keine unabhaengigen Kontingente.
MODELLE = ['gemini-3.8-flash', 'gemini-flash-latest', 'gemini-3.7-flash', 'gemini-3.6-flash', 'gemini-3.5-flash',
           'gemini-3-flash-preview', 'gemini-flash-lite-latest', 'gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
# Bildauswahl (eine Anfrage je Abschnitt, ~10 je Video): schnelle Lite-Modelle
# zuerst, damit die starken Modelle fuer Skript und Pruefung uebrig bleiben.
SEHEN = ['gemini-flash-lite-latest', 'gemini-3.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-3.6-flash',
         'gemini-3.5-flash', 'gemini-flash-latest']


VERBRAUCH = {}  # modell -> [anfragen, tokens_rein, tokens_raus]
WIEDERVERWENDET = 0


def _verbrauch_melden():
    if VERBRAUCH:
        print('Gemini-Verbrauch: ' + '; '.join(f'{m}: {a} Anfragen, {r // 1000}k rein, {o // 1000}k raus'
                                               for m, (a, r, o) in VERBRAUCH.items()))
    if WIEDERVERWENDET:
        print(f'KI-Pruefungen wiederverwendet: {WIEDERVERWENDET} (keine neue API-Anfrage)')


import atexit  # noqa: E402
atexit.register(_verbrauch_melden)


def gemini(prompt, schema, temperatur=None, bilder=(), modelle=None, dateien=(), cache=None, fallback_prompt=None):
    """Text darf im Tageslauf ausweichen; Medien bleiben beim echten Vision-Modell."""
    kwargs = dict(temperatur=temperatur, bilder=bilder, modelle=modelle, dateien=dateien, cache=cache)
    fallback = os.environ.get('CF_TEXT_FALLBACK') == 'groq' and not bilder and not dateien
    try:
        return _gemini(prompt, schema, **kwargs, anfrage_s=12 if fallback else 180)
    except RuntimeError as e:
        if not fallback or 'abgelehnt' in str(e):
            raise
    import autorenvergleich as av
    prompt = fallback_prompt if fallback_prompt is not None else prompt
    global WIEDERVERWENDET
    modell = 'groq:' + av.GROQ_MODELL
    key = ki_speicher.cache_key(prompt, schema, [modell], temperatur, cache) if cache else None
    treffer = ki_speicher.cache_lesen(key, schema, [modell]) if key else None
    if treffer:
        WIEDERVERWENDET += 1
        return treffer
    if float(os.environ.get('CF_SCHRITT_ENDE', 'inf')) <= time.monotonic():
        raise RuntimeError('Text-Ausweichweg: Schrittfrist erreicht')
    if not os.environ.get('GROQ_API_KEY'):
        raise RuntimeError('Text-Ausweichweg: Groq-Zugang fehlt')
    ende = min(time.monotonic() + 90, float(os.environ.get('CF_SCHRITT_ENDE', 'inf')))
    print('Text-Ausweichweg: Groq GPT-OSS; Fakten- und Qualitaetsgates bleiben bestehen', flush=True)
    # GPT-OSS rechnet interne Reasoning-Tokens ins Completion-Limit ein,
    # auch bei include_reasoning=False. Die reale Reparatur mit 2048 war unvollstaendig.
    ausgabe = 1536 if any(k in schema.get('properties', {}) for k in ('probleme', 'schwaechen')) else 3072
    try:
        antwort, _, _ = av.groq(prompt, schema, ausgabe_tokens=ausgabe, deadline=ende)
    except (RuntimeError, ValueError, OSError) as e:
        raise RuntimeError('Text-Ausweichweg nicht verfuegbar: ' + av.fehlertext(e)) from None
    if not ki_speicher.schema_ok(antwort, schema):
        raise RuntimeError('Text-Ausweichweg lieferte kein vollstaendiges Schema')
    if key:
        try:
            ki_speicher.cache_schreiben(key, antwort, modell, schema)
        except OSError:
            print('Text-Pruefcache nicht gesichert; frisches Ergebnis bleibt erhalten')
    return antwort, modell


def _gemini(prompt, schema, temperatur=None, bilder=(), modelle=None, dateien=(), cache=None, anfrage_s=180):
    """bilder: JPEG-Bytes, die die KI mit ansieht (Clip-Auswahl in bauen.py).
    modelle: eigene Reihenfolge, z. B. das schnelle Lite-Modell zuerst."""
    import base64
    global WIEDERVERWENDET
    schluessel = os.environ['GEMINI_API_KEY']
    modelle = list(modelle or MODELLE)
    if cache not in (None, 'fakten', 'story') or (cache and (bilder or dateien)):
        raise ValueError('Cache nur fuer explizite Fakten-/Storypruefungen ohne Medien')
    key = ki_speicher.cache_key(prompt, schema, modelle, temperatur, cache) if cache else None
    treffer = ki_speicher.cache_lesen(key, schema, modelle) if key else None
    if treffer:
        WIEDERVERWENDET += 1
        return treffer
    # Eine Anfrage darf nicht neun Modelle mit je zwei langen Timeouts abwarten.
    ende = min(time.monotonic() + anfrage_s,
               float(os.environ.get('CF_SCHRITT_ENDE', 'inf')))
    def bildteil(b):
        mime = ('image/png' if b.startswith(b'\x89PNG\r\n\x1a\n') else
                'image/webp' if b[:4] == b'RIFF' and b[8:12] == b'WEBP' else 'image/jpeg')
        return {'inline_data': {'mime_type': mime, 'data': base64.b64encode(b).decode()}}
    # Medien zuerst, anschliessend der konkrete Auftrag (Gemini-Medienleitfaden).
    teile = ([bildteil(b) for b in bilder]
             + [{'file_data': {'mime_type': m, 'file_uri': u}} for m, u in dateien]
             + [{'text': prompt}])
    koerper = {
        'contents': [{'parts': teile}],
        'generationConfig': {'responseMimeType': 'application/json',
                             'responseSchema': schema},
    }
    letzter = None
    for modell in modelle:
        gesperrt = ki_speicher.sperre(schluessel, modell)
        if gesperrt:
            letzter = f'{modell}: {gesperrt}'
            continue
        # Google empfiehlt fuer Gemini 3.x die Sampling-Standardwerte.
        # Latest-Aliase koennen ebenfalls auf 3.x zeigen: nicht heruntersetzen.
        koerper['generationConfig'].pop('temperature', None)
        if temperatur is not None and not modell.startswith('gemini-3') and 'latest' not in modell:
            koerper['generationConfig']['temperature'] = temperatur
        for versuch in range(2):
            rest = ende - time.monotonic()
            if rest <= 0:
                raise RuntimeError('KI-Zeitbudget fuer diese Anfrage erreicht')
            try:
                print(f'KI-Anfrage: {modell}; Versuch {versuch + 1}', flush=True)
                req = urllib.request.Request(
                    f'https://generativelanguage.googleapis.com/v1beta/models/{modell}:generateContent?key={schluessel}',
                    data=json.dumps(koerper).encode(), headers={'Content-Type': 'application/json'})
                d = json.load(urllib.request.urlopen(req, timeout=min(45, rest)))
                # GEMELDET: „In der Pipeline sparsam mit Tokens sein" - erst messen:
                # Anfragen und Tokens je Modell, Ausgabe am Ende jedes Laufs.
                n = d.get('usageMetadata', {})
                z = VERBRAUCH.setdefault(modell, [0, 0, 0])
                z[0] += 1; z[1] += n.get('promptTokenCount', 0); z[2] += n.get('candidatesTokenCount', 0)
                kandidat = d['candidates'][0]
                if kandidat.get('finishReason', 'STOP') != 'STOP':
                    raise ValueError('KI-Antwort unvollstaendig oder gesperrt')
                # Thought-Parts sind kein JSON-Pruefresultat.
                text = ''.join(p.get('text', '') for p in kandidat['content']['parts'] if not p.get('thought'))
                ergebnis = json.loads(text)
                if not ki_speicher.schema_ok(ergebnis, schema):
                    raise ValueError('KI-Antwort entspricht nicht dem erforderlichen Schema')
                if key:
                    try:
                        ki_speicher.cache_schreiben(key, ergebnis, modell, schema)
                    except OSError:
                        print('KI-Pruefcache konnte nicht gespeichert werden; Ergebnis bleibt frisch geprueft')
                return ergebnis, modell
            except Exception as e:  # Kontingent/Netz: kurz warten, dann naechster Versuch
                print(f'KI-Anfrage fehlgeschlagen: {modell}; {type(e).__name__}', flush=True)
                # Kein roher API-Fehler: URLs/Antworttexte koennen Zugangsdaten enthalten.
                letzter = f'{modell}: {type(e).__name__}'
                if isinstance(e, TimeoutError):
                    ki_speicher.sperren(schluessel, modell, 'Netzwerk-Zeitlimit', 60)
                    break  # Nicht denselben haengenden Anbieter sofort erneut abwarten.
                koerper_fehler = ''
                if isinstance(e, urllib.error.HTTPError):
                    try:
                        koerper_fehler = e.read().decode(errors='replace')
                    except Exception:
                        pass
                # Tageskontingent leer: Warten hilft bis Mitternacht (Pazifik) nicht - naechstes Modell
                if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                    ki_speicher.sperren(schluessel, modell, 'Modell nicht verfuegbar', 86400)
                    letzter = f'{modell}: Modell nicht verfuegbar'
                    break
                if isinstance(e, urllib.error.HTTPError) and e.code == 429 \
                        and re.search(r'per[ _]?day', koerper_fehler, re.I):
                    ki_speicher.sperren(schluessel, modell, 'Tageskontingent erschoepft')
                    letzter = f'{modell}: Tageskontingent erschoepft'
                    break
                if isinstance(e, urllib.error.HTTPError) and e.code == 503:
                    ki_speicher.sperren(schluessel, modell, 'voruebergehend ueberlastet', 300)
                    break  # Ueberlast: naechstes Modell, nicht dieselbe Anfrage erneut aufhalten
                if isinstance(e, urllib.error.HTTPError) and e.code in (400, 401, 403):
                    raise RuntimeError(f'Gemini-Anfrage abgelehnt (HTTP {e.code}); keine blinden Wiederholungen') from None
                if isinstance(e, urllib.error.HTTPError) and e.code == 429:
                    # Minuten-/Tokenlimit: genau einmal befristet warten, dann Modell kuehlen.
                    if versuch:
                        ki_speicher.sperren(schluessel, modell, 'Minuten-/Tokenkontingent erschoepft', 60)
                        letzter = f'{modell}: Minuten-/Tokenkontingent erschoepft'
                        break
                    pause = 60
                    try:
                        pause = max(1, float(e.headers.get('Retry-After', 60)))
                    except (ValueError, TypeError, AttributeError):
                        pass
                    if pause > 60 or pause + 5 >= ende - time.monotonic():
                        ki_speicher.sperren(schluessel, modell, 'Minuten-/Tokenkontingent erschoepft', min(pause, 3600))
                        break
                    time.sleep(pause)
                elif versuch == 0:
                    if ende - time.monotonic() <= 5:
                        raise RuntimeError('KI-Zeitbudget fuer diese Anfrage erreicht') from None
                    time.sleep(5)
    raise RuntimeError(f'Gemini nicht erreichbar: {letzter}')


SKRIPT_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'thema': {'type': 'STRING'},
        'titel_zeile1': {'type': 'STRING'},
        'titel_zeile2': {'type': 'STRING'},
        'schluesselwoerter': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'teile': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
            'platz': {'type': 'INTEGER'}, 'name': {'type': 'STRING'},
            'suche': {'type': 'STRING'}, 'text': {'type': 'STRING'}, 'quelle_url': {'type': 'STRING'},
            'szene': {'type': 'STRING'},
            'bildtext': {'type': 'STRING'},
            'geraeusch': {'type': 'STRING'},  # optional: echtes Umgebungsgeraeusch der Szene
            'beat': {'type': 'STRING', 'enum': ['hook', 'frage', 'beleg', 'erklaerung', 'wendung', 'aufloesung']},
            'bildmodus': {'type': 'STRING', 'enum': ['auto', 'foto', 'stock', 'illustration', 'karte']}},
            'required': ['suche', 'text']}},
        'beschreibung': {'type': 'STRING'},
        'hashtags': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'musik_suche': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
    },
    'required': ['thema', 'titel_zeile1', 'titel_zeile2', 'schluesselwoerter', 'teile', 'beschreibung', 'hashtags'],
}

PRUEF_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'ok': {'type': 'BOOLEAN'},
        'probleme': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
    },
    'required': ['ok', 'probleme'],
}


def hinweise(kanal, thema):
    """Konzept 2f: Vorbilder (YouTube-Ausreisser), Tagestrends und - fuer
    Kanaele mit nur_quellen - die EINZIGEN erlaubten Fakten. Jede Quelle darf
    ausfallen; dann schreibt die KI ohne sie."""
    import trends
    text, quellen = '', []
    if not thema:
        vorbilder = trends.youtube_ausreisser(kanal.get('trend_suche', []))
        if vorbilder:
            text += ('\nShorts in this niche that are outperforming RIGHT NOW (views, x = times their channel average). '
                     # GEMELDET: Themen aus viralen Videos uebernehmen. Thema/Fakten sind frei -
                     # der TEXT anderer (Transkript) ist geschuetzt und YouTube bestraft
                     # „wiederverwendete Inhalte": gleiches Thema ja, eigene Quelle + eigene Worte.
                     'PROVEN TOPICS: you MAY pick the same subject as one of these if our own source covers it - '
                     'tell it in your own words with your own angle; never copy their wording, structure or title:\n'
                     + '\n'.join(f"- {v['titel']} ({v['aufrufe']:,} views, {v['faktor']}x)" for v in vorbilder) + '\n')
        gefragt = trends.google_trends()
        if gefragt:
            text += ('\nToday\'s Google search trends (US). Only use one if it fits this niche naturally, otherwise ignore:\n- '
                     + '\n- '.join(gefragt[:12]) + '\n')
    if kanal.get('nur_quellen'):
        # GEMESSEN: Ohne aktuelle Quellen fiel „Top 5 AI Video Tools" zweimal
        # durch die Faktenpruefung (veraltetes Wissen). Darum nur Belegtes.
        quellen = (trends.ki_quellen(maximal=1) if kanal.get('format') == 'erklaerung'
                   else trends.ki_quellen())
        if kanal.get('format') == 'erklaerung':
            # Eine ausfuehrlich belegte Anwendung statt dreier Repos und langer Sternelisten.
            quellen = [q for q in quellen if q.get('belegt')][:1]
        if kanal.get('format', 'ranking') == 'ranking':
            quellen = rangliste(quellen, kanal)
        if quellen:
            text += ('\nSOURCES fetched today. Every factual claim MUST come from these sources; mention nothing that is '
                     'not in them:\n' + '\n'.join(f"- [{q['quelle']}] {q['name']} ({q['url']}): {q['text']}"
                                                  for q in quellen) + '\n')
        plaetze = rangliste(quellen, kanal)
        if quellen and kanal.get('format', 'ranking') == 'ranking' and plaetze:
            text += ('\nFIXED RANKING - use exactly these entries with exactly these ranks, no others:\n'
                     + '\n'.join(f"#{n} {q['name']} ({q['url']})" for n, q in enumerate(plaetze, 1)) + '\n')
    print(f"Hinweise: {text.count(chr(10) + '- ')} Zeilen, davon {len(quellen)} Quellen")
    return text, quellen


def rangliste(quellen, kanal):
    """Nur ausreichend belegte Tools und genau eine vergleichbare Kennzahl.
    Die Auswahl ist keine weltweite Bestenliste oder eigene Leistungsmessung."""
    n = kanal.get('plaetze', [5, 7])[1]
    if dramaturgie.videoformat(kanal) == 'short':
        n = min(n, 3)
    gruppen = {}
    for q in quellen:
        if q.get('zahl') is not None and q.get('belegt'):
            gruppen.setdefault(q['quelle'], []).append(q)
    if not gruppen:
        return []
    quelle = max(gruppen, key=lambda k: (len(gruppen[k]), k == 'Hugging Face'))
    return sorted(gruppen[quelle], key=lambda q: -q['zahl'])[:n]


def zuordnen(entwurf, quellen):
    """GEMESSEN: Die KI schrieb „Hugging Face - Lightricks/LTX-2.5" statt der
    Adresse - dann fehlte das passende Bild. Darum im Code zuordnen: Steht der
    Name einer Quelle im Feld, im Namen oder im Text, gilt deren Adresse."""
    for t in entwurf['teile']:
        if t.get('platz') and not str(t.get('quelle_url', '')).startswith('http'):
            heuhaufen = ' '.join(str(t.get(k, '')) for k in ('quelle_url', 'name', 'text')).lower()
            treffer = [q for q in quellen if q.get('url') and (q['name'].lower() in heuhaufen or
                                                                q['name'].split('/')[-1].lower() in heuhaufen)]
            t['quelle_url'] = max(treffer, key=lambda q: len(q['name']))['url'] if treffer else ''


STORY_KATEGORIEN = {
    'hook': 'does the first sentence create a curiosity gap, contradiction or concrete promise within 3 seconds?',
    'spannung': 'is there an open question or tension that keeps people watching until the end?',
    'ueberraschung': 'at least one genuine "I did not know that" moment?',
    'tempo': 'does every part give a reason to keep watching - no filler, no repetition?',
    'aufloesung': 'does the ending pay off what the hook promised?',
    'teilbarkeit': 'would a normal viewer send this to a friend or save it?',
}
STORY_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'note': {'type': 'INTEGER'},
        'kategorien': {'type': 'OBJECT', 'properties': {k: {'type': 'INTEGER'} for k in STORY_KATEGORIEN},
                       'required': list(STORY_KATEGORIEN)},
        'schwaechen': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'besserer_hook': {'type': 'STRING'},
    },
    'required': ['note', 'kategorien', 'schwaechen', 'besserer_hook'],
}


def story_bewerten(entwurf):
    """GEMELDET: „Es bringt nichts, wenn ein Video hochqualitativ ist, aber die
    Story floppt." Bewertet NUR die Geschichte (Halten bis zum Ende) - vor dem
    teuren Video-Bau. Eine redaktionelle Note ist keine Zuschauerprognose."""
    text = '\n'.join(t['text'] for t in entwurf['teile'])
    erg, _ = gemini(prompts.story(text, STORY_KATEGORIEN,
                                  ' / '.join(entwurf['titel']) if isinstance(entwurf.get('titel'), list) else
                                  f'{entwurf.get("titel_zeile1", "")} / {entwurf.get("titel_zeile2", "")}',
                                  dramaturgie.videoformat(entwurf)),
                    STORY_SCHEMA, temperatur=0.2, cache='story')
    return erg


CTA = re.compile(r'be sure to like|like,?\s*(?:and\s*)?share|share,?\s*(?:and\s*)?save', re.I)


def ohne_cta_einwand(p):
    """Einwaende gegen den Pflicht-Aufruf (Like/Teilen/Speichern) aus der Faktenpruefung nehmen.

    GEMESSEN 08.10.2026 (Lauf 37757439013): Der Pruefer meldete „Be sure to like, share
    and save this video." als 'Source mismatch' - jede verbesserte Story-Fassung fiel
    dadurch durch, das Skript blieb bei Aufloesung 6/10 und wurde gesperrt. Der Aufruf
    ist Nutzervorgabe, keine Tatsachenbehauptung. Nur Einwaende, deren beanstandete
    Stelle der Aufruf ist, fallen weg; andere Fehler bleiben.
    """
    probleme = p.get('probleme') or []
    rest = [x for x in probleme if not CTA.search(str(x)[:200])]
    if len(rest) == len(probleme):
        return p
    print('Faktenpruefung: Pflicht-Aufruf (Like/Teilen/Speichern) ist keine Tatsachenbehauptung - Einwand ignoriert')
    return dict(p, probleme=rest, ok=bool(p.get('ok')) or not rest)


def wortrate(kanal):
    """Gesprochene Woerter pro Sekunde der Erzaehlstimme (Kanalprofil, sonst kanalstandard).

    GEMESSEN 08.10.2026 (Lauf 37749486997): Gemini Orus sprach 207 Woerter in 109-110 s
    (~1.9 W/s) - trotz Tempo x1.15 noch 95 s statt hoechstens 90 s.
    """
    from kanalstandard import STANDARD
    grund = STANDARD['woerter_pro_sekunde']
    wert = kanal.get('woerter_pro_sekunde', grund)
    return wert if isinstance(wert, (int, float)) and not isinstance(wert, bool) and 1.5 <= wert <= 3 else grund


def anweisung(kanal, thema, frueher):
    import prompts
    lmin, lmax = dramaturgie.laengen(kanal)
    # Muss zur Pruefgrenze in main() passen (Short 2.4), sonst schreibt der Autor zu lang
    # und jede Fassung wird verworfen.
    rate = wortrate(kanal)
    # Seit 08.10.2026 gleiche Regel fuer Short UND Langvideo: Orus spricht beide (vorher
    # Langvideo fest 2.35-2.65 W/s fuer Kokoro -> 10 Min. Text waeren mit Orus ~13 Min.).
    wmin, wmax = (2.75 * rate / 2.4, rate)
    woerter = f'{int(lmin * wmin)}-{int(lmax * wmax)}'
    winkel = kanal.get('winkel', [])
    blick = kanal.get('_winkel') or (winkel[datetime.date.today().toordinal() % len(winkel)] if winkel else '')
    return prompts.skript(kanal, thema, frueher, blick, woerter)


def groq_skriptauftrag(kanal, thema, quellen, auftrag, mindest, hoechstens):
    """Gleiche Quellen und konkrete Reparaturen, ohne lange technische Renderer-Regie."""
    korrektur, entwurf = '', None
    marker = next((m for m in ('\nHere is a draft.', '\nREWRITE for a stronger story') if m in auftrag), None)
    if marker:
        tail = auftrag[auftrag.index(marker):]
        m = re.search(r'\n(?:CURRENT DRAFT[^\n]*|DRAFT):?\n(\{.*)$', tail, re.S)
        if m:
            entwurf = json.loads(m[1])
            korrektur = tail[:m.start()]
            entwurf = {k: entwurf[k] for k in ('thema', 'titel_zeile1', 'titel_zeile2',
                       'beschreibung', 'teile') if k in entwurf}
            # Reparaturen beziehen sich auf Behauptungen/Erzaehlung. Die neue
            # Bildregie folgt diesem Text; alte Szenen nicht erneut einsenden.
            entwurf['teile'] = [{k: t[k] for k in ('text', 'platz', 'name')
                                 if k in t} for t in entwurf['teile']]
    ranking = kanal.get('format', 'ranking') == 'ranking'
    struktur = ('Strict countdown using only the supplied sources and their fixed ranks.' if ranking else
                'One real obstacle, response and consequence; no invented crisis or emotions.'
                if kanal.get('format') == 'geschichte' else
                'One everyday problem, one documented tool, practical steps, supported use and honest limitation; '
                'make the frustration and the payoff felt (human stakes, factual).')
    cta = ('Speak exactly TWO concise like/share/save requests: after first useful context within '
           '20-30 seconds and after the ending payoff; never before the hook.' if
           dramaturgie.videoformat(kanal) == 'lang' else
           'After the final payoff speak exactly ONCE: Be sure to like, share and save this video.')
    return (prompts.DATEN + prompts.FAKTEN + prompts.SPRECHEN
        + f'Write an original English video in {mindest}-{hoechstens} spoken words. '
        + ('Use 24-50 unranked beats. ' if dramaturgie.videoformat(kanal) == 'lang' else
           'Use 9 short beats of 22-24 spoken words each (198-216 total). Count narration only. ')
        + struktur + ' First sentence max 9 words; answer the hook before the final request. '
        + cta + ' Include CTA words in the narration budget. Each suche: 2-4 concrete English search words. '
          'Each szene: 20-25 words, visible subject/action, era, setting, framing and light; matching '
          'illustration, never invented historical evidence. Central vertical crop, no text/logos/real-person likeness. '
        + 'Original painted urban game-poster aesthetic; fictional presenter opens and recurs during the story; '
          'no copied game characters. '
          'Two factual title lines max 22/28 characters; keywords, description, hashtags and fitting '
          'instrumental music searches. Preserve source URLs. Omit platz for nonrankings. '
          'User ideas are research hypotheses, not verified facts. Return requested JSON only.\n'
        + json.dumps({'channel': kanal['name'], 'topic': thema,
            'user_request': kanal.get('_themenauftrag', {}),
            'lessons': kanal.get('_regeln', [])[:4],
            'sources': [{k: q.get(k, '') for k in ('name', 'text', 'url')} for q in quellen],
            'current_draft': entwurf, 'corrections': korrektur}, ensure_ascii=False))


def wiki_waehlen(thema, auftrag, schema, grenze):
    """Eindeutige Markennamen zuerst direkt recherchieren, ohne KI-Auswahl."""
    import trends
    import themen
    vorgabe = themen.details('business-origin-stories', thema)
    if vorgabe.get('wikipedia'):
        quelle = (themen.quelle(vorgabe) if grenze <= 7000 else None) \
                  or trends.wikipedia(vorgabe['wikipedia'], grenze=grenze)
        return {'thema': thema, 'wikipedia': vorgabe['wikipedia']}, quelle
    if thema and len(thema) <= 80 and len(thema.split()) <= 4:
        quelle = trends.wikipedia(thema, grenze=grenze)
        if quelle:
            return {'thema': thema, 'wikipedia': quelle['name']}, quelle
    if thema:
        auftrag += ('\nThis explicit user topic is binding. Identify its company/article only; '
                    'do not replace it with another company or reject it because of earlier attempts.')
    wahl, _ = gemini(auftrag, schema, temperatur=0.9, modelle=SEHEN)
    return wahl, trends.wikipedia(wahl['wikipedia'], grenze=grenze)


def main(kanal_pfad, aus_pfad, thema=None):
    kanal = json.loads(Path(kanal_pfad).read_text(encoding='utf-8'))
    import lernen
    kanal['_regeln'] = lernen.regeln(Path(kanal_pfad).stem)
    import themen
    vorgabe = themen.details(Path(kanal_pfad).stem, thema)
    if vorgabe.get('idee_original'):
        kanal['_themenauftrag'] = {'idee': vorgabe['idee_original'],
                                  'rechercheauftrag': vorgabe.get('rechercheauftrag', '')}
    if vorgabe.get('nutzerskript'):
        kanal['_nutzerskript'] = vorgabe['nutzerskript']
    # GEMELDET: aus den Videos lernen, die wirklich liefen (Aufrufe, Zuschauerbindung)
    import erfolg
    stem = Path(kanal_pfad).stem
    if kanal.get('winkel'):
        kanal['_winkel'] = erfolg.waehlen(stem, 'winkel', kanal['winkel'],
                                        videoformat=dramaturgie.videoformat(kanal))
    kanal['_vorbilder'] = erfolg.vorbilder(stem, videoformat=dramaturgie.videoformat(kanal))
    verlauf_pfad = Path('verlauf') / (Path(kanal_pfad).stem + '.json')
    verlauf = json.loads(verlauf_pfad.read_text(encoding='utf-8')) if verlauf_pfad.exists() else []
    # Gescheiterte Versuche sind kein Grund, ein ausdrueckliches Nutzerthema zu meiden.
    frueher = '; '.join(v['thema'] for v in verlauf[-60:] if v.get('status') == 'gesendet')
    if thema:
        frueher = ''

    t0 = time.time()
    print('Skript: Quellen fuer den Kanal abrufen', flush=True)
    zusatz, quellen = hinweise(kanal, thema)
    if kanal.get('nur_quellen') and not quellen:
        raise RuntimeError('Keine belegte KI-Anwendung gefunden; keine unbelegte Skriptanfrage')
    print(f'Skript: {len(quellen)} Quellen abgerufen; Entwurf und Pruefungen folgen', flush=True)
    # Die Pruefung bekommt dieselben Quellen - sonst haelt sie eine heute
    # belegte Neuheit fuer „unverifizierbar", nur weil ihr Wissen aelter ist.
    def pruef_text():
        return '\n'.join(f"[{q['quelle']}] {q['name']}: {q['text']}" for q in quellen)

    def pruefen(e):
        """KI-Faktencheck PLUS Zahlenprobe im Code (zahlen.py): Eine Zahl, die in
        keiner Quelle steht, laesst das Skript durchfallen - auch wenn die KI sie
        durchwinkt. Der Modellname zaehlt als Quelle („gemma-3-27b" belegt 27B)."""
        import zahlen
        p, pruefmodell = gemini(prompts.fakten(pruef_text(), e), PRUEF_SCHEMA,
                              temperatur=0.1, cache='fakten', modelle=SEHEN)
        p = ohne_cta_einwand(p)
        fehlt = zahlen.unbelegt(e, [f"{q.get('name', '')} {q.get('text', '')}" for q in quellen])
        if fehlt:
            print('Zahlenprobe: nicht in den Quellen:', fehlt)
            p = {'ok': False, 'probleme': p['probleme'] + [
                'Number not found in the sources - remove it or use the exact number from the sources: ' + z
                for z in fehlt]}
        # Zweitpruefer einer anderen Firma (zweit.py): schwere Fehler sperren,
        # Ausschmueckungen gehen als Auftrag in die Story-Ueberarbeitung.
        z = None
        if quellen and not pruefmodell.startswith('groq:'):
            import zweit
            z = zweit.pruefen(' '.join(t['text'] for t in e['teile']),
                              '\n'.join(f"{q.get('name', '')}: {q.get('text', '')}" for q in quellen))
            if z:
                print(f"Zweitpruefer ({z['modell']}): {len(z['probleme'])} schwer, {len(z['leicht'])} leicht")
                if not z['ok']:
                    p = {'ok': False, 'probleme': p['probleme'] + ['[second checker] ' + x for x in z['probleme']]}
                p['leicht'] = z['leicht']
        p['modell'] = pruefmodell
        p['zweitpruefer_modell'] = z['modell'] if z else None
        p['zweitpruefer_anderer_anbieter'] = bool(z and not pruefmodell.startswith('groq:'))
        return p
    # GEMESSEN 02.10.2026: „Burt's Bees" fiel auch nach der Ueberarbeitung
    # durch (Detailfehler) - ohne zweites Thema gab es an dem Tag kein Video.
    # Ein festes Thema vom Nutzer wird nicht ausgetauscht.
    verworfen = []
    lang = dramaturgie.videoformat(kanal) == 'lang'
    rate = wortrate(kanal)
    mindest = int(dramaturgie.laengen(kanal)[0] * 2.75 * rate / 2.4)
    # GEMESSEN 07.10.2026 (Run 37652008678, WeWork): 2.9 Woerter/s erlaubte ~261
    # Woerter; Kokoro sprach daraus 117 s statt hoechstens 90 s -> Tempo 1.25.
    # Gesprochen werden ~2.2-2.4 Woerter/s; 2.4 entspricht Codex' Groq-Vorgabe 198-216.
    hoechstens = int(dramaturgie.laengen(kanal)[1] * rate)
    pmin = kanal.get('plaetze', [5, 7])[0]
    woerter_von = lambda e: sum(len(t['text'].split()) for t in e['teile'])
    def schreiben(auftrag):
        # GEMESSEN: Auch die Ueberarbeitung nach der Faktenpruefung kuerzte
        # das Skript (45 s Video) - darum gilt die Mindestlaenge fuer JEDEN Entwurf.
        # GEMESSEN: Eine Nachbesserung reichte nicht (147 Woerter = 56,8 s).
        # Bis zu drei; danach gilt der Entwurf als durchgefallen.
        zusatz_ = ''
        nachgebessert = False
        for versuch in range(4):
            # GEMESSEN 07.10.2026: Gemini-Gratiskontingent ueberlastet/leer -> AI-Skriptphase
            # 1620 s, kein Video an zwei Tagen. Claude (Abo des Nutzers, eigenes Kontingent)
            # schreibt zuerst; Fakten-/Storypruefung bleiben bei Gemini/Groq (Autor != Pruefer).
            e, m = None, None
            import claude_ki
            if claude_ki.verfuegbar():
                rest = float(os.environ.get('CF_SCHRITT_ENDE', 'inf')) - time.monotonic()
                e, m = claude_ki.schreiben(auftrag + zusatz_, SKRIPT_SCHEMA, zeit=int(max(60, min(240, rest - 30))))
                if e is None or not ki_speicher.schema_ok(e, SKRIPT_SCHEMA):
                    if e is not None:
                        claude_ki.sperren('Antwort passt nicht zum Schema')
                    print('Claude-Autor nicht nutzbar, weiter mit Gemini/Groq:', str(m)[:160], flush=True)
                    e = None
                else:
                    m = 'claude:' + m
            if e is None:
                e, m = gemini(auftrag + zusatz_, SKRIPT_SCHEMA,
                             fallback_prompt=groq_skriptauftrag(kanal, thema, quellen, auftrag, mindest, hoechstens) + zusatz_)
            ranking = kanal.get('format', 'ranking') == 'ranking'
            if not ranking:
                for teil in e['teile']:
                    teil.pop('platz', None)
            zahl = woerter_von(e)
            plaetze = sum(1 for t in e['teile'] if t.get('platz'))
            # GEMESSEN: Ranking kam mit 4 statt 5-7 Plaetzen.
            zu_wenig = kanal.get('format', 'ranking') == 'ranking' and plaetze < pmin
            zuordnen(e, quellen)
            soll = {q['url']: n for n, q in enumerate(rangliste(quellen, kanal), 1)} if ranking else {}
            # GEMELDET (2 Analysen): gewuerfelte Reihenfolge (#4 -> #6 -> #3 ...)
            # verwirrt. Jetzt Countdown - und das prueft der Code, nicht die KI.
            folge = [t['platz'] for t in e['teile'] if t.get('platz')]
            if ranking and folge != sorted(folge, reverse=True):
                print(f'Versuch {versuch + 1}: kein Countdown: {folge}')
                zusatz_ = f'\nYour previous draft used the order {folge}. Use a strict countdown down to 1.'
                continue
            falsch = [f"#{t['platz']} must be #{soll[t['quelle_url']]}" for t in e['teile']
                      if t.get('platz') and t.get('quelle_url') in soll and soll[t['quelle_url']] != t['platz']]
            # GEMESSEN: Die Loop-Regel wurde ignoriert („Follow for more daily
            # AI tools." als Schluss) und „with just one click" kam durch die
            # Pruefung. Beides prueft jetzt der Code - einmal nachbessern,
            # danach wird es hingenommen (kein Grund, ein Video zu verwerfen).
            schluss = e['teile'][-1]['text'].strip() if e['teile'] else ''
            floskel = re.findall(r'just one click|in seconds|\bmagic\b|\binsane\b|game.?changer',
                                 ' '.join(t['text'] for t in e['teile']), re.I)
            # GEMESSEN: Der Schluss ohne Punkt („And the best part") wirkte laut
            # KI-Pruefung wie ein Abbruch (Schluss 4/10) - nur noch Floskeln pruefen.
            if floskel and not nachgebessert and zahl >= mindest and not zu_wenig \
                    and not falsch:
                nachgebessert = True
                print(f'Versuch {versuch + 1}: Loop/Floskel nachbessern ({floskel or schluss[-40:]})')
                zusatz_ = f'\nYour previous draft used banned phrases {floskel}. Keep everything else.'
                continue
            if mindest <= zahl <= hoechstens and not zu_wenig and not falsch:
                return e, m, None
            if zahl > hoechstens:
                zusatz_ = (f'\nYour draft has {zahl} spoken words; the maximum is {hoechstens}. '
                           'Shorten repeated explanations and secondary facts while keeping the '
                           'main evidence, full ranking and complete payoff. Do not solve this '
                           'with faster speech. Keep at least ' + str(mindest) + ' words.')
                continue
            if falsch:
                print(f'Versuch {versuch + 1}: Rangfolge falsch: {falsch}')
                zusatz_ = ('\nYour previous draft broke the FIXED RANKING (' + '; '.join(falsch)
                           + '). Use exactly the given ranks.')
                continue
            print(f'Versuch {versuch + 1}: {zahl} Woerter, {plaetze} Plaetze - zu wenig')
            zusatz_ = (f'\nYour previous draft had only {zahl} spoken words and {plaetze} ranked entries. '
                       f'The script MUST have at least {mindest + 20} spoken words in total'
                       + (f' and at least {pmin} ranked entries' if zu_wenig else '')
                       + ' - give each entry 2-3 sentences with concrete facts from the sources, no filler.')
        return e, m, f'Skript ausserhalb der Laenge oder Rangfolge falsch ({zahl} Woerter, {plaetze} Plaetze)'

    basis_zusatz = zusatz
    wiki_fotos = []
    # GEMESSEN 04.10.2026: Fielen alle Themen weg (Wikipedia 429), war 'pruefung'
    # unbelegt -> UnboundLocalError, der ganze Lauf brach ab. Jetzt sauberer Fehlschlag.
    pruefung, entwurf = {'ok': False, 'probleme': ['Kein Thema mit brauchbarer Quelle gefunden']}, None
    for runde in range(1 if thema else 3):
        runden_thema = thema
        if kanal.get('quelle') == 'wikipedia':
            # Erst das Thema, dann die Quelle, dann das Skript NUR aus der Quelle
            import trends
            # GEMELDET: Die Themen muessen alle immer aktuell sein. Firmen, die gestern viel
            # gelesen wurden (Wikipedia-Aufrufe, ohne KI ermittelt) - ein Anlass, JETZT zu schauen.
            aktuell = [] if thema else trends.firmen_im_trend()[:5]  # weniger Anfragen (429)
            if not thema and not aktuell:  # GEMESSEN: einmal leer (Wikipedia kurz nicht erreichbar)
                time.sleep(3); aktuell = trends.firmen_im_trend()[:5]
            # GEMELDET 04.10.2026: Flop-Video Skydance (KI-Note 3/10) - aktuell, aber ohne ein
            # einziges freies Foto (nur unscharfer Hintergrund) und ohne Gruendungsdrama
            # (ein Firmen-Update). Trend-Firmen nur mit mindestens 4 freien Fotos.
            mit_fotos = []
            for a in aktuell if kanal.get('bildstil') != 'illustration' else []:
                time.sleep(0.5)
                if len(trends.wiki_bilder(a[0])) >= 4:
                    mit_fotos.append(a)
            print(f'Trend-Firmen mit Fotos: {[a[0] for a in mit_fotos]} (von {len(aktuell)})')
            aktuell = mit_fotos if kanal.get('bildstil') != 'illustration' else aktuell
            wahl, q = wiki_waehlen(thema, prompts.DATEN + f'Pick ONE {kanal["name"]} topic with a source-rich origin story '
                             'and identifiable visual material. Do not invent proof of future popularity. '
                             + (f'Topic: {thema}. ' if thema else '')
                             + f'Do NOT use: {"; ".join(filter(None, [frueher] + verworfen)) or "none"}. '
                             + (('\nCOMPANIES IN THE NEWS RIGHT NOW (most-read on Wikipedia yesterday): '
                                 + '; '.join(f'{x[0]} ({x[2]}, {x[1]:,} views)' for x in aktuell)
                                 + '. Prefer one of these ONLY if it has a real, dramatic founding story '
                                   '(founded 15+ years ago, a founder who took a risk, a near-failure) - '
                                   'viewers search for them today. A recent merger or corporate update is NOT '
                                   'an origin story; then pick a classic brand instead. ') if aktuell else '')
                             + 'Pick a WORLD-FAMOUS brand most viewers know (long English Wikipedia article '
                             'with a detailed history section) - not a regional or niche company. '
                             'Give the exact title of its English Wikipedia article.' + basis_zusatz,
                             {'type': 'OBJECT', 'properties': {'thema': {'type': 'STRING'},
                                                               'wikipedia': {'type': 'STRING'}},
                              'required': ['thema', 'wikipedia']}, 30000 if lang else 7000)
            # GEMESSEN: Aus 1.353 Zeichen Quelle (Balaji Wafers) liess sich keine
            # 60-s-Geschichte schreiben, ohne zu strecken - sofort naechstes Thema.
            # GEMESSEN 05.10.2026: Jollibee (2.555 Zeichen), Balaji Wafers (1.353) - aus so
            # duennen Artikeln fiel jede Fassung durch die Faktenpruefung, kein Video.
            if q and len(q['text']) < (12000 if lang else 5000):
                print(f"Quelle zu kurz ({len(q['text'])} Zeichen): {q['name']} - neues Thema")
                q = None
            if not q:
                print(f"Kein Wikipedia-Artikel: {wahl['wikipedia']} - neues Thema")
                verworfen.append(wahl['thema'])
                continue
            quellen = [q]
            wiki_fotos = trends.wiki_bilder(q['name']) if kanal.get('bildstil') != 'illustration' else []
            kanal['_bildmaterial'] = [{'titel': b['titel'], 'beschreibung': b['beschreibung'][:240]}
                                      for b in wiki_fotos[:40]]
            print(f'Freie Fotos: {len(wiki_fotos)}')
            runden_thema = wahl['thema']
            if any(q['name'] == a[0] for a in aktuell):
                basis_zusatz += ('\nThis company is in the news right now: open the hook with what is happening '
                                 'today (ONLY if the source mentions it), then tell how it all began.')
            zusatz = (basis_zusatz + f"\nSOURCE (English Wikipedia, \"{q['name']}\"). Every factual claim MUST "
                      f"come from this text; leave out anything that is not in it:\n{q['text']}\n")
            print(f"Quelle: Wikipedia - {q['name']} ({len(q['text'])} Zeichen)")
        entwurf, modell, mangel = schreiben(anweisung(kanal, runden_thema,
                                                      '; '.join(filter(None, [frueher] + verworfen))) + zusatz)
        # Zweiter Durchgang: Fakten und Regeln pruefen (Konzept 4a, Punkt 8).
        pruefung = pruefen(entwurf)
        if not pruefung['ok'] or mangel:
            # Einmal neu schreiben, mit den gefundenen Problemen als Auflage.
            probleme = pruefung['probleme'] + ([mangel] if mangel else [])
            # GEMESSEN 04.10.2026: Neu von vorn geschrieben, brachte die Korrektur
            # neue Fehler mit (Harley: „Arthurs Brueder" statt Ole Evinrude) und das
            # Thema fiel weg. Jetzt: den Entwurf behalten, NUR die Fehler beheben -
            # bis zu zwei Mal.
            for _ in range(2):
                entwurf, modell, mangel = schreiben(
                    anweisung(kanal, entwurf['thema'], frueher) + zusatz
                    + '\nHere is a draft. Keep its story, structure and wording, but FIX ONLY these problems '
                      '(correct or remove each claim using the sources):\n- ' + '\n- '.join(probleme)
                    + '\nDRAFT:\n' + json.dumps(entwurf, ensure_ascii=False))
                pruefung = pruefen(entwurf)
                if pruefung['ok'] and not mangel:
                    break
                probleme = pruefung['probleme'] + ([mangel] if mangel else [])
        if mangel:  # zu kurz = unter 60 s = keine TikTok-Verguetung: nicht vorlegen
            pruefung = {'ok': False, 'probleme': pruefung['probleme'] + [mangel]}
        if pruefung['ok']:
            break
        print(f"Thema verworfen: {entwurf['thema']} - {pruefung['probleme']}")
        verworfen.append(entwurf['thema'])

    # Story-Pruefung vor dem Bau: zentrale Mindestnote, keine schwache Einzelkategorie.
    # Bis zu drei optionale Runden innerhalb der Skriptfrist. Jede neue Fassung
    # muss WIEDER durch die Faktenpruefung -
    # Spannung nie auf Kosten der Wahrheit. Behalten wird die beste Fassung.
    def fassung_speichern(entwurf, modell, pruefung, story):
        zuordnen(entwurf, quellen)
        # GEMESSEN: Die KI liess „name" leer - dann fehlte der Name unter der Karte.
        for t in entwurf['teile']:
            if t.get('platz') and not t.get('name') and t.get('quelle_url'):
                t['name'] = t['quelle_url'].rstrip('/').split('/')[-1].replace('-', ' ').replace('_', ' ')[:24]
        # Bild-Aufhaenger: Der Einstieg zeigt schon die Karte von Platz 1
        # (Neugier: „was ist das?"), statt eines leeren Farbverlaufs.
        erster = next((t for t in entwurf['teile'] if t.get('platz') == 1 and t.get('quelle_url')), None)
        if erster and not entwurf['teile'][0].get('platz'):
            entwurf['teile'][0]['quelle_url'] = erster['quelle_url']

        # Stimme abwechselnd nach Tag (Abwechslung gegen Massenware-Regel)
        stimmen = kanal.get('stimmen', ['am_michael'])
        # Nur die Stimmen des Nutzers; welche, entscheidet der Erfolg (erfolg.py)
        stimme = erfolg.waehlen(Path(kanal_pfad).stem, 'stimme', stimmen,
                              videoformat=dramaturgie.videoformat(kanal))
        zeile = lambda z: ' '.join(f'*{w}*' if any(w.strip('.,!?').lower() == s.lower() for s in
                                                    ' '.join(entwurf['schluesselwoerter']).split()) else w
                                    for w in z.split())
        skript = {
            **lernen.erprobte_einstellungen(Path(kanal_pfad).stem),
            'kanal': kanal['name'], 'thema': entwurf['thema'],
            'titel': [zeile(entwurf['titel_zeile1']), zeile(entwurf['titel_zeile2'])],
            'stimme': stimme, 'tempo': 1.05, 'teile': entwurf['teile'],
            'titel_farbe': kanal.get('titel_farbe', '#20D2BE'),
            'untertitel_profil': lernen.erprobte_einstellungen(stem).get('untertitel_profil', 'ruhig'),
            'posten_ny': kanal.get('posten_ny', '15:00'),
            'laenge_s': dramaturgie.laengen(kanal), 'videoformat': dramaturgie.videoformat(kanal),
            'regeln': kanal.get('_regeln', []),
            'winkel': kanal.get('_winkel', ''), 'format': kanal.get('format', 'ranking'),
            'story': story,
            'hintergrund_suche': kanal.get('hintergrund_suche', ''),
            'musik_suche': [q.strip()[:100] for q in entwurf.get('musik_suche', [])
                            if isinstance(q, str) and q.strip()][:3] or kanal.get('musik_suche', []),
            'bilder': wiki_fotos,
            'beschreibung': entwurf['beschreibung'] + '\nClips: Pixabay'
                            + (''.join(f"\nSource: Wikipedia - {q['name']} (CC BY-SA)" for q in quellen
                                       if q.get('quelle') == 'Wikipedia')), 'hashtags': entwurf['hashtags'],
            'pruefung': pruefung, 'quellen': [q['url'] for q in quellen if q.get('url')],
            'belege': [{'name': q.get('name', ''), 'text': q.get('text', ''),
                        'url': q.get('url', ''), 'quelle': q.get('quelle', '')} for q in quellen],
            'modell': modell, 'sekunden_ki': round(time.time() - t0, 1),
            'prompt_version': prompts.VERSION,
        }
        Path(aus_pfad).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(aus_pfad) + '.tmp')
        tmp.write_text(json.dumps(skript, indent=2, ensure_ascii=False), encoding='utf-8')
        tmp.replace(aus_pfad)
        return skript

    story = None
    if pruefung['ok']:
        entwurf['videoformat'] = dramaturgie.videoformat(kanal)
        story = story_bewerten(entwurf)
        print(f"Story: {story['note']}/10 {story['kategorien']}")
        fassung_speichern(entwurf, modell, pruefung, story)
        try:
            for runde in range(3):  # Ziel 10/10; keine unbeschraenkten Textschleifen.
                if story['note'] >= 10 and not redaktion(story, STORY_KATEGORIEN, 'Skript')[1]:
                    break
                if not redaktion(story, STORY_KATEGORIEN, 'Skript')[1] \
                        and float(os.environ.get('CF_SCHRITT_ENDE', 'inf')) - time.monotonic() < 120:
                    print('Gepruefte Story bleibt erhalten; Restzeit fuer den Videobau lassen', flush=True)
                    break
                neu, m, mangel = schreiben(
                    anweisung(kanal, entwurf['thema'], frueher) + zusatz
                    + '\nREWRITE for a stronger story (same topic, same facts and sources). A story editor found:\n- '
                    + '\n- '.join(story['schwaechen'])
                    + f"\nConsider this opening: {story['besserer_hook']}\nKeep the tension until the end and pay off "
                      'the hook in the last part.'
                    + (('\nAlso remove these details the sources do not support:\n- ' + '\n- '.join(pruefung['leicht']))
                       if pruefung.get('leicht') else '')
                    # GEMESSEN 04.10.2026: Ohne den bisherigen Entwurf schrieb die KI jede
                    # Runde neu von vorn - Story 6 -> 6 -> 5. In doku.py (mit Entwurf) 7 -> 8.
                    + '\nCURRENT DRAFT - improve THIS draft, preserve only source-supported facts:\n'
                    + json.dumps(entwurf, ensure_ascii=False))
                if mangel:
                    continue
                p2 = pruefen(neu)
                if not p2['ok']:
                    # GEMESSEN 04.10.2026 (Lamborghini): Alle 3 spannenderen Fassungen
                    # fielen durch die Faktenpruefung, die Story blieb bei 4/10. Statt sie
                    # wegzuwerfen: EINMAL nur die gemeldeten Fehler reparieren lassen.
                    print('Story-Fassung fiel durch die Faktenpruefung - Reparatur:', [x[:80] for x in p2['probleme']])
                    repariert, m, mangel = schreiben(
                        anweisung(kanal, entwurf['thema'], frueher) + zusatz
                        + '\nHere is a draft. Keep its story, structure and wording, but FIX ONLY these fact problems '
                          '(remove or correct the claim using the sources):\n- ' + '\n- '.join(p2['probleme'])
                        + '\nDRAFT:\n' + json.dumps(neu, ensure_ascii=False))
                    if mangel:
                        continue
                    p2 = pruefen(repariert)
                    if not p2['ok']:
                        print('Auch die Reparatur fiel durch - verworfen')
                        continue
                    neu = repariert
                neu['videoformat'] = dramaturgie.videoformat(kanal)
                s2 = story_bewerten(neu)
                print(f"Story neu: {s2['note']}/10 (vorher {story['note']})")
                if rang(s2, STORY_KATEGORIEN) > rang(story, STORY_KATEGORIEN):
                    entwurf, modell, pruefung, story = neu, m, p2, s2
                    fassung_speichern(entwurf, modell, pruefung, story)
                else:
                    # Sparsam: Bringt eine Runde keine bessere Note, bringen weitere
                    # meist auch nichts (GEMESSEN: 6 -> 6 -> 5) - abbrechen.
                    break

        except RuntimeError:
            print("Optionale Story-Verbesserung abgebrochen; gepruefte Fassung bleibt erhalten", flush=True)

    if entwurf is None:  # kein einziges Thema hatte eine brauchbare Quelle
        print('Kein Thema gefunden - Versuch beendet', file=sys.stderr)
        sys.exit(2)
    skript = fassung_speichern(entwurf, modell, pruefung, story)
    print(json.dumps({k: skript[k] for k in ('thema', 'titel', 'stimme', 'pruefung', 'modell', 'sekunden_ki')},
                     indent=2, ensure_ascii=False))
    # Konzept 4a: Was durchfaellt, wird nicht vorgelegt. GEMESSEN: Bei
    # „Top 5 AI Video Tools" fand die Pruefung auch nach der Ueberarbeitung
    # veraltete Aussagen (Runway, Sora) - ohne aktuelle Suche kein Video.
    if not pruefung['ok']:
        print('FAKTENPRUEFUNG NICHT BESTANDEN - kein Video.', file=sys.stderr)
        sys.exit(2)
    gruende = skript_gruende(skript)
    if gruende:
        print('SKRIPTQUALITAET NICHT BESTANDEN: ' + '; '.join(gruende), file=sys.stderr)
        sys.exit(3)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else '') or None)
