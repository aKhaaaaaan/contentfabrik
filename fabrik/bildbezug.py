"""Jede fertige Einstellung gegen ihren Sprechtext pruefen, ohne Titel-/Untertitelhilfe."""
import io
import json
import math
import re
from pathlib import Path
import subprocess
import tempfile

VERSION = '2026-10-13.1'
MINIMUM = 7
GRUPPE = 1  # Ein Bild je Urteil: Lite vertauschte in der Liveprobe Bilder in Sechsergruppen.
SCHEMA = {'type': 'OBJECT', 'properties': {'pruefung': {'type': 'ARRAY', 'items': {
    'type': 'OBJECT', 'properties': {
        'index': {'type': 'INTEGER'}, 'gesehen': {'type': 'STRING'}, 'note': {'type': 'INTEGER'},
        'passt': {'type': 'BOOLEAN'}, 'grund': {'type': 'STRING'}, 'erforderliches_bild': {'type': 'STRING'}},
    'required': ['index', 'gesehen', 'note', 'passt', 'grund', 'erforderliches_bild']}}},
    'required': ['pruefung']}


def bewerten(ergebnisse, slots):
    """Vollstaendige Einzelbefunde; ein fehlender/abgelehnter Slot besteht nie."""
    befunde = []
    ids = [s['index'] for s in slots]
    if not isinstance(ergebnisse, list) or any(not isinstance(e, dict) for e in ergebnisse) \
            or [e.get('index') for e in ergebnisse] != ids:
        return ['Bild-Text-Pruefung deckt nicht alle Einstellungen eindeutig ab']
    for e in ergebnisse:
        n = e.get('note')
        if type(n) is not int or not 1 <= n <= 10 or type(e.get('passt')) is not bool \
                or not isinstance(e.get('gesehen'), str) or not e['gesehen'].strip() \
                or not isinstance(e.get('grund'), str) or not e['grund'].strip():
            befunde.append(f"Einstellung {e['index']}: Bild-Text-Pruefung unvollstaendig")
        elif not e['passt'] or n < MINIMUM:
            befunde.append(f"Einstellung {e['index']}: Bild passt nicht zum Sprechtext ({n}/10): {e['grund'][:300]}")
    return befunde


def frame(video, sekunde, art, ziel):
    from PIL import Image
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{sekunde:.3f}', '-i', str(video),
                    '-frames:v', '1', str(ziel)], check=True, timeout=30,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    with Image.open(ziel) as im:
        im = im.convert('RGB')
        w, h = im.size
        # Die Note muss den sichtbaren Inhalt bewerten, nicht passende Overlaywoerter.
        box = (0, int(h * .16), w, int(h * .65)) if art == 'short' else \
              (0, int(h * .18), w, int(h * .76))
        im = im.crop(box)
        im.thumbnail((768, 768))
        b = io.BytesIO(); im.save(b, 'JPEG', quality=90)
        return b.getvalue()


def pruefen(video, skript, ablauf, ziel):
    import bildplan
    import dramaturgie
    import ki_speicher
    import prompts
    from skript import gemini, SEHEN
    slots = ablauf.get('einstellungen') or []
    sha = bildplan.material_id(video)
    art = dramaturgie.videoformat(skript)
    ergebnis = {'version': VERSION, 'video_sha256': sha, 'videoformat': art,
                'ok': False, 'pruefung': [], 'befunde': [], 'modelle': [], 'einstellungen': len(slots)}
    def speichern():
        ki_speicher.speichern(ziel, ergebnis)
        return ergebnis
    if not slots:
        ergebnis['befunde'] = ['Bild-Text-Pruefung: Bildablauf fehlt']
        return speichern()
    for s in slots:
        if type(s.get('index')) is not int or not isinstance(s.get('phase_text'), str) \
                or not s['phase_text'].strip() or any(type(s.get(k)) not in (float, int)
                or not math.isfinite(s[k]) or s[k] < 0 for k in ('s', 'dauer_s')) or not s['dauer_s']:
            ergebnis['befunde'] = ['Bild-Text-Pruefung: ungueltige Einstellung']
            return speichern()
    code = ki_speicher.hashwert(Path(__file__).read_text(encoding='utf-8'))
    key = ki_speicher.cache_key(VERSION + code + json.dumps(slots, sort_keys=True), SCHEMA, SEHEN, .1, 'bildbezug', sha)
    cached = ki_speicher.cache_lesen(key, SCHEMA, SEHEN)
    if cached:
        d, modell = cached
        ergebnis['pruefung'] = d['pruefung']; ergebnis['modelle'] = [modell]
    else:
        try:
            with tempfile.TemporaryDirectory(prefix='contentfabrik-bildbezug-') as temp:
                for a in range(0, len(slots), GRUPPE):
                    teil = slots[a:a + GRUPPE]
                    bilder = [frame(video, s['s'] + s['dauer_s'] / 2, art, Path(temp) / f"{s['index']}.jpg") for s in teil]
                    daten = [{'index': s['index'], 'spoken_words': s.get('text', ''),
                              'whole_spoken_phase': s['phase_text'], 'time_s': round(s['s'], 2)} for s in teil]
                    auftrag = (prompts.DATEN + 'TASK: Independently verify narration-to-image relevance. '
                        'Image i corresponds only to item i below. These are actual frames cropped to remove '
                        'branding and subtitles. Do NOT infer the image from narration or a planned scene. '
                        'FIRST describe the visible subject and action in gesehen; THEN compare to the speech. '
                        'An attractive painted style, matching color, software name, captions, generic office '
                        'worker or vague metaphor are NOT evidence of a match. For software steps/functions '
                        'we need the actual interface, documented example, or a clearly explanatory diagram '
                        'showing that specific operation. Hardware installation does not show installing a '
                        'Python package. Boxes or blank cards do not show PDF tables, Markdown or JSON export. '
                        'A cupboard does not show converting a document. A person using a scanner can show '
                        'scanning; a face alone cannot demonstrate OCR or parsing. A host may introduce a '
                        'question or ask viewers to engage, but cannot substitute for a technical explanation. '
                        'An engagement request is not an app tutorial: recognizable like, share and bookmark '
                        'icons or an engaging presenter can match it; do not require a simulated button press. '
                        'Check the whole phase as context; the slot can contain only part of a sentence. '
                        'Judge visual meaning only, independent of anatomy, style, audio or prior ratings. '
                        'Score1-3 wrong/unrelated,4-6 vague/partial,7-10 directly useful visual explanation. '
                        'Set passt=false when below7 or the operation is not visible. grund must name the '
                        'visible evidence and the exact spoken operation it matches or fails. On rejection '
                        'erforderliches_bild describes a feasible relevant replacement. Return every index '
                        'exactly once in given order. German findings; only the schema JSON.\n'
                        + json.dumps(daten, ensure_ascii=False))
                    d, modell = gemini(auftrag, SCHEMA, bilder=bilder, modelle=SEHEN, temperatur=.1)
                    if [e.get('index') for e in d.get('pruefung', [])] != [s['index'] for s in teil]:
                        raise ValueError('Pruefantwort laesst Einstellungen aus oder verwechselt Bilder')
                    ergebnis['pruefung'].extend(d['pruefung']); ergebnis['modelle'].append(modell)
            if ki_speicher.schema_ok({'pruefung': ergebnis['pruefung']}, SCHEMA) and all(
                    1 <= e['note'] <= 10 and e['gesehen'].strip() and e['grund'].strip()
                    for e in ergebnis['pruefung']):
                # Vollstaendige negative Urteile ebenfalls sparen; neue Frames/Regeln haben neue Keys.
                ki_speicher.cache_schreiben(key, {'pruefung': ergebnis['pruefung']}, ergebnis['modelle'][0], SCHEMA)
        except Exception as e:
            ergebnis['befunde'] = ['Bild-Text-Pruefung nicht vollstaendig moeglich: ' + type(e).__name__]
            return speichern()
    ergebnis['befunde'] = bewerten(ergebnis['pruefung'], slots)
    ergebnis['ok'] = not ergebnis['befunde']
    return speichern()


def gruende(d, sha):
    if not isinstance(d, dict) or d.get('version') != VERSION or d.get('video_sha256') != sha:
        return ['Bild-Text-Pruefung fehlt oder gehoert nicht zur aktuellen Videodatei']
    if d.get('ok') is not True or d.get('befunde') != [] or not d.get('pruefung'):
        return d.get('befunde') or ['Bild-Text-Pruefung nicht bestanden']
    n = d.get('einstellungen')
    if type(n) is not int or n < 1:
        return ['Bild-Text-Pruefung: Abdeckung fehlt']
    return bewerten(d['pruefung'], [{'index': i} for i in range(n)])


def revision_gruende(sha):
    """Eine echte Neupruefung gilt auch fuer ein bereits zugestelltes aelteres Artefakt."""
    if not isinstance(sha, str) or not re.fullmatch(r'[a-f0-9]{64}', sha):
        return []
    p = Path('verlauf/bildpruefungen') / (sha + '.json')
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        d = None
    return gruende(d, sha)
