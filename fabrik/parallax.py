"""Lebende Bilder: 2,5D-Parallax aus einer geschaetzten Tiefenkarte.

Nutzer 28.10.2026: "kostenlose KI, die die Bilder mehr bewegt"; der Video-Pruefer bemaengelte mehrfach
"Standbild". Echtes Bild-zu-Video (Wan, LTX) braucht eine Grafikkarte, Kling/Runway kosten Geld. Hier:
Depth Anything V2 Small (Apache-2.0, ONNX, laeuft auf der GitHub-CPU) schaetzt, was vorne und was hinten
ist; Vordergrund und Hintergrund wandern dann verschieden weit - die Kamera wirkt dreidimensional.

Nur fuer gemalte Szenen: Screenshots, Grafiken und Zahlenkarten wuerden ihre Schrift verziehen.
Jeder Fehler (kein Modell, kein OpenCV, kein Netz) liefert None - dann bleibt der bisherige Zoom.
"""
import hashlib
import os
import subprocess
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

MODELL = Path(__file__).resolve().parents[1] / 'modelle' / 'depth-anything-v2-small-int8.onnx'
MODELL_URL = ('https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/'
              '4472b7362082ad9968fee890ca0f1e5aca36b93d/onnx/model_int8.onnx')
MODELL_SHA = '01aa7a23de3f4a0ee1a2bb9997e6918104c85a9f95dea46d27b9b3fb0c6b9001'
# Vordergrund wandert ueber die ganze Einstellung um diesen Anteil der Bildbreite gegen den Hintergrund.
# Dezent: groessere Werte reissen an Kanten (Figur vor Wand) sichtbar auf.
# 29.10.2026: 6 % ueber 5 s war im echten SK-Hynix-Short nicht wahrnehmbar; Nutzer wollte 15 %. Ohne Beschnitt
# verzog 15 % die Raender (Beine doppelt, Stuhlbein) - mit RAND 8 % Beschnitt an der Werkstattszene sauber.
# 30.10.2026 (Business Intel): Nutzer - "die Kamera-Drehung verzerrt die Figuren, bisschen runterschrauben". Innerhalb
# einer Figur aendert sich die Tiefe (Nase/Schulter/Arm) - jeder Tiefenunterschied verbiegt sie proportional.
VERSCHIEBUNG = 0.10
HERAN = 0.10  # Vordergrund kommt zusaetzlich naeher
RAND = 0.08  # so viel vom Rand wird abgeschnitten (gespiegelte Randpixel nie sichtbar)
KURZE_SEITE = 392  # Modelleingabe, Vielfaches von 14

_sitzung = None
_gitter = {}


def an():
    return os.environ.get('CF_LEBEND', '1') != '0'


def _modell():
    global _sitzung
    if _sitzung is None:
        import onnxruntime as ort
        if not MODELL.exists() or hashlib.sha256(MODELL.read_bytes()).hexdigest() != MODELL_SHA:
            MODELL.parent.mkdir(parents=True, exist_ok=True)
            tmp = MODELL.with_suffix('.tmp')
            urllib.request.urlretrieve(MODELL_URL, tmp)
            if hashlib.sha256(tmp.read_bytes()).hexdigest() != MODELL_SHA:
                tmp.unlink()
                raise ValueError('Tiefenmodell: Pruefsumme falsch')
            tmp.replace(MODELL)
        _sitzung = ort.InferenceSession(str(MODELL), providers=['CPUExecutionProvider'])
    return _sitzung


def tiefe(rgb):
    """Tiefenkarte 0..1 in Bildgroesse, 1 = nah (Depth Anything liefert inverse Tiefe)."""
    import cv2
    h, w = rgb.shape[:2]
    f = KURZE_SEITE / min(h, w)
    mh, mw = max(14, round(h * f / 14) * 14), max(14, round(w * f / 14) * 14)
    x = cv2.resize(rgb, (mw, mh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    d = _modell().run(None, {'pixel_values': x.transpose(2, 0, 1)[None].astype(np.float32)})[0][0]
    d = cv2.resize(d, (w, h), interpolation=cv2.INTER_LINEAR)
    d = (d - d.min()) / max(1e-6, float(d.max() - d.min()))
    # Weiche Kanten: harte Tiefenspruenge reissen das Bild beim Verschieben auf
    return cv2.GaussianBlur(d.astype(np.float32), (0, 0), max(2.0, w / 200))


def bild(rgb, d, p):
    """Ein Bild der Fahrt; p laeuft von 0 bis 1."""
    import cv2
    h, w = d.shape
    if _gitter.get('form') != (h, w):
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        _gitter.update(form=(h, w), x=xx - w / 2, y=yy - h / 2)
    p = np.float32(p)
    s = p - np.float32(0.5)  # Mitte der Einstellung = Originalbild
    k = 1 / (1 + np.float32(HERAN) * p * d)  # nahe Teile wachsen leicht
    # 28.10.2026: Hintergrund steht fast still, nur Nahes wandert (Tiefe ~ d^2: nah bewegt sich rund zehnmal
    # weiter als die halbe Tiefe). Vorher drehte sich alles um die mittlere Tiefe - wirkte wie ein Schwenk.
    mx = _gitter['x'] * k + np.float32(w / 2) - s * np.float32(VERSCHIEBUNG * w) * d * d
    my = _gitter['y'] * k + np.float32(h / 2)
    return cv2.remap(rgb, mx, my, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def ohne_rand(img):
    """Rand abschneiden und auf die alte Groesse bringen - dort lagen bei starker Fahrt gespiegelte Pixel."""
    import cv2
    h, w = img.shape[:2]
    y, x = int(h * RAND / 2), int(w * RAND / 2)
    return cv2.resize(img[y:h - y, x:w - x], (w, h), interpolation=cv2.INTER_CUBIC)


def video(quelle, groesse, dauer, fps, ziel):
    """MP4 (ohne Ton) der Parallax-Fahrt in groesse (b, h); None, wenn etwas fehlt."""
    if not an():
        return None
    try:
        b, h = groesse
        rgb = np.asarray(Image.open(quelle).convert('RGB').resize((b, h), Image.LANCZOS))
        d = tiefe(rgb)
        n = max(2, int(round(dauer * fps)))
        prozess = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                                    '-s', f'{b}x{h}', '-r', str(fps), '-i', '-', '-an', '-c:v', 'libx264',
                                    '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', str(ziel)],
                                   stdin=subprocess.PIPE)
        for i in range(n):
            p = i / (n - 1)
            prozess.stdin.write(ohne_rand(bild(rgb, d, 0.5 - 0.5 * np.cos(np.pi * p))).tobytes())  # sanft an/aus
        prozess.stdin.close()
        if prozess.wait() != 0:
            return None
        return Path(ziel)
    except Exception as e:  # lebende Bilder sind Kuer - nie den Bau kippen
        print('Lebendes Bild nicht moeglich, bleibt beim Zoom:', str(e)[:160])
        return None
