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


def hintergrund(nr):
    """Farbverlauf - Rueckfall, wenn kein Clip gefunden wurde."""
    farbton = (nr * 0.17) % 1.0
    oben = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(farbton, 0.55, 0.30))
    unten = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(farbton, 0.65, 0.08))
    verlauf = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(oben) * (1 - verlauf) + np.array(unten) * verlauf).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, B, axis=1)).convert('RGBA')


def bild_fuer(teil, titel, nr, gesamt, durchsichtig=False):
    """Ebene je Abschnitt: Titel (2 Zeilen, Schluesselwort farbig), Platz, Name.
    durchsichtig=True: nur die Schrift + Abdunklung oben/unten, als Ebene ueber
    einem Videoclip."""
    if durchsichtig:
        img = Image.new('RGBA', (B, H), (0, 0, 0, 0))
        schatten = np.zeros((H, B, 4), dtype=np.uint8)
        a = np.zeros(H)
        a[:700] = np.linspace(170, 60, 700)            # oben dunkel fuer den Titel
        a[1150:] = np.linspace(60, 190, H - 1150)      # unten dunkel fuer Untertitel
        a[700:1150] = 60
        schatten[..., 3] = a[:, None].astype(np.uint8)
        img = Image.alpha_composite(img, Image.fromarray(schatten, 'RGBA'))
    else:
        img = hintergrund(nr)
    d = ImageDraw.Draw(img)
    # Titel: genau zwei Zeilen, Schluesselwoerter farbig (Konzept 2b).
    # Probelauf 1: zweite Zeile war breiter als das Bild -> Groesse passt sich an.
    y = 170
    for zeile in titel:
        teile = [(w, w.strip('*') != w) for w in zeile.split(' ')]
        groesse = 86
        while True:
            f = schrift(groesse)
            breite = sum(d.textlength(w.strip('*') + ' ', font=f) for w, _ in teile)
            if breite <= B - 100 or groesse <= 40:
                break
            groesse -= 4
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


PIXABAY_CACHE = Path('clips')


def clip_fuer(suche, schon, laenge):
    """Passenden Pixabay-Clip suchen und herunterladen (Pixabay-Regeln:
    Ergebnisse 24 h zwischenspeichern, Clips herunterladen statt verlinken).
    Gibt (pfad, quelle) oder (None, None) zurueck."""
    import os, urllib.request, urllib.parse, hashlib
    schluessel = os.environ.get('PIXABAY_API_KEY')
    if not schluessel or not suche:
        return None, None
    PIXABAY_CACHE.mkdir(exist_ok=True)
    tag = time.strftime('%Y-%m-%d')
    cache = PIXABAY_CACHE / f"suche_{hashlib.sha1((suche + tag).encode()).hexdigest()[:12]}.json"
    if cache.exists():
        daten = json.loads(cache.read_text())
    else:
        url = ('https://pixabay.com/api/videos/?' + urllib.parse.urlencode(
            {'key': schluessel, 'q': suche, 'safesearch': 'true', 'per_page': 20, 'order': 'popular'}))
        daten = json.load(urllib.request.urlopen(url, timeout=30))
        cache.write_text(json.dumps(daten))
    for hit in daten.get('hits', []):
        if hit['id'] in schon or hit.get('duration', 0) < 3:
            continue
        v = hit['videos'].get('medium') or hit['videos'].get('small')
        if not v or not v.get('url'):
            continue
        ziel = PIXABAY_CACHE / f"pixabay_{hit['id']}.mp4"
        if not ziel.exists():
            urllib.request.urlretrieve(v['url'], ziel)
        schon.add(hit['id'])
        return ziel, {'quelle': 'Pixabay', 'id': hit['id'], 'seite': hit['pageURL'], 'von': hit.get('user')}
    return None, None


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
        # Ton direkt aus dem Speicher (16 kHz), nicht als Datei: Die Datei-
        # Variante geht ueber PyAV, und dessen neue Fassung passt nicht zu
        # faster-whisper ("unexpected keyword argument 'metadata_errors'").
        n16 = int(len(ton) * 16000 / rate)
        ton16 = np.interp(np.linspace(0, len(ton) - 1, n16), np.arange(len(ton)), ton).astype(np.float32)
        segs, _ = modell.transcribe(ton16, word_timestamps=True)
        woerter = [{'w': x.word.strip(), 's': x.start, 'e': x.end} for seg in segs for x in seg.words]
    untertitel(woerter, aus / 'untertitel.ass')

    # Je Abschnitt ein eigenes Stueck: Clip (zugeschnitten auf 9:16) mit
    # Schrift-Ebene darueber - oder Farbverlauf, wenn kein Clip passt.
    quellen, schon, liste = [], set(), []
    with messen('clips_und_stuecke'):
        for i, t in enumerate(s['teile']):
            dauer = laengen[i]
            stueck = aus / f'stueck_{i:02d}.mp4'
            clip, quelle = clip_fuer(t.get('suche') or s.get('suche'), schon, dauer)
            ebene = aus / f'ebene_{i:02d}.png'
            bild_fuer(t, s['titel'], i, len(s['teile']), durchsichtig=bool(clip)).save(ebene)
            if clip:
                quellen.append(quelle)
                filt = (f'[0:v]scale={B}:{H}:force_original_aspect_ratio=increase,crop={B}:{H},setsar=1,'
                        f'fps={FPS}[v];[v][1:v]overlay=0:0,format=yuv420p')
                ein = ['-stream_loop', '-1', '-i', str(clip), '-i', str(ebene)]
            else:
                quellen.append({'quelle': 'eigenes Bild'})
                filt = f'[0:v]fps={FPS},format=yuv420p'
                ein = ['-loop', '1', '-i', str(ebene)]
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *ein, '-filter_complex', filt,
                            '-t', f'{dauer:.3f}', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                            str(stueck)], check=True)
            liste.append(f"file '{stueck.name}'")
        (aus / 'stuecke.txt').write_text('\n'.join(liste) + '\n', encoding='utf-8')
    # Quellen je Video festhalten (Rechte-Regeln, Konzept 2c) - und fuer
    # die Beschreibung („Clips: Pixabay", Bitte von Pixabay).
    (aus / 'quellen.json').write_text(json.dumps(quellen, indent=2, ensure_ascii=False), encoding='utf-8')

    with messen('rendern'):
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'stuecke.txt',
            '-i', 'stimme.wav',
            '-vf', f'fps={FPS},format=yuv420p,ass=untertitel.ass',
            '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11',  # Plattformnorm (Konzept 4a, Punkt 6)
            # 48 kHz Stereo: loudnorm rechnet intern hoch, und das Ergebnis
            # (96 kHz Mono) spielten Handy-Player nicht ab - gemeldet: „keine
            # Stimme hörbar", obwohl die Tonspur laut genug war (−15 dB).
            '-ar', '48000', '-ac', '2',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-c:a', 'aac', '-b:a', '160k',
            '-shortest', '-movflags', '+faststart', 'short.mp4'], cwd=aus, check=True)

    zeiten['gesamt'] = round(time.time() - beginn, 1)
    zeiten['videolaenge_s'] = round(sum(laengen), 1)
    zeiten['woerter'] = len(woerter)
    (aus / 'messung.json').write_text(json.dumps(zeiten, indent=2), encoding='utf-8')
    print(json.dumps(zeiten, indent=2))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
