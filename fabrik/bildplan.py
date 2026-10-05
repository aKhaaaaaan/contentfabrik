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
        'index': {'type': 'INTEGER'}, 'bildmodus': {'type': 'STRING', 'enum': ['foto', 'stock', 'illustration', 'karte', 'demo']},
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


def vorbereiten(s, laengen, woerter, cache=None):
    from skript import gemini
    import lernen
    from rendercache import signatur
    zeitplan = slots(s, laengen, woerter)
    key = signatur([s['teile'], laengen, s.get('bilder', []), prompts.VERSION,
                    lernen.redaktionsregeln(), Path(__file__).read_text(encoding='utf-8')])
    alt = (cache or {}).get('bildplan') or {}
    daten = alt.get('einstellungen') if alt.get('key') == key else None
    if daten is None:
        auftrag = (prompts.DATEN + prompts.SZENEN + '\nTASK: Plan the actual visual edit, NOT new narration. '
            'Each timed slot below needs a distinct relevant shot, within its original spoken phase. '
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
            'Its gallery has three different transparency examples, ONE group-photo example '
            'and two text-rendering examples. Do not plan several different group-photo demos; '
            'for extra reference/editing explanation slots use labelled conceptual illustrations '
            'of a human working with portraits or indicating an editing area. '
            'When explaining abstract capabilities, illustration may show the HUMAN problem or '
            'workflow (a pile of mail, a creator arranging photographs, original presenter explaining), '
            'never a fabricated tool screen or claimed output. Such visuals are explicitly labelled '
            'ILLUSTRATION by the renderer. Do not demand demo for a repository with only benchmarks '
            'or code; its documentation is not a live demonstration. Avoid repeated cards or identical '
            'demo imagery. Every available photograph may be used only ONCE; after an archival '
            'photo use an illustrative object/action detail, not another nonexistent photograph '
            'of that same event. Do not plan foto unless the supplied metadata actually supports '
            'the spoken subject and era. foto refers to the '
            'available indexed photo metadata; illustration is useful when no genuine photo fits. '
            'Return EXACTLY one entry per slot, same integer index. motiv states the distinct visible '
            'subject/action. No extra words or factual assertions in the narration.\n' + json.dumps({
                'slots': zeitplan, 'phases': s['teile'], 'photos': s.get('bilder', []),
                'editorial_feedback': lernen.redaktionsregeln()}, ensure_ascii=False))
        d, modell = gemini(auftrag, SCHEMA)
        daten = d['einstellungen']
        print('Gemini-Bildplan:', modell, '| Einstellungen:', len(daten))
    if len(daten) != len(zeitplan) or [d.get('index') for d in daten] != list(range(len(zeitplan))):
        raise ValueError('Bildplan deckt nicht alle Sprechphasen lueckenlos ab')
    aus = []
    for slot, d in zip(zeitplan, daten):
        if d.get('bildmodus') not in ('foto', 'stock', 'illustration', 'karte', 'demo') or not d.get('szene') or not d.get('motiv'):
            raise ValueError('Bildplan enthaelt eine leere oder ungueltige Einstellung')
        t = copy.deepcopy(s['teile'][slot['phase']])
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
