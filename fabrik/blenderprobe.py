"""Blender-Probe 12.11.2026 (Nutzer 09.11./11.11.): drei Business-Standbilder 1080x1920 headless rendern und die
Sekunden je Bild messen. Kein Einfluss auf die Produktion.

Die Szenen sind die Faelle, an denen der Bildpruefer bei Business scheitert (AMD 11.11.: 8 generische Szenen):
Vertrag unterschreiben, Chip auf dem Tisch, Produkt im Regal. Nur Blender-Grundformen, keine fremden Modelle,
keine Schrift (Pruefer und Nutzer mochten gemalte Schrift nie).

Aufruf: blender -b -P fabrik/blenderprobe.py -- <ausgabeordner> [samples]
"""
import json
import math
import sys
import time
from pathlib import Path

import bpy

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
AUS = Path(ARGS[0] if ARGS else 'blenderprobe')
SAMPLES = int(ARGS[1]) if len(ARGS) > 1 else 24
# Runde 3 (12.11., Nutzer: "gemalte Blender-Bilder sehen nicht so nice aus - Farbstil wie GTA?"): 'toon' =
# Plakatlook direkt in Blender (Toon-BSDF mit harten Schattenstufen, Freestyle-Tuschelinien, Sonnenuntergang
# Orange gegen Tuerkis, Standard-Farbraum fuer satte Flaechen) statt Malfilter auf einem fertigen Foto.
STIL = ARGS[2] if len(ARGS) > 2 else 'toon'


def leeren():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.cycles.device = 'CPU'
    s.cycles.samples = SAMPLES
    s.cycles.use_denoising = True
    s.render.resolution_x, s.render.resolution_y = 1080, 1920
    s.render.image_settings.file_format = 'JPEG'
    s.render.image_settings.quality = 90
    # Runde 2 (12.11., Nutzer "deine Vorschlaege umsetzen"): Runde 1 war ueberbelichtet - der schwarze Chip
    # wurde grau, alles pastell. Dunkle Welt + kontrastreicher AgX-Look statt heller Umgebung.
    try:
        s.view_settings.look = 'AgX - Punchy'
    except TypeError:
        pass
    welt = bpy.data.worlds.new('welt')
    welt.use_nodes = True
    welt.node_tree.nodes['Background'].inputs[0].default_value = (0.05, 0.03, 0.02, 1)
    welt.node_tree.nodes['Background'].inputs[1].default_value = 0.12
    s.world = welt
    if STIL == 'toon':
        s.view_settings.view_transform = 'Standard'
        s.view_settings.look = 'None'
        s.render.use_freestyle = True
        s.render.line_thickness_mode = 'ABSOLUTE'
        s.render.line_thickness = 3.0
        fs = s.view_layers[0].freestyle_settings
        linien = fs.linesets[0] if len(fs.linesets) else fs.linesets.new('linien')
        linien.select_by_visibility = True
        linien.select_silhouette = linien.select_border = linien.select_crease = True
        # GEMESSEN 12.11. (Lauf 43229413778): ein neues Lineset in der leeren Fabrikszene hat KEINEN Linienstil
        if linien.linestyle is None:
            linien.linestyle = bpy.data.linestyles.new('tusche')
        linien.linestyle.color = (0.02, 0.01, 0.01)
    return s


def stoff(name, farbe, rau=0.5, metall=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    if STIL == 'toon':
        nt = m.node_tree
        nt.nodes.remove(nt.nodes['Principled BSDF'])
        diffus = nt.nodes.new('ShaderNodeBsdfToon')
        diffus.component = 'DIFFUSE'
        diffus.inputs['Color'].default_value = (*farbe, 1)
        diffus.inputs['Size'].default_value = 0.55
        diffus.inputs['Smooth'].default_value = 0.03
        glanz = nt.nodes.new('ShaderNodeBsdfToon')
        glanz.component = 'GLOSSY'
        glanz.inputs['Color'].default_value = (*farbe, 1) if metall else (1, 0.95, 0.85, 1)
        glanz.inputs['Size'].default_value = 0.12 + 0.3 * rau
        glanz.inputs['Smooth'].default_value = 0.03
        mix = nt.nodes.new('ShaderNodeMixShader')
        mix.inputs[0].default_value = 0.65 if metall else 0.1
        nt.links.new(diffus.outputs[0], mix.inputs[1])
        nt.links.new(glanz.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
        return m
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*farbe, 1)
    p.inputs['Roughness'].default_value = rau
    p.inputs['Metallic'].default_value = metall
    return m


def kiste(name, ort, masse, material, kante=0.01):
    bpy.ops.mesh.primitive_cube_add(location=ort)
    o = bpy.context.object
    o.name = name
    o.scale = [m / 2 for m in masse]
    bpy.ops.object.transform_apply(scale=True)
    if kante:
        mod = o.modifiers.new('kante', 'BEVEL')
        mod.width, mod.segments = kante, 3
    o.data.materials.append(material)
    return o


def walze(name, ort, r, h, material, drehung=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=ort, rotation=drehung, vertices=48)
    o = bpy.context.object
    o.name = name
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    return o


def licht(art, ort, staerke, farbe=(1, 0.9, 0.78), groesse=1.0, ziel=(0, 0, 0)):
    daten = bpy.data.lights.new(art + str(ort), art)
    daten.energy, daten.color = staerke, farbe
    if art == 'AREA':
        daten.size = groesse
    o = bpy.data.objects.new(daten.name, daten)
    o.location = ort
    bpy.context.collection.objects.link(o)
    richten(o, ziel)
    return o


def richten(o, ziel):
    from mathutils import Vector
    o.rotation_euler = (Vector(ziel) - o.location).to_track_quat('-Z', 'Y').to_euler()


def kamera(ort, ziel, brennweite=50):
    daten = bpy.data.cameras.new('kamera')
    daten.lens = brennweite
    daten.dof.use_dof = True
    o = bpy.data.objects.new('kamera', daten)
    o.location = ort
    bpy.context.collection.objects.link(o)
    richten(o, ziel)
    from mathutils import Vector
    daten.dof.focus_distance = (Vector(ziel) - Vector(ort)).length
    daten.dof.aperture_fstop = 2.8
    bpy.context.scene.camera = o


def holztisch():
    holz = stoff('holz', (0.16, 0.06, 0.02), 0.4)
    # 12.11.: 3 x 2 m - der Chip-Blick sah oben ueber die Tischkante (dunkler Streifen im Render und im Clip)
    kiste('tisch', (0, 0, -0.03), (8, 8, 0.06), holz, 0.005)


def vertrag():
    holztisch()
    papier = stoff('papier', (0.92, 0.9, 0.84), 0.8)
    for i in range(2):
        b = kiste(f'blatt{i}', (0.02 * i, -0.01 * i, 0.001 + 0.002 * i), (0.42, 0.594, 0.002), papier, 0)
        b.rotation_euler[2] = math.radians(-8 + 5 * i)
    tinte = stoff('tinte', (0.05, 0.05, 0.12), 0.3)
    for i in range(6):  # Zeilen als duenne Striche (keine lesbare Schrift)
        kiste(f'zeile{i}', (0.0, 0.18 - i * 0.05, 0.0062), (0.3 - (i % 3) * 0.05, 0.004, 0.0004), tinte, 0)
    lack = stoff('lack', (0.02, 0.02, 0.02), 0.15)
    gold = stoff('gold', (0.9, 0.65, 0.25), 0.25, 1.0)
    walze('fueller', (0.12, -0.2, 0.012), 0.009, 0.15, lack, (0, math.radians(90), math.radians(35)))
    walze('kappe', (0.19, -0.15, 0.012), 0.0095, 0.03, gold, (0, math.radians(90), math.radians(35)))
    walze('siegel', (-0.14, -0.22, 0.008), 0.035, 0.016, stoff('wachs', (0.55, 0.05, 0.04), 0.4))
    licht('AREA', (-0.8, 0.6, 1.2), 60, (1, 0.78, 0.55), groesse=0.6)
    licht('POINT', (0.6, -0.5, 0.5), 8, (1, 0.55, 0.3))
    kamera((0.15, -0.75, 0.75), (0.02, -0.05, 0.0), 45)


def chip():
    holztisch()
    schwarz = stoff('gehaeuse', (0.03, 0.03, 0.035), 0.35)
    metall = stoff('pin', (0.85, 0.85, 0.82), 0.2, 1.0)
    kiste('chip', (0, 0, 0.012), (0.2, 0.06, 0.018), schwarz, 0.002)
    for seite in (-1, 1):
        for i in range(20):  # 40 Beinchen wie bei einem DIP-Prozessor der 1970er
            x = -0.095 + i * 0.01
            kiste(f'pin{seite}{i}', (x, seite * 0.036, 0.006), (0.004, 0.014, 0.0015), metall, 0)
            kiste(f'fuss{seite}{i}', (x, seite * 0.043, -0.0005), (0.004, 0.0015, 0.012), metall, 0)
    walze('kerbe', (-0.092, 0, 0.0215), 0.006, 0.002, stoff('kerbe', (0.08, 0.08, 0.09), 0.5))
    # Runde 2: Chip liegt AUF der Platine und steht ganz im Bild (Runde 1: zu nah, Platine unscharf daneben)
    # Keine Platine: Nutzer-Favorit (Runde 2) zeigte den Chip allein auf dem Holz (die Platine lag damals versehentlich
    # unter der Tischplatte); Standbild und Projektion brauchen ausserdem dieselbe Geometrie.
    licht('AREA', (-0.4, -0.3, 0.6), 30, (1, 0.8, 0.6), 0.4, ziel=(0, 0, 0))
    licht('AREA', (0.5, 0.4, 0.4), 15, (0.5, 0.7, 1), 0.3, ziel=(0, 0, 0))
    kamera((0.12, -0.42, 0.38), (0.0, 0.0, 0.01), 35)
    bpy.context.scene.camera.data.dof.aperture_fstop = 8


def regal():
    welt = bpy.context.scene.world.node_tree.nodes['Background']
    welt.inputs[0].default_value = (0.06, 0.04, 0.03, 1)
    holz = stoff('regalholz', (0.2, 0.09, 0.03), 0.5)
    for i in range(4):
        kiste(f'brett{i}', (0, 0, i * 0.45), (1.2, 0.35, 0.03), holz, 0.004)
    kiste('rueck', (0, 0.18, 0.7), (1.2, 0.02, 1.45), stoff('wand', (0.25, 0.15, 0.09), 0.8), 0)
    farben = [(0.7, 0.04, 0.02), (0.9, 0.55, 0.02), (0.02, 0.15, 0.55), (0.85, 0.82, 0.7)]
    for reihe in range(3):
        for j in range(7):
            f = farben[(j + reihe) % len(farben)]
            kiste(f'dose{reihe}{j}', (-0.48 + j * 0.16, -0.02, reihe * 0.45 + 0.14), (0.12, 0.12, 0.24),
                  stoff(f'p{reihe}{j}', f, 0.35), 0.008)
    licht('AREA', (0, -1.2, 1.6), 110, (1, 0.82, 0.62), groesse=1.0, ziel=(0, 0, 0.6))
    licht('POINT', (-0.8, -0.6, 0.3), 12, (1, 0.6, 0.35))
    kamera((0.35, -1.75, 0.75), (0, 0, 0.55), 40)


SZENEN = {'vertrag': vertrag, 'chip': chip, 'regal': regal}


def projektion(gemaelde, szene='chip', bilder=120, grad=6, heran=0.40):
    # Nutzer 12.11. abends (letzter Stand): "weniger drehen, dafuer mehr zoomen - das Bild vorher immer von weitem,
    # dann rein zoomen". Start = exakt das ganze Gemaelde (0 Grad, Originalbrennweite: keine Raender), dann weich
    # bis +grad drehen und gleichmaessig +40 % heranfahren (4 s @30 fps); der Zoom waechst mit der Drehung und
    # verdeckt so die ungemalten Raender.
    """Runde 4 (12.11., Nutzer: "kann man die mit Codex gemalten Blender-Motive nicht etwas drehen?"):
    Camera Projection Mapping - das Codex-Gemaelde wird aus der Originalkamera auf dieselbe Geometrie projiziert
    (UV-Project), nur Emission (die Malerei bringt Licht und Schatten mit). Danach dreht die Renderkamera
    +-grad um das Motiv. Groessere Winkel zeigen ungemalte Rueckseiten."""
    from mathutils import Matrix, Vector
    leeren()
    SZENEN[szene]()
    # GEMESSEN 12.11. (Lauf 43277804607): der weite Startblick sah ueber die Tischkante ins Leere - dunkler Streifen
    # (Chip) bzw. Schlieren/schwarze Ecke (Vertrag). Grosser Boden knapp unter dem Tisch: jeder Bildpunkt des
    # Gemaeldes trifft Geometrie (oberer Bildrand trifft bei beiden Kameras nach ~1,7 m auf den Boden).
    kiste('boden', (0, 0, -0.004), (12, 12, 0.002), stoff('boden', (0.2, 0.1, 0.05)), 0)
    s = bpy.context.scene
    s.render.use_freestyle = False
    s.view_settings.view_transform, s.view_settings.look = 'Standard', 'None'
    s.cycles.samples, s.cycles.use_denoising = 4, False
    kam = s.camera
    kam.data.dof.use_dof = False
    projektor = kam.copy()  # bleibt stehen, waehrend die Renderkamera faehrt
    projektor.data = kam.data.copy()
    # GEMESSEN 12.11. (Lauf 43229457145): bei +-12 Grad ohne Zoom Randstreifen links/oben. Jetzt startet die
    # Kamera deckungsgleich mit dem Projektor (weit, randfrei); der wachsende Zoom haelt die Raender draussen.
    s.collection.objects.link(projektor)
    bild = bpy.data.images.load(str(gemaelde))
    mat = bpy.data.materials.new('gemaelde')
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.remove(nt.nodes['Principled BSDF'])
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image, tex.extension = bild, 'EXTEND'
    uv = nt.nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'proj'
    emi = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(uv.outputs[0], tex.inputs['Vector'])
    nt.links.new(tex.outputs['Color'], emi.inputs['Color'])
    nt.links.new(emi.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    for o in [o for o in s.objects if o.type == 'MESH']:
        o.data.uv_layers.new(name='proj')
        o.data.materials.clear()
        o.data.materials.append(mat)
        if max(o.dimensions) > 0.25:  # grosse Flaechen unterteilen, sonst verzerrt die affine UV-Interpolation
            sub = o.modifiers.new('fein', 'SUBSURF')
            sub.subdivision_type, sub.levels, sub.render_levels = 'SIMPLE', 6, 6
        mod = o.modifiers.new('proj', 'UV_PROJECT')
        mod.uv_layer = 'proj'
        mod.projectors[0].object = projektor
        mod.aspect_x, mod.aspect_y = s.render.resolution_x, s.render.resolution_y
    ziel = Vector((0.0, 0.0, 0.01))
    start_ort = kam.location - ziel
    s.frame_start, s.frame_end, s.render.fps = 1, bilder, 30
    basis = kam.data.lens
    for f in range(1, bilder + 1):
        t = (f - 1) / (bilder - 1)
        weich = 0.5 - 0.5 * math.cos(math.pi * t)
        winkel = math.radians(grad * weich)  # vom Originalblick weich bis +grad
        kam.location = ziel + Matrix.Rotation(winkel, 4, 'Z') @ start_ort
        richten(kam, tuple(ziel))
        kam.data.lens = basis * (1 + heran * t)  # gleichmaessig heran (sofort sichtbar)
        kam.keyframe_insert('location', frame=f)
        kam.keyframe_insert('rotation_euler', frame=f)
        kam.data.keyframe_insert('lens', frame=f)
    s.render.image_settings.file_format = 'PNG'
    s.render.filepath = str((AUS / 'proj' / '').resolve()) + '/'
    start = time.time()
    bpy.ops.render.render(animation=True)
    sek = round(time.time() - start, 1)
    ergebnis = [{'szene': f'{szene}-projektion', 'sekunden': sek, 'je_bild': round(sek / bilder, 2), 'bilder': bilder,
                 'grad': grad, 'samples': 4, 'stil': 'projektion', 'datei': 'proj.mp4',
                 'blender': bpy.app.version_string}]
    print(json.dumps(ergebnis[0]), flush=True)
    (AUS / 'blenderprobe.json').write_text(json.dumps(ergebnis, indent=1), encoding='utf-8')


def szene_aus_json(pfad):
    """Probe 12.11. "Claude als 3D-Regisseur": Szene aus geprueftem JSON (fabrik/szene3d.py) im Look des
    Nutzer-Favoriten (Runde 2: warmes Holz, dunkle Welt, AgX Punchy) - nur Grundformen, kein fremder Code."""
    d = json.loads(Path(pfad).read_text(encoding='utf-8'))
    leeren()
    holztisch()
    for i, o in enumerate(d['objekte']):
        mat = stoff(f'm{i}', tuple(o['farbe']), o['rauheit'], o['metall'])
        x, y, z = o['masse']
        if o['form'] == 'box':
            obj = kiste(f'o{i}', tuple(o['ort']), (x, y, z), mat, min(0.003, min(x, y, z) / 4))
        elif o['form'] == 'zylinder':
            obj = walze(f'o{i}', tuple(o['ort']), max(x, y) / 2, z, mat)
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(location=tuple(o['ort']), segments=48, ring_count=24)
            obj = bpy.context.object
            obj.scale = (x / 2, y / 2, z / 2)
            bpy.ops.object.shade_smooth()
            obj.data.materials.append(mat)
        obj.rotation_euler = tuple(math.radians(g) for g in o['drehung_grad'])
    for l in d['lichter']:
        licht('AREA', tuple(l['ort']), l['staerke'], tuple(l['farbe']), groesse=0.5)
    k = d['kamera']
    kamera(tuple(k['ort']), tuple(k['ziel']), k['brennweite'])
    bpy.context.scene.camera.data.dof.aperture_fstop = 8
    AUS.mkdir(parents=True, exist_ok=True)
    datei = AUS / 'szene.jpg'
    bpy.context.scene.render.filepath = str(datei.resolve())
    start = time.time()
    bpy.ops.render.render(write_still=True)
    ergebnis = [{'szene': d.get('motiv', 'szene')[:60], 'sekunden': round(time.time() - start, 1), 'samples': SAMPLES,
                 'stil': 'szene', 'datei': 'szene.jpg', 'blender': bpy.app.version_string,
                 'satz': d.get('satz', ''), 'objekte': len(d['objekte'])}]
    (AUS / 'blenderprobe.json').write_text(json.dumps(ergebnis, indent=1), encoding='utf-8')


def main():
    AUS.mkdir(parents=True, exist_ok=True)
    if STIL == 'szene':  # ARGS[3]: von Claude beschriebene, mit szene3d.pruefen gepruefte Szene (JSON)
        return szene_aus_json(Path(ARGS[3]))
    if STIL == 'projektion':  # ARGS[4]: Szene (12.11.: alle drei Bibliotheksmotive als Drehclip)
        return projektion(Path(ARGS[3]), ARGS[4] if len(ARGS) > 4 else 'chip')
    ergebnis = []
    for name, bau in SZENEN.items():
        leeren()
        bau()
        if STIL == 'toon':  # Tuerkis-Gegenlicht gegenueber der Kamera: Orange/Tuerkis-Kontrast der Spielplakate
            k = bpy.context.scene.camera.location
            abstand = k.length
            licht('AREA', (-k.x * 0.8, -k.y * 0.8 + abstand * 0.6, k.z * 0.9), 30 * abstand ** 2,
                  (0.15, 0.75, 1.0), groesse=abstand * 0.5)
        start = time.time()
        datei = AUS / f'{name}.jpg'
        bpy.context.scene.render.filepath = str(datei.resolve())
        bpy.ops.render.render(write_still=True)
        ergebnis.append({'szene': name, 'sekunden': round(time.time() - start, 1), 'samples': SAMPLES, 'stil': STIL,
                         'datei': datei.name, 'blender': bpy.app.version_string})
        print(json.dumps(ergebnis[-1]), flush=True)
    (AUS / 'blenderprobe.json').write_text(json.dumps(ergebnis, indent=1), encoding='utf-8')


main()
