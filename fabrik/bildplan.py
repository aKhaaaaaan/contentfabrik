"""Mehrere echte Einstellungen je Sprechphase; Ton und Wortzeiten bleiben erhalten."""
import copy
import hashlib
import json
import math
from pathlib import Path
import dramaturgie
import prompts

SCHEMA = {'type': 'OBJECT', 'properties': {'einstellungen': {'type': 'ARRAY', 'items': {
    'type': 'OBJECT', 'properties': {
        'index': {'type': 'INTEGER'}, 'bildmodus': {'type': 'STRING', 'enum': ['foto', 'stock', 'illustration', 'karte', 'demo', 'figur', 'asset']},
        'asset': {'type': 'STRING'},
        'figur': {'type': 'BOOLEAN'},
        'suche': {'type': 'STRING'}, 'szene': {'type': 'STRING'}, 'motiv': {'type': 'STRING'}},
    'required': ['index', 'bildmodus', 'suche', 'szene', 'motiv']}}}, 'required': ['einstellungen']}


def slots(s, laengen, woerter):
    ziel = 8 if dramaturgie.videoformat(s) == 'lang' else 4.5
    aus, start = [], 0.0
    for phase, (t, dauer) in enumerate(zip(s['teile'], laengen)):
        anzahl = max(1, math.ceil(dauer / ziel))
        for j in range(anzahl):
            a, b = start + dauer * j / anzahl, start + dauer * (j + 1) / anzahl
            text = ' '.join(w['w'] for w in woerter if a <= (w['s'] + w['e']) / 2 < b)
            aus.append({'index': len(aus), 'phase': phase, 's': a, 'dauer_s': b - a,
                        'text': text or t['text'], 'phase_text': t['text']})
        start += dauer
    return aus


ETAPPE = 30


def etappen(zeitplan, groesse=ETAPPE):
    """GEMESSEN 08.10.2026 (Langvideo-Pilot 37826232160): fuer ~80 Einstellungen lieferte das
    Lite-Modell nur 24 -> 'deckt nicht alle Sprechphasen ab', Versuch verloren. Lange Plaene
    darum in Etappen; ein Short (<= 30 Einstellungen) bleibt EIN Auftrag wie bisher."""
    return [zeitplan[i:i + groesse] for i in range(0, len(zeitplan), groesse)] or [[]]


# GEMELDET 10.10.2026 (Business-Short Netflix): „Die Motive passen wenig zu den Woertern."
# Gemessen: "streams overtook DVD shipments" -> jemand oeffnet einen DVD-Umschlag; "$7.99 a month"
# -> Kalender; Like/Share-Satz -> Blick auf die Uhr. Den Plan machte Flash-Lite (schwaechstes Modell).
# Planen jetzt mit starken Modellen zuerst, Lite nur als Rueckfall; danach eine Bezugspruefung.
PLANEN = ['gemini-3.8-flash', 'gemini-flash-latest', 'gemini-3.6-flash', 'gemini-3.5-flash',
          'gemini-flash-lite-latest', 'gemini-3.5-flash-lite']
BEZUG_MIN = 7
BEZUG_SCHEMA = {'type': 'OBJECT', 'properties': {'pruefung': {'type': 'ARRAY', 'items': {
    'type': 'OBJECT', 'properties': {'index': {'type': 'INTEGER'}, 'note': {'type': 'INTEGER'},
                                     'motiv': {'type': 'STRING'}, 'szene': {'type': 'STRING'},
                                     'suche': {'type': 'STRING'}},
    'required': ['index', 'note', 'motiv', 'szene', 'suche']}}}, 'required': ['pruefung']}


def bezug_pruefen(gemini, teil, daten):
    """Vor dem Malen: zeigt jedes geplante Motiv, was in seinem Slot GESAGT wird? Schwache
    Illustrations-Motive (Note < BEZUG_MIN) werden durch einen woertlicheren Vorschlag ersetzt.
    Faellt die Pruefung aus, bleibt der Plan unveraendert (kein Abbruch)."""
    plan = {d['index']: d for d in daten}
    eintraege = [{'index': x['index'], 'spoken_words': x['text'], 'planned_motif': plan[x['index']].get('motiv'),
                  'planned_scene': plan[x['index']].get('szene')}
                 for x in teil if plan.get(x['index'], {}).get('bildmodus') in ('illustration', 'stock', 'foto')]
    if not eintraege:
        return daten, 0
    try:
        d, _ = gemini(prompts.DATEN + prompts.SZENEN
                      + '\nTASK: For each slot, rate 1-10 how directly the planned image shows what its spoken words '
                        'say: the named subject, action, place or consequence a viewer hears at that moment. A loosely '
                        'related or opposite image (e.g. opening a DVD envelope while hearing that streaming overtook '
                        'DVDs) scores low. For every score below ' + str(BEZUG_MIN) + ', give a better motif (2-5 words), '
                        'a 20-45 word painted scene that literally shows the spoken words, and 2-4 search words. For a '
                        'number, price or statistic, show the people or place it affects doing the concrete action. '
                        'Keep good slots unchanged (repeat their motif/scene). Return every slot.\n'
                      + json.dumps(eintraege, ensure_ascii=False), BEZUG_SCHEMA, modelle=PLANEN)
    except Exception as e:  # Pruefung ist Verbesserung, kein Pflichtschritt
        print('Bezugspruefung nicht verfuegbar:', str(e)[:100])
        return daten, 0
    ersetzt = 0
    for p_ in d.get('pruefung', []):
        alt = plan.get(p_.get('index'))
        if alt and alt.get('bildmodus') in ('illustration', 'stock', 'foto') and p_.get('note', 10) < BEZUG_MIN \
                and p_.get('szene') and p_.get('motiv'):
            alt.update(motiv=p_['motiv'][:80], szene=p_['szene'][:400], suche=p_.get('suche') or alt.get('suche'),
                       bildmodus='illustration')
            ersetzt += 1
    print(f'Bezugspruefung: {ersetzt} von {len(eintraege)} Motiven woertlicher gemacht')
    return daten, ersetzt


def _planen(gemini, modelle, auftrag, indizes):
    """Ein Bildplan-Auftrag; bei Ueberlast oder unvollstaendiger Antwort genau ein neuer Versuch."""
    import time
    for runde in range(2):
        try:
            d, modell = gemini(auftrag, SCHEMA, modelle=modelle)
        except RuntimeError as e:
            # GEMESSEN 08.10.2026 (Lauf 37784030675): Gemini kurz ueberlastet, der Groq-Ausweg
            # war fuer den Bildplan zu gross -> Bau weg. Nach kurzer Pause Gemini erneut.
            if runde:
                raise
            print('Bildplan: Gemini nicht erreichbar, neuer Versuch in 20 s -', str(e)[:120])
            time.sleep(20)
            continue
        daten = d['einstellungen']
        print('Gemini-Bildplan:', modell, '| Einstellungen:', len(daten), f'(erwartet {len(indizes)})')
        if [x.get('index') for x in daten] == indizes:
            return daten
        print('Bildplan unvollstaendig - neuer Versuch')
    return daten  # die Pruefung unten meldet die Luecke


def demo_material(s):
    """Echte README-Bilder je Quellseite fuer den Bildplaner (nur Werkzeug-Seiten auf GitHub/HF)."""
    urls = []
    for t in s['teile']:
        u = t.get('quelle_url')
        if u and u not in urls and ('github.com/' in u or 'huggingface.co/' in u):
            urls.append(u)
    aus = []
    try:
        import bauen
        for u in urls[:3]:
            medien = bauen.readme_medien(u) or []
            if medien:
                aus.append({'source_url': u, 'media': [{'file': l.rsplit('/', 1)[-1], 'alt': a,
                                                        'animated': l.lower().endswith('.gif')}
                                                       for l, a in medien[:8]]})
    except Exception as e:  # Netz weg: Plan ohne Liste wie bisher
        print('README-Bilder nicht abrufbar:', str(e)[:100])
    return aus


def vorbereiten(s, laengen, woerter, cache=None):
    from skript import gemini, SEHEN
    import lernen
    import bibliothek
    from rendercache import signatur
    zeitplan = slots(s, laengen, woerter)
    key = signatur([s['teile'], laengen, s.get('bilder', []), prompts.VERSION,
                    lernen.redaktionsregeln(), bibliothek.signatur().decode('utf-8'), Path(__file__).read_text(encoding='utf-8')])
    alt = (cache or {}).get('bildplan') or {}
    daten = alt.get('einstellungen') if alt.get('key') == key else None
    # Die menschlich kontrollierte Regie ist verbindlich und braucht keinen
    # zweiten KI-Auftrag, der dieselbe Bildfolge lediglich wieder ueberschreibt.
    if daten is None and all(t.get('bildfolge') and all(
            all(v.get(k) for k in ('bildmodus', 'suche', 'szene', 'motiv'))
            for v in t['bildfolge']) for t in s['teile']):
        daten, zaehler = [], {}
        for slot in zeitplan:
            phase = slot['phase']
            j = zaehler.get(phase, 0)
            zaehler[phase] = j + 1
            vorgaben = s['teile'][phase]['bildfolge']
            if j >= len(vorgaben):
                raise ValueError(f'Phase {phase}: redaktionelle Bildfolge zu kurz fuer die gemessene Stimme')
            daten.append(dict(vorgaben[j], index=slot['index']))
        print('Redaktioneller Bildplan | Einstellungen:', len(daten))
    if daten is None:
        auftrag = (prompts.DATEN + prompts.SZENEN + '\nTASK: Plan the actual visual edit, NOT new narration. '
            'Each timed slot below needs a distinct relevant shot, within its original spoken phase. '
            'Keep each szene to 20-22 English words, motiv to 2-5 words. '
            'Prefer asset for a genuinely relevant approved library illustration. Set asset to its '
            'exact id from illustration_library; use only this channel. Do not use a library image '
            'just to fill time when its subject does not match. Illustrative scenes are the visual '
            'default requested by the user; genuine demos are brief evidence of actual tool functions. '
            'Introduce the original channel presenter in the opening and bring the same identity '
            'back during the story in useful actions, not only the closing CTA. Prefer presenter '
            'library assets; for a new illustration involving our presenter set figur=true so the '
            'reference image is actually used. Business: blue-eyed man with fedora, grey suit, dark '
            'tie and gold pocket watch. AI Tools: black-haired man with black leather jacket and '
            'cyan glowing glasses. Never use the presenter as a named real historical founder. '
            'Use overview, object detail, visible process, comparison or outcome when supported. '
            'A zoom, different crop or title change is NOT a new motif. Never use unrelated candles, '
            'abstract loops or background-only frames to fill missing imagery. Every shot must '
            'illustrate the words spoken in that slot. For historical facts use genuine matching '
            'photos or clearly illustrative original scenes, never pretend a fictional presenter '
            'is a real founder. Illustrations: original painted urban open-world-game poster look, '
            'strong contours and cinematic light; no copied game characters, logos or scenes. '
            'Keep generated cards and props unlettered, use simple floral motifs, no numerals or '
            'card indices. Prefer clear object compositions; avoid crowded hands and small shelf '
            'packaging. Vary gaze and pose naturally when a fictional presenter is useful. '
            'Use the fictional presenter only when the slot actually benefits from a presenter. '
            'For AI tools use karte only for brief identification, then demo for genuine screenshots '
            'or example outputs from that exact source URL. Do not invent a tool result using stock '
            'or illustration. For Qwen-Image prefer demo: its model card has actual image examples. '
            'Its gallery has three different transparency examples and ONE group-photo example. '
            'Benchmark overviews and generated scientific-chart art are NOT useful demos. '
            'Do not plan several different group-photo demos; '
            'for extra reference/editing explanation slots use labelled conceptual illustrations '
            'of a human working with portraits or indicating an editing area. '
            'When explaining abstract capabilities, illustration may show the HUMAN problem or '
            'workflow (a pile of mail, a creator arranging photographs, original presenter explaining), '
            'never a fabricated tool screen or claimed output; the description discloses AI '
            'illustrations. Do not demand demo for a repository with only benchmarks '
            'or code; its documentation is not a live demonstration. Avoid repeated cards or identical '
            'demo imagery. Every available photograph may be used only ONCE; after an archival '
            'photo use an illustrative object/action detail, not another nonexistent photograph '
            'of that same event. Do not plan foto unless the supplied metadata actually supports '
            'the spoken subject and era. foto refers to the '
            'available indexed photo metadata; illustration is useful when no genuine photo fits. '
            'Return EXACTLY one entry per slot, same integer index. motiv states the distinct visible '
            'subject/action. No extra words or factual assertions in the narration.\n'
            # GEMELDET 09.10.2026 (Aurelio-Short, Nutzernote 6/10): „Fotos, die nicht mit dem Text
            # zusammenhaengen" - 21 Symbolbilder (Sparschwein, Muenzen, Schluessel), obwohl die README
            # ein demo.gif mit genau den genannten Funktionen hatte.
            'TOOL DEMO MATERIAL lists real README images/animations of the tool. When it is not empty, '
            'every slot whose narration names a concrete feature, screen, output or result of the tool '
            'MUST use demo (aim for at least a third of all slots); an animated demo yields several '
            'different stills. Never show symbolic props (piggy banks, coins, keys, stamps, generic '
            'paperwork) for a concrete tool feature. Use illustration for the human problem, the hook, '
            'the presenter and the call to action.\n')
        kontext = {
                'tool_demo_material': demo_material(s),
                'phases': s['teile'], 'photos': s.get('bilder', []),
                # Bibliotheksbilder sind Hochformat - im Langvideo (16:9) waeren sie beschnitten.
                'illustration_library': [b for b in bibliothek.katalog() if b['kanal'] == s.get('kanal')]
                                        if dramaturgie.videoformat(s) == 'short' else [],
                'editorial_feedback': lernen.redaktionsregeln()}
        daten = []
        for teil in etappen(zeitplan):
            neu = _planen(gemini, PLANEN, auftrag + json.dumps(dict(kontext, slots=teil), ensure_ascii=False),
                          [x['index'] for x in teil])
            neu, _ = bezug_pruefen(gemini, teil, neu)
            daten += neu
    if len(daten) != len(zeitplan) or [d.get('index') for d in daten] != list(range(len(zeitplan))):
        raise ValueError('Bildplan deckt nicht alle Sprechphasen lueckenlos ab')
    aus = []
    pro_phase = {}
    for slot, d in zip(zeitplan, daten):
        if d.get('bildmodus') not in ('foto', 'stock', 'illustration', 'karte', 'demo', 'figur', 'grafik', 'asset') or not d.get('szene') or not d.get('motiv'):
            raise ValueError('Bildplan enthaelt eine leere oder ungueltige Einstellung')
        t = copy.deepcopy(s['teile'][slot['phase']])
        j = pro_phase.get(slot['phase'], 0)
        pro_phase[slot['phase']] = j + 1
        vorgaben = t.get('bildfolge', [])
        if j < len(vorgaben):
            d = dict(d, **vorgaben[j])
            if d.get('demo_url'):
                t['demo_url'] = d['demo_url']
            if 'grafik_variante' in d:
                t['grafik_variante'] = d['grafik_variante']
        if d.get('bildmodus') == 'asset':
            try:
                bibliothek.bild(d.get('asset'), s.get('kanal'))
                t['asset'] = d['asset']
            except ValueError:
                # GEMESSEN 08.10.2026 (Lauf 37753715598): ein fuer den Kanal nicht freigegebenes
                # Bibliotheksbild liess den ganzen Bau abbrechen. Szene stattdessen neu malen.
                d = dict(d, bildmodus='illustration')
        if 'figur' in d:
            t['figur'] = d['figur']
        t.update({k: d[k] for k in ('bildmodus', 'suche', 'szene', 'motiv')})
        t['text'] = slot['text']
        t['_phase'] = slot['phase']
        aus.append(dict(slot, teil=t))
    return aus, {'key': key, 'einstellungen': daten}


def material_id(pfad):
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()


def pruefen(daten, dauer, art='short'):
    befunde = []
    shots = daten.get('einstellungen') or []
    if not shots:
        return {'befunde': ['Kein nachweisbarer Bildablauf vorhanden']}
    ende = 0.0
    letzter, haltezeit = None, 0.0
    material = set()
    for shot in shots:
        d = shot.get('dauer_s', 0)
        if not isinstance(d, (int, float)) or isinstance(d, bool) or not math.isfinite(d) or d <= 0:
            befunde.append('Ungueltige Bilddauer')
            continue
        if abs(shot.get('s', -1) - ende) > .1:
            befunde.append('Bildablauf hat Luecke oder Ueberlappung')
        if d > (10 if art == 'lang' else 6):
            befunde.append('Einstellung zu lang ohne neues Motiv')
        if not shot.get('material_id') or shot.get('material_art') == 'hintergrund':
            befunde.append('Sprechabschnitt ohne passendes Hauptbild')
        else:
            material.add(shot['material_id'])
            haltezeit = haltezeit + d if letzter == shot['material_id'] else d
            letzter = shot['material_id']
            if haltezeit > (10 if art == 'lang' else 6):
                befunde.append('Gleiches Motiv trotz mehrerer Einstellungen zu lange gehalten')
        ende = shot.get('s', ende) + d
    minimum = math.ceil(dauer / (16 if art == 'lang' else 7))
    if len(material) < minimum:
        befunde.append(f'Zu wenig unterschiedliche Motive: {len(material)} statt mindestens {minimum}')
    if abs(ende - dauer) > .15:
        befunde.append('Bildablauf deckt nicht die ganze Videolaenge ab')
    return {'befunde': list(dict.fromkeys(befunde)), 'einstellungen': len(shots),
            'motive': len(material), 'motive_min': minimum}
