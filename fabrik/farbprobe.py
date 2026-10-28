"""Probe 28.10.2026 (Nutzer: "bei Historik-Videos mehr Farbe, aber kraeftig"): gemeinfreie Archivclips
(Internet Archive, Prelinger) echt einfaerben (DDColor, Apache-2.0, laeuft ohne Grafikkarte) und danach
kraeftig malen wie die Stock-Clip-Probe "Gemalt+", die dem Nutzer gefiel. Nicht Teil der Pipeline.

Ausgabe je Clip: Video mit drei Spalten (Archiv | eingefaerbt | eingefaerbt + gemalt) und Zeit je Bild.
Aufruf: python fabrik/farbprobe.py <ddcolor-ordner> <ausgabe> <modell> id:start [id:start ...]
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

SEKUNDEN = 3
BREITE, HOEHE = 360, 640


def vertikal(f):
    h, w = f.shape[:2]
    b = int(h * 9 / 16)
    x = (w - b) // 2
    return cv2.resize(f[:, x:x + b], (BREITE, HOEHE), interpolation=cv2.INTER_CUBIC)


def gemalt(f, satt=1.7):
    """Wie "Gemalt+" der Stock-Clip-Probe: Malfilter, Vibrance, warm, Kontrast."""
    f = cv2.stylization(f, sigma_s=45, sigma_r=0.35)
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
    s = hsv[..., 1] / 255
    hsv[..., 1] = np.clip(255 * (s + (1 - s) * s * (satt - 1) * 1.2 + s * (satt - 1) * .5), 0, 255)
    hsv[..., 2] = np.clip((hsv[..., 2] - 128) * 1.18 + 132, 0, 255)
    g = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    g[..., 2] *= 1.10
    g[..., 0] *= .88
    return np.clip(g, 0, 255).astype(np.uint8)


def modell_laden(ordner, name):
    sys.path.insert(0, str(ordner))
    from ddcolor import DDColor, ColorizationPipeline
    from huggingface_hub import PyTorchModelHubMixin

    class DDColorHF(DDColor, PyTorchModelHubMixin):
        def __init__(self, config=None, **kwargs):
            if isinstance(config, dict):
                kwargs = {**config, **kwargs}
            super().__init__(**kwargs)
    return ColorizationPipeline(DDColorHF.from_pretrained(f'piddnad/{name}'), input_size=512)


def main(ordner, aus, name, clips):
    aus = Path(aus)
    aus.mkdir(parents=True, exist_ok=True)
    pipeline = modell_laden(ordner, name)
    messung = []
    for n, spec in enumerate(clips):
        kennung, start = spec.split(':')
        roh = aus / f'roh_{n}.mp4'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', start, '-user_agent', 'Mozilla/5.0',
                        '-i', f'https://archive.org/download/{kennung}/{kennung}.mp4', '-t', str(SEKUNDEN),
                        '-an', str(roh)], check=True)
        cap = cv2.VideoCapture(str(roh))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        ziel = aus / f'farbe_{n}_roh.mp4'
        out = cv2.VideoWriter(str(ziel), cv2.VideoWriter_fourcc(*'mp4v'), fps, (BREITE * 3, HOEHE))
        zeiten = []
        k = 0
        while True:
            ok, f = cap.read()
            if not ok:
                break
            t = time.time()
            bunt = pipeline.process(f)
            zeiten.append(time.time() - t)
            v, b = vertikal(f), vertikal(bunt)
            bild = np.hstack([v, b, gemalt(b)])
            for x, text in ((10, 'Archiv'), (370, 'Eingefaerbt'), (730, 'Eingefaerbt+gemalt')):
                cv2.putText(bild, text, (x, 30), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 2)
            out.write(bild)
            if k == int(fps * SEKUNDEN / 2):
                cv2.imwrite(str(aus / f'standbild_{n}.jpg'), bild)
            k += 1
        out.release()
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(ziel), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        '-crf', '23', str(aus / f'farbe_{n}.mp4')], check=True)
        messung.append({'clip': spec, 'bilder': k, 'sekunden_je_bild': round(sum(zeiten) / max(1, len(zeiten)), 2)})
        print(messung[-1], flush=True)
    (aus / 'messung.json').write_text(json.dumps({'modell': name, 'clips': messung}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
