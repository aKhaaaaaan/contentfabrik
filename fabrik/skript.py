"""Skript-Baustein: Kanal-Einstellung -> Thema -> Skript -> Faktenpruefung.

Schreibt ein Skript im Format, das fabrik/bauen.py versteht.
KI: Google Gemini, kostenloses Kontingent (Schluessel GEMINI_API_KEY).

Aufruf:  python fabrik/skript.py kanaele/ai-tools-explained.json skripte/heute.json [thema]
"""
import json, os, re, sys, time, urllib.error, urllib.request, datetime
from pathlib import Path

# GEPRUEFT 02.10.2026: gemini-2.5-flash ist fuer neue Konten gesperrt (404);
# gemini-3.8-flash und gemini-flash-latest antworten (200).
# Bei Ueberlastung (503, gemessen bei 3.8-flash) sofort das naechste Modell.
# GEMESSEN 04.10.2026: Der kostenlose Tarif erlaubt je Modell nur 20 Anfragen
# am Tag (GenerateRequestsPerDayPerProjectPerModel-FreeTier = 20); Pro-Modelle
# gar keine. Nach einem Testtag waren drei Modelle leer. Jede Flash-Fassung hat
# ein eigenes Kontingent - darum alle, die beste zuerst (getestet: 2.5 nicht mehr
# verfuegbar, 3.7 zeitweise ueberlastet).
MODELLE = ['gemini-3.8-flash', 'gemini-flash-latest', 'gemini-3.7-flash', 'gemini-3.6-flash', 'gemini-3.5-flash',
           'gemini-3-flash-preview', 'gemini-flash-lite-latest', 'gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
# Bildauswahl (eine Anfrage je Abschnitt, ~10 je Video): schnelle Lite-Modelle
# zuerst, damit die starken Modelle fuer Skript und Pruefung uebrig bleiben.
SEHEN = ['gemini-flash-lite-latest', 'gemini-3.5-flash-lite', 'gemini-3.1-flash-lite', 'gemini-3.6-flash',
         'gemini-3.5-flash', 'gemini-flash-latest']


VERBRAUCH = {}  # modell -> [anfragen, tokens_rein, tokens_raus]


def _verbrauch_melden():
    if VERBRAUCH:
        print('Gemini-Verbrauch: ' + '; '.join(f'{m}: {a} Anfragen, {r // 1000}k rein, {o // 1000}k raus'
                                               for m, (a, r, o) in VERBRAUCH.items()))


import atexit  # noqa: E402
atexit.register(_verbrauch_melden)


def gemini(prompt, schema, temperatur=0.9, bilder=(), modelle=None, dateien=()):
    """bilder: JPEG-Bytes, die die KI mit ansieht (Clip-Auswahl in bauen.py).
    modelle: eigene Reihenfolge, z. B. das schnelle Lite-Modell zuerst."""
    import base64
    schluessel = os.environ['GEMINI_API_KEY']
    teile = [{'text': prompt}] + [{'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(b).decode()}}
                                  for b in bilder] + \
        [{'file_data': {'mime_type': m, 'file_uri': u}} for m, u in dateien]  # z. B. Video (kritik.py)
    koerper = {
        'contents': [{'parts': teile}],
        'generationConfig': {'temperature': temperatur, 'responseMimeType': 'application/json',
                             'responseSchema': schema},
    }
    letzter = None
    for modell in modelle or MODELLE:
        for versuch in range(2):
            try:
                req = urllib.request.Request(
                    f'https://generativelanguage.googleapis.com/v1beta/models/{modell}:generateContent?key={schluessel}',
                    data=json.dumps(koerper).encode(), headers={'Content-Type': 'application/json'})
                d = json.load(urllib.request.urlopen(req, timeout=120))
                # GEMELDET: „In der Pipeline sparsam mit Tokens sein" - erst messen:
                # Anfragen und Tokens je Modell, Ausgabe am Ende jedes Laufs.
                n = d.get('usageMetadata', {})
                z = VERBRAUCH.setdefault(modell, [0, 0, 0])
                z[0] += 1; z[1] += n.get('promptTokenCount', 0); z[2] += n.get('candidatesTokenCount', 0)
                return json.loads(d['candidates'][0]['content']['parts'][0]['text']), modell
            except Exception as e:  # Kontingent/Netz: kurz warten, dann naechster Versuch
                letzter = str(e).replace(schluessel, '***')
                koerper_fehler = ''
                if isinstance(e, urllib.error.HTTPError):
                    try:
                        koerper_fehler = e.read().decode(errors='replace')
                    except Exception:
                        pass
                # Tageskontingent leer: Warten hilft bis Mitternacht (Pazifik) nicht - naechstes Modell
                if 'PerDay' in koerper_fehler:
                    letzter = f'{modell}: Tageskontingent erschoepft'
                    break
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
            'suche': {'type': 'STRING'}, 'text': {'type': 'STRING'}, 'quelle_url': {'type': 'STRING'}},
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
        quellen = trends.ki_quellen()
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
    """Die Plaetze entscheidet der Code, nicht die KI. GEMESSEN: Trotz der
    Anweisung „nach Zahlen sortieren" stand ein Modell mit 4.973 Likes auf
    Platz 6 und eins mit 2.828 auf Platz 3. Sterne (GitHub) und Likes (Hugging
    Face) sind beides Zustimmung der Nutzer - darum gemeinsam sortiert."""
    n = kanal.get('plaetze', [5, 7])[1]
    return sorted((q for q in quellen if q.get('zahl') is not None), key=lambda q: -q['zahl'])[:n]


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
    teuren Video-Bau. Note 8+ = Zuschauer bleiben voraussichtlich bis zum Schluss."""
    text = '\n'.join(t['text'] for t in entwurf['teile'])
    erg, _ = gemini('You are a top short-form storyteller and retention analyst (YouTube Shorts / TikTok). Rate '
                    'ONLY the story of this script - would a scrolling viewer stop and stay to the very end? '
                    'Score each 1-10:\n' + '\n'.join(f'- {k}: {v}' for k, v in STORY_KATEGORIEN.items())
                    + '\nOverall "note" 1-10 (be strict: 8+ only if most viewers would watch to the end). List '
                    'concrete weaknesses with the exact sentence they refer to (what keeps it from 10/10), and write the strongest possible '
                    'alternative first sentence that stays 100% true to the facts in the script.\n\n'
                    f'Title: {entwurf.get("titel_zeile1", "")} / {entwurf.get("titel_zeile2", "")}\nScript:\n{text}',
                    STORY_SCHEMA, temperatur=0.2)
    return erg


def anweisung(kanal, thema, frueher):
    lmin, lmax = kanal.get('laenge_s', [62, 90])
    # GEMESSEN: Kokoro spricht ~2,7 Woerter/s; mit 2,5 je Sekunde gerechnet
    # kam ein Video auf 50 s - unter der 60-s-Grenze fuer TikTok-Verguetung.
    woerter = f'{int(lmin * 2.9)}-{int(lmax * 2.9)}'
    fmt = kanal.get('format', 'ranking')
    # Wechselnder Blickwinkel je Tag - dieselben belegten Daten, anders erzaehlt
    # (Analyse: viral gehen Nutzen, Neuheit, Ueberraschung; YouTube bestraft
    # gleichfoermige Massenware).
    winkel = kanal.get('winkel', [])
    # Erfolgs-Gedaechtnis waehlt (erfolg.py); ohne Wahl: nach Tag abwechseln
    blick = kanal.get('_winkel') or (winkel[datetime.date.today().toordinal() % len(winkel)] if winkel else '')
    if fmt == 'ranking':
        pmin, pmax = kanal.get('plaetze', [5, 7])
        aufbau = (f'RANKING format with {pmin}-{pmax} entries. First part: a hook without a rank. '
                  + ('Rank strictly by the numbers in the sources (stars, likes, downloads) - the biggest is number 1. '
                     if kanal.get('nur_quellen') else '') +
                  'Then the ranked entries as a COUNTDOWN from the highest number down to number 1 (e.g. 6-5-4-3-2-1). '
                  'Each ranked entry has "platz" (its rank) and "name" (max 2 words). Last part: short call to action '
                  '(follow for more), no rank.')
    else:
        # GEMESSEN: Geschichten kamen in 6 Anlaeufen nicht auf die Mindestlaenge (128-169 Woerter)
        aufbau = ('STORY format with 6-7 parts of 25-35 words each: first part is a strong hook (a surprising fact or question), then 4-6 parts that '
                  'tell the story in order with tension, last part a short takeaway plus call to action. No "platz".')
    return f"""You write scripts for the faceless YouTube Shorts / TikTok channel "{kanal['name']}" (language: English).
{('Topic: ' + thema) if thema else 'Pick ONE fresh, specific topic that is proven to perform in this niche right now.'}
Do NOT repeat these earlier topics: {frueher or 'none'}.

Rules:
- {aufbau}
- Total spoken length {woerter} words (the video must be longer than 60 seconds).
{('- ANGLE for today (title, hook and wording follow it): ' + blick) if blick else ''}
{"- NORMAL VIEWERS, NOT DEVELOPERS: every entry starts with what a normal person can DO with it (from its source), then one number that proves it. Avoid jargon like 'image-text-to-text' - say 'reads pictures and answers questions about them'. Say 'free' only if the source shows it is open source or free to download." if kanal.get('nur_quellen') else ''}
- The first sentence is the hook: a clear benefit, something brand new, or a surprise - within 3 seconds.
  No intro, no greeting.
- ENDING: a short call to action that asks viewers to SAVE the video for later (e.g. "Save this so you don't
  lose it." - GEMESSEN: a top tool-list video had 5,404 saves vs 5,151 likes; saves are the strongest signal),
  then ONE complete closing sentence that calls back to the hook (same image or question), so a replay feels
  natural. Never end mid-sentence.
- Never write "with just one click", "in seconds", "magic", "insane", "game changer".
- Short, spoken sentences: one idea each, at most 18 words (GEMESSEN: 17-18 words on average, the best
  scripts ~10). Write numbers as digits (1977, 3,703), never as words. Concrete facts only. Every claim must be TRUE and verifiable today; if unsure, leave it out.
  No financial, medical or legal advice. No made-up numbers.
- No hype or exaggeration words (instantly, overnight, everyone, every single, never before, changed the
  world) unless the source says exactly that. Legends and rumours only if clearly labelled as such.
- Own words and own angle; never copy text from other videos.
- {'"quelle_url": for every ranked entry, the EXACT url of its source from the SOURCES list (copy it). ' if kanal.get('nur_quellen') else ''}"suche": 2-3 English words for a free stock VIDEO search that visually fits this part (concrete scene, no brand names, no people's names).
- On-screen title: exactly two lines, line 1 max 22 characters, line 2 max 28 characters.
  "schluesselwoerter": the 1-2 words of the title that tell the viewer instantly what the video is about.
- "beschreibung": 2 sentences for the platform description. "hashtags": 3-5 relevant hashtags.
{('OUR OWN best performing videos so far (real views and watch time) - learn from their hook and '
  'structure, do not repeat their topic:' + chr(10) + chr(10).join('- ' + v for v in kanal['_vorbilder']) + chr(10))
 if kanal.get('_vorbilder') else ''}
{('LESSONS from quality reviews of our earlier videos - follow them strictly:' + chr(10)
  + chr(10).join('- ' + r for r in kanal['_regeln'])) if kanal.get('_regeln') else ''}
"""


def main(kanal_pfad, aus_pfad, thema=None):
    kanal = json.loads(Path(kanal_pfad).read_text(encoding='utf-8'))
    import lernen
    kanal['_regeln'] = lernen.regeln(Path(kanal_pfad).stem)
    # GEMELDET: aus den Videos lernen, die wirklich liefen (Aufrufe, Zuschauerbindung)
    import erfolg
    stem = Path(kanal_pfad).stem
    if kanal.get('winkel'):
        kanal['_winkel'] = erfolg.waehlen(stem, 'winkel', kanal['winkel'])
    kanal['_vorbilder'] = erfolg.vorbilder(stem)
    verlauf_pfad = Path('verlauf') / (Path(kanal_pfad).stem + '.json')
    verlauf = json.loads(verlauf_pfad.read_text(encoding='utf-8')) if verlauf_pfad.exists() else []
    frueher = '; '.join(v['thema'] for v in verlauf[-60:])

    t0 = time.time()
    zusatz, quellen = hinweise(kanal, thema)
    # Die Pruefung bekommt dieselben Quellen - sonst haelt sie eine heute
    # belegte Neuheit fuer „unverifizierbar", nur weil ihr Wissen aelter ist.
    def pruef_text():
        belege = ('\nSOURCES fetched today (treat as verified; claims beyond them are unverifiable):\n'
                  + '\n'.join(f"- [{q['quelle']}] {q['name']}: {q['text']}" for q in quellen)) if quellen else ''
        return ('You are a strict fact checker for a YouTube Short script. Check every factual claim. '
                'Mark ok=false if ANY claim is false, outdated, unverifiable or exaggerated, or if a rule is broken '
                '(number 1 must be last in rankings, no medical/financial/legal advice). List each problem briefly.'
                + belege + '\n\n')

    def pruefen(e):
        """KI-Faktencheck PLUS Zahlenprobe im Code (zahlen.py): Eine Zahl, die in
        keiner Quelle steht, laesst das Skript durchfallen - auch wenn die KI sie
        durchwinkt. Der Modellname zaehlt als Quelle („gemma-3-27b" belegt 27B)."""
        import zahlen
        p, _ = gemini(pruef_text() + json.dumps(e, ensure_ascii=False), PRUEF_SCHEMA, temperatur=0.1)
        fehlt = zahlen.unbelegt(e, [f"{q.get('name', '')} {q.get('text', '')}" for q in quellen])
        if fehlt:
            print('Zahlenprobe: nicht in den Quellen:', fehlt)
            p = {'ok': False, 'probleme': p['probleme'] + [
                'Number not found in the sources - remove it or use the exact number from the sources: ' + z
                for z in fehlt]}
        # Zweitpruefer einer anderen Firma (zweit.py): schwere Fehler sperren,
        # Ausschmueckungen gehen als Auftrag in die Story-Ueberarbeitung.
        if quellen:
            import zweit
            z = zweit.pruefen(' '.join(t['text'] for t in e['teile']),
                              '\n'.join(f"{q.get('name', '')}: {q.get('text', '')}" for q in quellen))
            if z:
                print(f"Zweitpruefer ({z['modell']}): {len(z['probleme'])} schwer, {len(z['leicht'])} leicht")
                if not z['ok']:
                    p = {'ok': False, 'probleme': p['probleme'] + ['[second checker] ' + x for x in z['probleme']]}
                p['leicht'] = z['leicht']
        return p
    # GEMESSEN 02.10.2026: „Burt's Bees" fiel auch nach der Ueberarbeitung
    # durch (Detailfehler) - ohne zweites Thema gab es an dem Tag kein Video.
    # Ein festes Thema vom Nutzer wird nicht ausgetauscht.
    verworfen = []
    mindest = int(kanal.get('laenge_s', [62, 90])[0] * 2.75)
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
            e, m = gemini(auftrag + zusatz_, SKRIPT_SCHEMA)
            zahl = woerter_von(e)
            plaetze = sum(1 for t in e['teile'] if t.get('platz'))
            # GEMESSEN: Ranking kam mit 4 statt 5-7 Plaetzen.
            zu_wenig = kanal.get('format', 'ranking') == 'ranking' and plaetze < pmin
            zuordnen(e, quellen)
            soll = {q['url']: n for n, q in enumerate(rangliste(quellen, kanal), 1)}
            # GEMELDET (2 Analysen): gewuerfelte Reihenfolge (#4 -> #6 -> #3 ...)
            # verwirrt. Jetzt Countdown - und das prueft der Code, nicht die KI.
            folge = [t['platz'] for t in e['teile'] if t.get('platz')]
            if folge != sorted(folge, reverse=True):
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
            if zahl >= mindest and not zu_wenig and not falsch:
                return e, m, None
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
        return e, m, f'Skript zu kurz oder Rangfolge falsch ({zahl} Woerter, {plaetze} Plaetze)'

    basis_zusatz = zusatz
    wiki_fotos = []
    for runde in range(1 if thema else 3):
        runden_thema = thema
        if kanal.get('quelle') == 'wikipedia':
            # Erst das Thema, dann die Quelle, dann das Skript NUR aus der Quelle
            wahl, _ = gemini(f'Pick ONE {kanal["name"]} topic for a YouTube Short that is proven to perform. '
                             + (f'Topic: {thema}. ' if thema else '')
                             + f'Do NOT use: {"; ".join(filter(None, [frueher] + verworfen)) or "none"}. '
                             'Give the exact title of its English Wikipedia article.' + basis_zusatz,
                             {'type': 'OBJECT', 'properties': {'thema': {'type': 'STRING'},
                                                               'wikipedia': {'type': 'STRING'}},
                              'required': ['thema', 'wikipedia']}, temperatur=0.9)
            import trends
            q = trends.wikipedia(wahl['wikipedia'])
            # GEMESSEN: Aus 1.353 Zeichen Quelle (Balaji Wafers) liess sich keine
            # 60-s-Geschichte schreiben, ohne zu strecken - sofort naechstes Thema.
            if q and len(q['text']) < 2500:
                print(f"Quelle zu kurz ({len(q['text'])} Zeichen): {q['name']} - neues Thema")
                q = None
            if not q:
                print(f"Kein Wikipedia-Artikel: {wahl['wikipedia']} - neues Thema")
                verworfen.append(wahl['thema'])
                continue
            quellen = [q]
            wiki_fotos = trends.wiki_bilder(q['name'])
            print(f'Freie Fotos: {len(wiki_fotos)}')
            runden_thema = wahl['thema']
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

    # Story-Pruefung vor dem Bau: unter 8 mit dem konkreten Feedback neu schreiben
    # (bis zu 2 Runden). Jede neue Fassung muss WIEDER durch die Faktenpruefung -
    # Spannung nie auf Kosten der Wahrheit. Behalten wird die beste Fassung.
    story = None
    if pruefung['ok']:
        story = story_bewerten(entwurf)
        print(f"Story: {story['note']}/10 {story['kategorien']}")
        for runde in range(3):  # Ziel 10/10 (GEMELDET); Text kostet kaum Rechenzeit
            if story['note'] >= 10:
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
                + '\nCURRENT DRAFT - improve THIS draft, keep every fact that is in it:\n'
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
            s2 = story_bewerten(neu)
            print(f"Story neu: {s2['note']}/10 (vorher {story['note']})")
            if s2['note'] > story['note']:
                entwurf, modell, pruefung, story = neu, m, p2, s2
            else:
                # Sparsam: Bringt eine Runde keine bessere Note, bringen weitere
                # meist auch nichts (GEMESSEN: 6 -> 6 -> 5) - abbrechen.
                break

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
    stimme = erfolg.waehlen(Path(kanal_pfad).stem, 'stimme', stimmen)
    zeile = lambda z: ' '.join(f'*{w}*' if any(w.strip('.,!?').lower() == s.lower() for s in
                                                ' '.join(entwurf['schluesselwoerter']).split()) else w
                                for w in z.split())
    skript = {
        'kanal': kanal['name'], 'thema': entwurf['thema'],
        'titel': [zeile(entwurf['titel_zeile1']), zeile(entwurf['titel_zeile2'])],
        'stimme': stimme, 'tempo': 1.05, 'teile': entwurf['teile'],
        'posten_ny': kanal.get('posten_ny', '15:00'),
        'laenge_s': kanal.get('laenge_s', [62, 90]),
        'regeln': kanal.get('_regeln', []),
        'winkel': kanal.get('_winkel', ''), 'format': kanal.get('format', 'ranking'),
        'story': story,
        'hintergrund_suche': kanal.get('hintergrund_suche', ''),
        'musik_suche': kanal.get('musik_suche', []),
        'bilder': wiki_fotos,
        'beschreibung': entwurf['beschreibung'] + '\nClips: Pixabay'
                        + (''.join(f"\nSource: Wikipedia - {q['name']} (CC BY-SA)" for q in quellen
                                   if q.get('quelle') == 'Wikipedia')), 'hashtags': entwurf['hashtags'],
        'pruefung': pruefung, 'quellen': [q['url'] for q in quellen if q.get('url')], 'modell': modell, 'sekunden_ki': round(time.time() - t0, 1),
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
    main(sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else '') or None)
