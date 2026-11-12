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
    return s


def stoff(name, farbe, rau=0.5, metall=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
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
    kiste('tisch', (0, 0, -0.03), (3, 2, 0.06), holz, 0.005)


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
    gruen = stoff('platine', (0.02, 0.18, 0.07), 0.5)
    kiste('platine', (0, 0.02, -0.004), (0.34, 0.3, 0.006), gruen, 0.002)
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


def main():
    AUS.mkdir(parents=True, exist_ok=True)
    ergebnis = []
    for name, bau in SZENEN.items():
        leeren()
        bau()
        start = time.time()
        datei = AUS / f'{name}.jpg'
        bpy.context.scene.render.filepath = str(datei.resolve())
        bpy.ops.render.render(write_still=True)
        ergebnis.append({'szene': name, 'sekunden': round(time.time() - start, 1), 'samples': SAMPLES,
                         'datei': datei.name, 'blender': bpy.app.version_string})
        print(json.dumps(ergebnis[-1]), flush=True)
    (AUS / 'blenderprobe.json').write_text(json.dumps(ergebnis, indent=1), encoding='utf-8')


main()
