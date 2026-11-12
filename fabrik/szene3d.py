"""Claude als 3D-Regisseur (Probe, Nutzer 12.11.2026: "Bekommt Blender auch Prompts?" -> "deine Empfehlungen").

Claude bekommt einen Satz aus einem Skript und liefert KEINEN Code, sondern eine Szenenbeschreibung (JSON): Objekte
aus Grundformen mit Massen in Metern, Material, Licht, Kamera. fabrik/blenderprobe.py (Stil "szene") baut daraus die
Szene im Look des Nutzer-Favoriten (Runde 2, warmes Holz) - so fuehrt GitHub nie fremden Code aus. pruefen()
begrenzt jeden Wert. Claude laeuft ueber das Abo (claude_ki, CLAUDE_CODE_OAUTH_TOKEN) - keine Zusatzkosten.

Aufruf: python fabrik/szene3d.py "<Satz>" <ausgabe.json>
"""
import json
import math
import sys

FORMEN = ('box', 'zylinder', 'kugel')
# GEMESSEN 12.11. (Lauf 43300000495): Claude schrieb 'cylinder' (Snowboard-Szene verworfen) - englisch gilt auch
ALIAS = {'cube': 'box', 'cuboid': 'box', 'cylinder': 'zylinder', 'sphere': 'kugel', 'ball': 'kugel'}
MAX_OBJEKTE, MAX_LICHTER = 120, 4
# GEMESSEN 12.11.: Claude setzte 165 W (DC-3) / 135 W (Telefon) -> blass-pastell. Nutzer-Favorit (Runde 2): Chip
# 30+15 W, Vertrag 60+8 W. Gesamtlicht wird anteilig auf hoechstens LICHT_SUMME gedimmt.
LICHT_SUMME = 60.0

SCHEMA = {'type': 'OBJECT', 'required': ['motiv', 'objekte', 'lichter', 'kamera'], 'properties': {
    'motiv': {'type': 'STRING'},
    'objekte': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'required': ['form', 'ort', 'masse', 'farbe'], 'properties': {
        'form': {'type': 'STRING', 'enum': list(FORMEN)},
        'ort': {'type': 'ARRAY', 'items': {'type': 'NUMBER'}},
        'masse': {'type': 'ARRAY', 'items': {'type': 'NUMBER'}},
        'drehung_grad': {'type': 'ARRAY', 'items': {'type': 'NUMBER'}},
        'farbe': {'type': 'ARRAY', 'items': {'type': 'NUMBER'}},
        'rauheit': {'type': 'NUMBER'}, 'metall': {'type': 'NUMBER'}}}},
    'lichter': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'required': ['ort', 'staerke'], 'properties': {
        'ort': {'type': 'ARRAY', 'items': {'type': 'NUMBER'}}, 'staerke': {'type': 'NUMBER'},
        'farbe': {'type': 'ARRAY', 'items': {'type': 'NUMBER'}}}}},
    'kamera': {'type': 'OBJECT', 'required': ['ort', 'ziel', 'brennweite'], 'properties': {
        'ort': {'type': 'ARRAY', 'items': {'type': 'NUMBER'}}, 'ziel': {'type': 'ARRAY', 'items': {'type': 'NUMBER'}},
        'brennweite': {'type': 'NUMBER'}}}}}

BEISPIEL = {'motiv': 'black 40-pin DIP microprocessor chip on a wooden desk',
            'objekte': [{'form': 'box', 'ort': [0, 0, 0.012], 'masse': [0.2, 0.06, 0.018], 'farbe': [0.03, 0.03, 0.035],
                         'rauheit': 0.35},
                        {'form': 'box', 'ort': [-0.095, 0.036, 0.006], 'masse': [0.004, 0.014, 0.0015],
                         'farbe': [0.85, 0.85, 0.82], 'rauheit': 0.2, 'metall': 1},
                        {'form': 'zylinder', 'ort': [-0.092, 0, 0.0215], 'masse': [0.012, 0.012, 0.002],
                         'farbe': [0.08, 0.08, 0.09]}],
            'lichter': [{'ort': [-0.4, -0.3, 0.6], 'staerke': 30, 'farbe': [1, 0.8, 0.6]}],
            'kamera': {'ort': [0.12, -0.42, 0.38], 'ziel': [0, 0, 0.01], 'brennweite': 35}}


def auftrag(satz):
    return f"""You are the 3D set designer for a YouTube Short about business and tech history.
Build ONE clean product-shot scene that literally shows the key object of this spoken sentence:
"{satz}"

Rules:
- A large warm wooden desk/floor already exists at z=0 (top surface). Place objects ON it (z >= 0).
- Build the object from boxes, cylinders and spheres with REAL proportions in meters. Add the characteristic
  details that make it recognizable (e.g. pins, buttons, screen, keys, wheels, labels as colored plates - no text).
- 3 to {MAX_OBJEKTE} objects. Keep it one clear hero object, optionally 1-3 small props. No people, no logos.
- "masse" = full size [x, y, z]; for cylinders [diameter, diameter, height]; for spheres [d, d, d].
- "farbe" = RGB 0..1 (realistic, slightly warm). "rauheit" 0..1, "metall" 0 or 1.
- 1 to {MAX_LICHTER} warm lights near the object ("staerke" in watts, 10-150).
- Camera: portrait 9:16 frame, hero object centered and filling about half the width, looking down ~35-45 degrees.
Example of the format (a chip): {json.dumps(BEISPIEL)}"""


def _zahlen(v, n, lo, hi):
    if not isinstance(v, list) or len(v) != n or any(not isinstance(x, (int, float)) or not math.isfinite(x)
                                                     or not lo <= x <= hi for x in v):
        raise ValueError(f'ungueltige Werte {v!r}')
    return [float(x) for x in v]


def pruefen(d):
    """Grenzen fuer jeden Wert - Blender bekommt nur geprueftes JSON."""
    objekte = d.get('objekte') or []
    if not 1 <= len(objekte) <= MAX_OBJEKTE:
        raise ValueError(f'{len(objekte)} Objekte')
    aus = {'motiv': str(d.get('motiv', ''))[:200], 'objekte': [], 'lichter': []}
    for o in objekte:
        form = ALIAS.get(str(o.get('form', '')).lower(), o.get('form'))
        if form not in FORMEN:
            raise ValueError(f"Form {o.get('form')!r}")
        aus['objekte'].append({'form': form, 'ort': _zahlen(o.get('ort'), 3, -3, 3),
                               'masse': _zahlen(o.get('masse'), 3, 0.0005, 3),
                               'drehung_grad': _zahlen(o.get('drehung_grad') or [0, 0, 0], 3, -360, 360),
                               'farbe': _zahlen(o.get('farbe'), 3, 0, 1),
                               'rauheit': min(1.0, max(0.0, float(o.get('rauheit', 0.5)))),
                               'metall': 1.0 if o.get('metall') else 0.0})
    for l in (d.get('lichter') or [])[:MAX_LICHTER]:
        aus['lichter'].append({'ort': _zahlen(l.get('ort'), 3, -5, 5),
                               'staerke': min(300.0, max(1.0, float(l.get('staerke', 30)))),
                               'farbe': _zahlen(l.get('farbe') or [1, 0.85, 0.7], 3, 0, 1)})
    summe = sum(l['staerke'] for l in aus['lichter'])
    if summe > LICHT_SUMME:
        for l in aus['lichter']:
            l['staerke'] = round(l['staerke'] * LICHT_SUMME / summe, 1)
    k = d.get('kamera') or {}
    aus['kamera'] = {'ort': _zahlen(k.get('ort'), 3, -6, 6), 'ziel': _zahlen(k.get('ziel'), 3, -3, 3),
                     'brennweite': min(120.0, max(18.0, float(k.get('brennweite', 35))))}
    return aus


def main(satz, ziel):
    import claude_ki
    daten, info = claude_ki.schreiben(auftrag(satz), SCHEMA, zeit=240)
    if daten is None:
        sys.exit(f'Claude lieferte keine Szene: {info}')
    szene = pruefen(daten)
    szene['satz'] = satz
    with open(ziel, 'w', encoding='utf-8') as f:
        json.dump(szene, f, ensure_ascii=False, indent=1)
    print(f"Szene: {szene['motiv']} ({len(szene['objekte'])} Objekte, {info})")


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
