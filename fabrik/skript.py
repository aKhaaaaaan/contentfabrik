"""Skript-Baustein: Kanal-Einstellung -> Thema -> Skript -> Faktenpruefung.

Schreibt ein Skript im Format, das fabrik/bauen.py versteht.
KI: Google Gemini, kostenloses Kontingent (Schluessel GEMINI_API_KEY).

Aufruf:  python fabrik/skript.py kanaele/ai-tools-explained.json skripte/heute.json [thema]
"""
import json, os, sys, time, urllib.request, datetime
from pathlib import Path

# GEPRUEFT 02.10.2026: gemini-2.5-flash ist fuer neue Konten gesperrt (404);
# gemini-3.8-flash und gemini-flash-latest antworten (200).
# Bei Ueberlastung (503, gemessen bei 3.8-flash) sofort das naechste Modell.
MODELLE = ['gemini-flash-latest', 'gemini-3-flash-preview', 'gemini-3.8-flash', 'gemini-flash-lite-latest']


def gemini(prompt, schema, temperatur=0.9):
    schluessel = os.environ['GEMINI_API_KEY']
    koerper = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': temperatur, 'responseMimeType': 'application/json',
                             'responseSchema': schema},
    }
    letzter = None
    for modell in MODELLE:
        for versuch in range(2):
            try:
                req = urllib.request.Request(
                    f'https://generativelanguage.googleapis.com/v1beta/models/{modell}:generateContent?key={schluessel}',
                    data=json.dumps(koerper).encode(), headers={'Content-Type': 'application/json'})
                d = json.load(urllib.request.urlopen(req, timeout=120))
                return json.loads(d['candidates'][0]['content']['parts'][0]['text']), modell
            except Exception as e:  # Kontingent/Netz: kurz warten, dann naechster Versuch
                letzter = str(e).replace(schluessel, '***')
                time.sleep(5 * (versuch + 1))
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
            'suche': {'type': 'STRING'}, 'text': {'type': 'STRING'}},
            'required': ['suche', 'text']}},
        'beschreibung': {'type': 'STRING'},
        'hashtags': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
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


def anweisung(kanal, thema, frueher):
    lmin, lmax = kanal.get('laenge_s', [62, 90])
    woerter = f'{int(lmin * 2.5)}-{int(lmax * 2.5)}'
    fmt = kanal.get('format', 'ranking')
    if fmt == 'ranking':
        pmin, pmax = kanal.get('plaetze', [5, 7])
        aufbau = (f'RANKING format with {pmin}-{pmax} entries. First part: a hook without a rank. '
                  'Then the ranked entries in a SHUFFLED order (never 7-6-5-...), number 1 ALWAYS last. '
                  'Each ranked entry has "platz" (its rank) and "name" (max 2 words). Last part: short call to action '
                  '(follow for more), no rank.')
    else:
        aufbau = ('STORY format: first part is a strong hook (a surprising fact or question), then 4-6 parts that '
                  'tell the story in order with tension, last part a short takeaway plus call to action. No "platz".')
    return f"""You write scripts for the faceless YouTube Shorts / TikTok channel "{kanal['name']}" (language: English).
{('Topic: ' + thema) if thema else 'Pick ONE fresh, specific topic that is proven to perform in this niche right now.'}
Do NOT repeat these earlier topics: {frueher or 'none'}.

Rules:
- {aufbau}
- Total spoken length {woerter} words (the video must be longer than 60 seconds).
- The first sentence is the hook: curiosity, a number or a contradiction. No intro, no greeting.
- Short, spoken sentences. Concrete facts only. Every claim must be TRUE and verifiable today; if unsure, leave it out.
  No financial, medical or legal advice. No made-up numbers.
- Own words and own angle; never copy text from other videos.
- "suche": 2-3 English words for a free stock VIDEO search that visually fits this part (concrete scene, no brand names, no people's names).
- On-screen title: exactly two lines, line 1 max 22 characters, line 2 max 28 characters.
  "schluesselwoerter": the 1-2 words of the title that tell the viewer instantly what the video is about.
- "beschreibung": 2 sentences for the platform description. "hashtags": 3-5 relevant hashtags.
"""


def main(kanal_pfad, aus_pfad, thema=None):
    kanal = json.loads(Path(kanal_pfad).read_text(encoding='utf-8'))
    verlauf_pfad = Path('verlauf') / (Path(kanal_pfad).stem + '.json')
    verlauf = json.loads(verlauf_pfad.read_text(encoding='utf-8')) if verlauf_pfad.exists() else []
    frueher = '; '.join(v['thema'] for v in verlauf[-60:])

    t0 = time.time()
    entwurf, modell = gemini(anweisung(kanal, thema, frueher), SKRIPT_SCHEMA)
    # Zweiter Durchgang: Fakten und Regeln pruefen (Konzept 4a, Punkt 8).
    pruefung, _ = gemini(
        'You are a strict fact checker for a YouTube Short script. Check every factual claim. '
        'Mark ok=false if ANY claim is false, outdated, unverifiable or exaggerated, or if a rule is broken '
        '(number 1 must be last in rankings, no medical/financial/legal advice). List each problem briefly.\n\n'
        + json.dumps(entwurf, ensure_ascii=False), PRUEF_SCHEMA, temperatur=0.1)
    if not pruefung['ok']:
        # Einmal neu schreiben, mit den gefundenen Problemen als Auflage.
        entwurf, modell = gemini(anweisung(kanal, entwurf['thema'], frueher)
                                 + '\nFix these problems found by the fact checker:\n- ' + '\n- '.join(pruefung['probleme']),
                                 SKRIPT_SCHEMA)
        pruefung, _ = gemini('Strict fact check as before.\n\n' + json.dumps(entwurf, ensure_ascii=False),
                             PRUEF_SCHEMA, temperatur=0.1)

    # Stimme abwechselnd nach Tag (Abwechslung gegen Massenware-Regel)
    stimmen = kanal.get('stimmen', ['am_michael'])
    stimme = stimmen[datetime.date.today().toordinal() % len(stimmen)]
    zeile = lambda z: ' '.join(f'*{w}*' if any(w.strip('.,!?').lower() == s.lower() for s in
                                                ' '.join(entwurf['schluesselwoerter']).split()) else w
                                for w in z.split())
    skript = {
        'kanal': kanal['name'], 'thema': entwurf['thema'],
        'titel': [zeile(entwurf['titel_zeile1']), zeile(entwurf['titel_zeile2'])],
        'stimme': stimme, 'tempo': 1.05, 'teile': entwurf['teile'],
        'beschreibung': entwurf['beschreibung'] + '\nClips: Pixabay', 'hashtags': entwurf['hashtags'],
        'pruefung': pruefung, 'modell': modell, 'sekunden_ki': round(time.time() - t0, 1),
    }
    Path(aus_pfad).parent.mkdir(parents=True, exist_ok=True)
    Path(aus_pfad).write_text(json.dumps(skript, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: skript[k] for k in ('thema', 'titel', 'stimme', 'pruefung', 'modell', 'sekunden_ki')},
                     indent=2, ensure_ascii=False))
    # Konzept 4a: Was durchfaellt, wird nicht vorgelegt. GEMESSEN: Bei
    # „Top 5 AI Video Tools" fand die Pruefung auch nach der Ueberarbeitung
    # veraltete Aussagen (Runway, Sora) - ohne aktuelle Suche kein Video.
    if not pruefung['ok']:
        print('FAKTENPRUEFUNG NICHT BESTANDEN - kein Video.', file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
