"""Video-Bauer, Probelauf 1: Skript (JSON) -> Stimme -> Untertitel -> Short.

Misst jede Stufe, damit klar wird, was ein Video an Rechenzeit kostet
(KONZEPT.md, Abschnitt 5a: Rechenminuten je Video = m).

Bausteine (alle kostenlos, gewerblich frei):
  Stimme      Kokoro-82M (Apache 2.0) ueber kokoro-onnx
  Zeitmarken  faster-whisper (MIT) - Wort fuer Wort
  Bild/Ton    Pillow + ffmpeg

Aufruf:  python fabrik/bauen.py skripte/probe.json ausgabe/
"""
import json, sys, time, subprocess, wave, colorsys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

B, H, FPS = 1080, 1920, 30
SCHRIFT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
zeiten = {}


def messen(name):
    """Stufe stoppen: with messen('stimme'): ..."""
    class _M:
        def __enter__(self): self.t = time.time()
        def __exit__(self, *a): zeiten[name] = round(time.time() - self.t, 1)
    return _M()


def schrift(groesse):
    return ImageFont.truetype(SCHRIFT, groesse)


def bild_fuer(teil, titel, nr, gesamt):
    """Ein Standbild je Abschnitt: Verlauf, Titel (2 Zeilen, Schluesselwort farbig), Platz."""
    farbton = (nr * 0.17) % 1.0
    oben = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(farbton, 0.55, 0.30))
    unten = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(farbton, 0.65, 0.08))
    verlauf = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(oben) * (1 - verlauf) + np.array(unten) * verlauf).astype(np.uint8)
    img = Image.fromarray(np.repeat(arr, B, axis=1))
    d = ImageDraw.Draw(img)
    # Titel: genau zwei Zeilen, Schluesselwoerter farbig (Konzept 2b)
    y = 170
    for zeile in titel:
        teile = [(w, w.strip('*') != w) for w in zeile.split(' ')]
        f = schrift(86)
        breite = sum(d.textlength(w.strip('*') + ' ', font=f) for w, _ in teile)
        x = (B - breite) / 2
        for w, betont in teile:
            wort = w.strip('*') + ' '
            d.text((x, y), wort, font=f, fill=(32, 210, 190) if betont else (255, 255, 255),
                   stroke_width=4, stroke_fill=(0, 0, 0))
            x += d.textlength(wort, font=f)
        y += 110
    if teil.get('platz'):
        f = schrift(260)
        t = f"#{teil['platz']}"
        d.text(((B - d.textlength(t, font=f)) / 2, 620), t, font=f, fill=(255, 255, 255),
               stroke_width=8, stroke_fill=(0, 0, 0))
    if teil.get('name'):
        f = schrift(96)
        d.text(((B - d.textlength(teil['name'], font=f)) / 2, 940), teil['name'], font=f,
               fill=(255, 214, 10), stroke_width=5, stroke_fill=(0, 0, 0))
    return img


def ass_zeit(s):
    h, r = divmod(s, 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def untertitel(woerter, pfad):
    """Wort-fuer-Wort-Untertitel: drei Woerter sichtbar, das gesprochene gelb."""
    kopf = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
            "Bold, Outline, Shadow, Alignment, MarginV\n"
            "Style: U,DejaVu Sans,92,&H00FFFFFF,&H00000000,&H64000000,1,7,2,2,330\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Text\n")
    zeilen = []
    for i, w in enumerate(woerter):
        gruppe = woerter[(i // 3) * 3:(i // 3) * 3 + 3]
        text = ' '.join(('{\\c&H0AD6FF&}' + g['w'].upper() + '{\\c&HFFFFFF&}') if g is w else g['w'].upper()
                        for g in gruppe)
        ende = woerter[i + 1]['s'] if i + 1 < len(woerter) else w['e'] + 0.3
        zeilen.append(f"Dialogue: 0,{ass_zeit(w['s'])},{ass_zeit(ende)},U,{text}")
    Path(pfad).write_text(kopf + '\n'.join(zeilen) + '\n', encoding='utf-8')


def main(skript_pfad, aus):
    aus = Path(aus); aus.mkdir(parents=True, exist_ok=True)
    s = json.loads(Path(skript_pfad).read_text(encoding='utf-8'))
    beginn = time.time()

    with messen('stimme_laden'):
        from kokoro_onnx import Kokoro
        kokoro = Kokoro('modelle/kokoro-v1.0.onnx', 'modelle/voices-v1.0.bin')
    teile, rate, laengen = [], 24000, []
    with messen('stimme'):
        for t in s['teile']:
            audio, rate = kokoro.create(t['text'], voice=s.get('stimme', 'af_heart'), speed=s.get('tempo', 1.05), lang='en-us')
            pause = np.zeros(int(rate * 0.25), dtype=np.float32)
            teile.append(np.concatenate([audio.astype(np.float32), pause]))
            laengen.append(len(teile[-1]) / rate)
    ton = np.concatenate(teile)
    with wave.open(str(aus / 'stimme.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((np.clip(ton, -1, 1) * 32767).astype(np.int16).tobytes())

    with messen('zeitmarken'):
        from faster_whisper import WhisperModel
        modell = WhisperModel('base.en', device='cpu', compute_type='int8')
        segs, _ = modell.transcribe(str(aus / 'stimme.wav'), word_timestamps=True)
        woerter = [{'w': x.word.strip(), 's': x.start, 'e': x.end} for seg in segs for x in seg.words]
    untertitel(woerter, aus / 'untertitel.ass')

    with messen('bilder'):
        liste = []
        for i, t in enumerate(s['teile']):
            p = aus / f'bild_{i:02d}.png'
            bild_fuer(t, s['titel'], i, len(s['teile'])).save(p)
            liste.append(f"file '{p.name}'\nduration {laengen[i]:.3f}")
        liste.append(f"file 'bild_{len(s['teile']) - 1:02d}.png'")
        (aus / 'bilder.txt').write_text('\n'.join(liste) + '\n', encoding='utf-8')

    with messen('rendern'):
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'bilder.txt',
            '-i', 'stimme.wav',
            '-vf', f'fps={FPS},format=yuv420p,ass=untertitel.ass',
            '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11',  # Plattformnorm (Konzept 4a, Punkt 6)
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-c:a', 'aac', '-b:a', '160k',
            '-shortest', '-movflags', '+faststart', 'short.mp4'], cwd=aus, check=True)

    zeiten['gesamt'] = round(time.time() - beginn, 1)
    zeiten['videolaenge_s'] = round(sum(laengen), 1)
    zeiten['woerter'] = len(woerter)
    (aus / 'messung.json').write_text(json.dumps(zeiten, indent=2), encoding='utf-8')
    print(json.dumps(zeiten, indent=2))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
