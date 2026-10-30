"""Jede fertige Einstellung gegen ihren Sprechtext pruefen, ohne Titel-/Untertitelhilfe."""
import io
import hashlib
import json
import math
import re
from pathlib import Path
import subprocess
import tempfile

VERSION = '2026-10-15.1'
# 2026-10-13.1 ist inhaltlich gleich, nur strenger (ohne Ausnahme fuer den Like/Teilen-Aufruf):
# echte Pruefergebnisse dieser Version bleiben gueltig (15.10.: sonst galt ein fertiges Business-
# Video faelschlich als "nicht geprueft").
GUELTIGE_VERSIONEN = {VERSION, '2026-10-13.1'}
MINIMUM = 7
VORGEPRUEFT_MAX = 4  # = bauen.ARCHIV_MAX
GRUPPE = 1  # Ein Bild je Urteil: Lite vertauschte in der Liveprobe Bilder in Sechsergruppen.
SCHEMA = {'type': 'OBJECT', 'properties': {'pruefung': {'type': 'ARRAY', 'items': {
    'type': 'OBJECT', 'properties': {
        'index': {'type': 'INTEGER'}, 'gesehen': {'type': 'STRING'}, 'note': {'type': 'INTEGER'},
        'passt': {'type': 'BOOLEAN'}, 'grund': {'type': 'STRING'}, 'erforderliches_bild': {'type': 'STRING'}},
    'required': ['index', 'gesehen', 'note', 'passt', 'grund', 'erforderliches_bild']}}},
    'required': ['pruefung']}


def aufruf(text):
    """Sprechphase ist der reine Like/Teilen/Speichern-Aufruf (Shorts-Ende).

    26.10.2026: der feste gesprochene Zusatz (texte.SCHLUSS_GESPROCHEN: Kommentarfrage + Folgen) gehoert
    zum Aufruf - mit ihm laege die Phase ueber 14 Woerter und das Schlussbild fiele aus der Ausnahme."""
    import texte
    t = text.lower()
    for zusatz in texte.SCHLUSS_GESPROCHEN.values():
        t = t.replace(zusatz.lower(), ' ')
    return all(w in t for w in ('like', 'share', 'save')) and len(t.split()) <= 14


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


KONTEXT_MAX = 2400  # Zeichen Erzaehltext je Bildurteil; ein Short (~800) bleibt vollstaendig


def erzaehlkontext(erzaehlung, phase_text, n=KONTEXT_MAX):
    """Erzaehltext rund um die gepruefte Phase.

    GEMESSEN 24.10.2026 (KI-Langvideo 40104699545): jedes der ~70 Einzelurteile trug den ganzen Langvideo-Text
    (~6.900 Zeichen) - Groq-Vision lehnte JEDEN Auftrag als zu gross ab (ValueError), bei Gemini-503 gab es
    darum gar kein Urteil, das fertige Video blieb gesperrt. Kontext dient nur Begriffen und Plattform."""
    if len(erzaehlung) <= n:
        return erzaehlung
    i = erzaehlung.find(phase_text[:120].strip())
    mitte = (i if i >= 0 else 0) + len(phase_text) // 2
    a = max(0, min(mitte - n // 2, len(erzaehlung) - n))
    b = a + n
    teil = erzaehlung[a:b]
    if a:
        teil = teil.split(' ', 1)[-1]
    if b < len(erzaehlung):
        teil = teil.rsplit(' ', 1)[0]
    return ('... ' if a else '') + teil + (' ...' if b < len(erzaehlung) else '')


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
    # Eichung 15.10.2026: Selbst beim vom Nutzer freigegebenen Louis-Vuitton-Video lehnte der Pruefer
    # beide Like/Teilen/Speichern-Einstellungen ab. Dort gibt es nichts zu illustrieren - offen
    # ausnehmen statt eine Note zu erfinden; ausgenommene Indizes stehen im Ergebnis.
    ergebnis['ausgenommen'] = [x['index'] for x in slots if aufruf(x['phase_text'])]
    slots = [x for x in slots if x['index'] not in ergebnis['ausgenommen']]
    # Nutzer 30.10.2026 (Mittelweg): Archivclips hat die Clipauswahl schon Standbild gegen Satz bewertet (>= 7/10).
    # Der Schlusspruefer sah danach nur den gemalten Frame und lehnte echte Archivszenen erneut ab.
    ergebnis['vorgeprueft'] = [x['index'] for x in slots
                               if type(x.get('vorgeprueft')) is int and x['vorgeprueft'] >= MINIMUM][:VORGEPRUEFT_MAX]
    slots = [x for x in slots if x['index'] not in ergebnis['vorgeprueft']]
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
                              'whole_spoken_phase': s['phase_text'], 'time_s': round(s['s'], 2),
                              **({'editor_logo_badge': True} if s.get('logo') else {}),
                              **({'opening_reaction_shot': True} if s.get('reaktion') else {})} for s in teil]
                    auftrag = (prompts.DATEN + 'TASK: Independently verify narration-to-image relevance. '
                        'Image i corresponds only to item i below. These are actual frames cropped to remove '
                        'branding and subtitles. Do NOT infer the image from narration or a planned scene. '
                        'FIRST describe the visible subject and action in gesehen; THEN compare to the speech. '
                        'An attractive painted style, matching color, software name, captions, generic office '
                        'worker or vague metaphor are NOT evidence of a match. For software steps/functions '
                        'we need the actual interface, documented example, or a clearly explanatory diagram '
                        'showing that specific operation. A documented, legible command tutorial matches '
                        'narration recommending installation or a command; do not require execution output '
                        'unless the speech claims an actual measured result. An illustrative diagram with '
                        'concrete labels and values can explain structure without being a live software test. '
                        # 16.10.2026: Docling-/Keynote-/Bigarrow-Einzelfaelle durch allgemeine Regeln ersetzt.
                        'A merely related object, place or blank container does not show the narrated operation; '
                        'a face alone cannot demonstrate a software function. A host may introduce a '
                        'question or ask viewers to engage, but cannot substitute for a technical explanation. '
                        'An engagement request is not an app tutorial: recognizable like, share and bookmark '
                        'icons or an engaging presenter can match it; do not require a simulated button press. '
                        'Check the whole phase as context; the slot can contain only part of a sentence. '
                        'For overlay tools the visible arrow, outline box or sign is the demonstrated operation; '
                        'the background app is not the narrated task. '
                        'Judge the actual marks, not just the background app category. Do not demand every '
                        'operation from the whole phase in a slot containing only some words. '
                        'Use the video context for platform and terms, not to invent visible evidence. '
                        'Nonvisual limitations such as no AI inside or no automatic clicking cannot be proven '
                        'from pixels: the independent source check covers their factual truth. For those lines '
                        'require a relevant view of the exact helper or human-control workflow without a '
                        'contradictory visual; do not demand visual proof of an absent internal component. '
                        # 26.10.2026: Squibb erhielt 2/10 u.a. wegen unserer 1859-Zahlenkarte und
                        # Untertiteln; unbekannte gemalte Gesichter galten als echte Gruender.
                        'Historical illustrations show the narrated action or object in a plausible era '
                        'and setting, never proof of exact historical identity, address or event from pixels. '
                        'Ordinary fictional people are allowed; do not infer a real-person likeness from '
                        'an anonymous painted face. A generic scene missing the narrated action still fails. '
                        + prompts.ABSTRAKTE_EREIGNISSE +
                        'Generated artwork must be unlettered. Actual frames can contain editorial titles, '
                        'subtitles, logo badges and number/date cards added after generation. Clearly separate '
                        'overlays are not lettering painted into the scene: ignore them as both evidence of '
                        'relevance and reasons for rejection. Scene-embedded garbled text remains a defect. '
                        'For story illustrations, never require a brand name, logo, date or recognizable founder. '
                        # 16.10.2026 (Coca-Cola, 2/10): unser eigenes Abschnittslogo galt als verbotenes Logo.
                        'A shot marked editor_logo_badge carries the company logo badge added by our editor '
                        'at the section start: ignore that badge and judge only the illustration under it. '
                        # GEMESSEN 29.10.2026 (KI 40949553360): das gewollte Hook-Gesicht (Nutzer: "Gesicht mit starker
                        # Emotion") bekam 2/10 "nur ein ueberraschter Mann, kein Bezug zu ChatGPT-Prompts".
                        'A shot marked opening_reaction_shot is the deliberate first-second hook: a close-up face '
                        'reacting to the spoken opening. Judge whether the visible emotion fits the feeling of '
                        'those words (shock, frustration, disbelief); it need not explain the topic. '
                        'Judge visual meaning only, independent of anatomy, style, audio or prior ratings. '
                        'Score1-3 wrong/unrelated,4-6 vague/partial,7-10 directly useful visual explanation. '
                        'Set passt=false when below7 or the operation is not visible. grund must name the '
                        'visible evidence and the exact spoken operation it matches or fails. On rejection '
                        'erforderliches_bild describes a feasible relevant replacement. Return every index '
                        'exactly once in given order. German findings; only the schema JSON.\n'
                        + json.dumps({'video_context':{'subject':skript.get('thema',''),
                            'narration':erzaehlkontext(' '.join(t['text'] for t in skript.get('teile',[])),
                                                       teil[0]['phase_text'])},
                            'shots':daten}, ensure_ascii=False))
                    einzelkey = ki_speicher.cache_key(VERSION+code+auftrag,SCHEMA,SEHEN,.1,
                        'bildbezug-einzeln',[hashlib.sha256(b).hexdigest() for b in bilder])
                    einzeltreffer = ki_speicher.cache_lesen(einzelkey,SCHEMA,SEHEN)
                    if einzeltreffer:
                        d,modell = einzeltreffer
                    else:
                        import bildvision
                        d, modell = bildvision.mit_ausweichweg(
                            lambda: gemini(auftrag, SCHEMA, bilder=bilder, modelle=SEHEN, temperatur=.1),
                            auftrag, SCHEMA, bilder[0])
                    if [e.get('index') for e in d.get('pruefung', [])] != [s['index'] for s in teil]:
                        raise ValueError('Pruefantwort laesst Einstellungen aus oder verwechselt Bilder')
                    if not einzeltreffer and ki_speicher.schema_ok(d,SCHEMA) and all(
                            1<=e['note']<=10 and e['gesehen'].strip() and e['grund'].strip() for e in d['pruefung']):
                        # Ein spaeterer API-Ausfall verwirft nicht die bereits echten Einzelurteile.
                        # Bindung an extrahierte Bildbytes UND exakten Sprechtext, keine Fake-Abdeckung.
                        ki_speicher.cache_schreiben(einzelkey,d,modell,SCHEMA)
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
    if not isinstance(d, dict) or d.get('version') not in GUELTIGE_VERSIONEN or d.get('video_sha256') != sha:
        return ['Bild-Text-Pruefung fehlt oder gehoert nicht zur aktuellen Videodatei']
    if d.get('ok') is not True or d.get('befunde') != [] or not d.get('pruefung'):
        return d.get('befunde') or ['Bild-Text-Pruefung nicht bestanden']
    n = d.get('einstellungen')
    if type(n) is not int or n < 1:
        return ['Bild-Text-Pruefung: Abdeckung fehlt']
    aus = d.get('ausgenommen') or []
    if not isinstance(aus, list) or len(aus) > 3 or any(type(i) is not int for i in aus):
        return ['Bild-Text-Pruefung: ungueltige Ausnahmen']
    vor = d.get('vorgeprueft') or []
    if not isinstance(vor, list) or len(vor) > VORGEPRUEFT_MAX or any(type(i) is not int for i in vor):
        return ['Bild-Text-Pruefung: ungueltige Vorpruefungen']
    return bewerten(d['pruefung'], [{'index': i} for i in range(n) if i not in aus and i not in vor])


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
