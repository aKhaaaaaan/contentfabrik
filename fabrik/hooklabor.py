"""Hook-Labor: fuenf Varianten fuer den ersten Satz, ein anderer KI-Richter waehlt.

Nutzerauftrag 10.10.2026 (Idee aus einer fremden „Content-Maschine"): YouTube Studio zeigte,
dass Shorts nur 21-24 s gesehen wurden - ueber das Weiterschauen entscheiden die ersten
Sekunden. Vorher gab es genau EINEN Hook vom Autor; die Story-Pruefung schlug hoechstens
einen „besseren Hook" vor. Jetzt: Autor (Claude) schreibt fuenf Varianten mit verschiedenen
Mechaniken, ein anderer Richter (Gemini) vergleicht sie mit dem bisherigen Satz. Uebernommen
wird nur, was danach die Fakten- und die Story-Pruefung besteht (Aufrufer prueft).
"""
import re

ANZAHL = 5

HOOK_SCHEMA = {
    'type': 'OBJECT',
    'properties': {'hooks': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
        'text': {'type': 'STRING'}, 'mechanik': {'type': 'STRING'}}, 'required': ['text', 'mechanik']}}},
    'required': ['hooks'],
}

WAHL_SCHEMA = {
    'type': 'OBJECT',
    'properties': {'beste': {'type': 'INTEGER'}, 'begruendung': {'type': 'STRING'}},
    'required': ['beste', 'begruendung'],
}

MECHANIKEN = ('a surprising number or contrast', 'a concrete moment with a person in action',
              'a bold claim the video then proves', 'a direct question the viewer cannot answer yet',
              'the end result first, then "how?"')


# Einstiegsarten wie lauf.py sie im Verlauf festhaelt (hook_art) - auf Englisch fuer den Auftrag
ARTEN = {'frage': 'a direct question', 'zahl': 'a number', 'widerspruch': 'a contrast ("but", "never", "only")',
         'aussage': 'a plain bold statement'}
MIN_VIDEOS = 3  # je Einstiegsart, sonst ist der Durchschnitt Zufall


def zuschauer_daten(kanal=None):
    """Echte Zuschauerdaten des Kanals je Einstiegsart (YouTube, gesehener Anteil), staerkste zuerst, oder ''.
    GEMESSEN 22.10.2026 (erfolg/*.json): Business Frage 37 % gesehen (3 Videos) gegen Zahl 15 % (8); KI Aussage
    37 % (8) gegen Zahl 15 % (3). Das Hook-Labor wusste davon nichts - Autor und Richter urteilten nur nach Gefuehl."""
    import json
    import os
    import statistics
    import sys
    from pathlib import Path
    kanal = kanal or os.environ.get('CF_KANAL') or (Path(sys.argv[1]).stem if len(sys.argv) > 1
                                                   and sys.argv[1].endswith('.json') else '')
    try:
        videos = json.loads((Path('erfolg') / f'{kanal}.json').read_text(encoding='utf-8'))['videos'].values()
    except (OSError, ValueError, KeyError, AttributeError):
        return ''
    gruppen = {}
    for v in videos:
        e = v.get('einstellungen') or {}
        if e.get('hook_art') in ARTEN and v.get('oeffentlich') and isinstance(v.get('anteil_prozent'), (int, float)) \
                and (e.get('videoformat') or 'short') == 'short':
            gruppen.setdefault(e['hook_art'], []).append(v['anteil_prozent'])
    werte = sorted(((statistics.mean(w), art, len(w)) for art, w in gruppen.items() if len(w) >= MIN_VIDEOS),
                   reverse=True)
    if len(werte) < 2:
        return ''
    return ('REAL AUDIENCE DATA for this channel (YouTube, average share of the Short watched, by opening type): '
            + '; '.join(f'{ARTEN[a]}: {m:.0f}% ({n} videos)' for m, a, n in werte)
            + '. Prefer the stronger opening types when they fit the facts honestly.\n')


def teilen(text):
    """Ersten Satz vom Rest trennen (Satzende . ! ? gefolgt von Leerraum)."""
    m = re.match(r'\s*(.+?[.!?]["”\']?)(\s+|$)(.*)', text or '', re.S)
    return (m.group(1).strip(), m.group(3).strip()) if m else ((text or '').strip(), '')


def woerter(text):
    return len(str(text).split())


def auftrag(entwurf, belege):
    """Auftrag an den Autor: nur den ersten Satz neu, gleiche Laenge, nur belegte Fakten."""
    satz, danach = teilen(entwurf['teile'][0]['text'])
    rest = '\n'.join(t['text'] for t in entwurf['teile'])
    # GEPRUEFT 10.10.2026 (echte Claude-Probe): ohne diesen Hinweis nahm eine Variante den
    # Folgesatz vorweg („... one employee bought it" + „Then one employee bought it.").
    folgt = danach or (entwurf['teile'][1]['text'] if len(entwurf['teile']) > 1 else '')
    return (f'You write the opening line of a YouTube Short / TikTok about: {entwurf["thema"]}.\n'
            + zuschauer_daten() +
            f'The current first sentence is: "{satz}"\n'
            f'Your sentence will be followed DIRECTLY by: "{teilen(folgt)[0]}" - do not repeat or reveal it.\n'
            f'Write {ANZAHL} alternative FIRST SENTENCES that make a viewer stop scrolling within 2 seconds. '
            f'Use a different mechanic for each: {"; ".join(MECHANIKEN)}.\n'
            f'Rules: {max(6, woerter(satz) - 4)}-{woerter(satz) + 4} words each; plain spoken English; the sentence '
            'must lead naturally into the rest of the script below; use ONLY facts stated in the script or the '
            'sources; no clickbait the video does not pay off; no emojis; no "In this video".\n'
            f'SCRIPT:\n{rest}\n\nSOURCES (facts allowed):\n{belege[:6000]}')


def wahl_auftrag(entwurf, kandidaten):
    rest = teilen(entwurf['teile'][0]['text'])[1] + ' ' + ' '.join(t['text'] for t in entwurf['teile'][1:])
    liste = '\n'.join(f'{i}: {k}' for i, k in enumerate(kandidaten))
    return ('You are a strict short-form video editor. Pick the opening sentence that makes the most viewers '
            'keep watching past 3 seconds AND that the rest of the script honestly pays off. Penalize vague '
            'teasing, clickbait, and sentences that do not connect to what follows.\n'
            + zuschauer_daten() +
            f'CANDIDATES:\n{liste}\n\nREST OF THE SCRIPT (after the opening sentence):\n{rest[:3000]}\n'
            'Answer with the index of the best candidate in "beste".')


def kandidaten(antwort, alt):
    """Gueltige, verschiedene Varianten; Index 0 bleibt immer der bisherige Satz."""
    aus = [alt]
    grenze = (max(6, woerter(alt) - 4), woerter(alt) + 4)
    for h in (antwort or {}).get('hooks') or []:
        text = re.sub(r'\s+', ' ', str((h or {}).get('text', ''))).strip().strip('"')
        if text and text[-1] not in '.!?':
            text += '.'
        if text and grenze[0] <= woerter(text) <= grenze[1] and text.lower() not in [a.lower() for a in aus]:
            aus.append(text)
    return aus[:ANZAHL + 1]


def einsetzen(entwurf, satz):
    """Neuer Entwurf mit ersetztem erstem Satz; das Original bleibt unveraendert."""
    import copy
    neu = copy.deepcopy(entwurf)
    _, rest = teilen(neu['teile'][0]['text'])
    neu['teile'][0]['text'] = f'{satz} {rest}'.strip()
    return neu


def verbessern(entwurf, belege, schreiber, richter):
    """Gibt (neuer_entwurf oder None, Protokoll) zurueck. schreiber/richter: (prompt, schema) -> dict."""
    alt = teilen(entwurf['teile'][0]['text'])[0]
    liste = kandidaten(schreiber(auftrag(entwurf, belege), HOOK_SCHEMA), alt)
    protokoll = {'alt': alt, 'kandidaten': liste[1:]}
    if len(liste) < 2:
        protokoll['ergebnis'] = 'keine gueltigen Varianten'
        return None, protokoll
    wahl = richter(wahl_auftrag(entwurf, liste), WAHL_SCHEMA) or {}
    beste = wahl.get('beste')
    protokoll['begruendung'] = str(wahl.get('begruendung', ''))[:300]
    if not isinstance(beste, int) or isinstance(beste, bool) or not 0 <= beste < len(liste):
        protokoll['ergebnis'] = 'ungueltige Wahl'
        return None, protokoll
    protokoll['gewaehlt'] = liste[beste]
    if beste == 0:
        protokoll['ergebnis'] = 'bisheriger Hook bleibt'
        return None, protokoll
    protokoll['ergebnis'] = 'neuer Hook vorgeschlagen'
    return einsetzen(entwurf, liste[beste]), protokoll
