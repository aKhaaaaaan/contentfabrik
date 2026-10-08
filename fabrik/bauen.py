"""Video-Bauer, Probelauf 1: Skript (JSON) -> Stimme -> Untertitel -> Short.

Misst jede Stufe, damit klar wird, was ein Video an Rechenzeit kostet
(KONZEPT.md, Abschnitt 5a: Rechenminuten je Video = m).

Bausteine (alle kostenlos, gewerblich frei):
  Stimme      Kokoro-82M (Apache 2.0) ueber kokoro-onnx
  Zeitmarken  faster-whisper (MIT) - Wort fuer Wort
  Bild/Ton    Pillow + ffmpeg

Aufruf:  python fabrik/bauen.py skripte/probe.json ausgabe/
"""
import json, math, os, re, sys, time, subprocess, wave, colorsys, shutil, hashlib
from PIL import ImageFilter
from pathlib import Path

import numpy as np
import prompts
import dramaturgie
import bildplan
import ton as audioqualitaet
from PIL import Image, ImageDraw, ImageFont

B, H, FPS = 1080, 1920, 30
# Montserrat (SIL OFL, gewerblich frei) liegt im Projekt - GEMELDET: DejaVu
# wirkte „sehr unprofessionell".
SCHRIFTEN = Path(__file__).resolve().parent.parent / 'schriften'
SCHRIFT = str(SCHRIFTEN / 'Montserrat-ExtraBold.ttf')
TITEL_SCHRIFT = str(SCHRIFTEN / 'Montserrat-Black.ttf')
zeiten = {}
# Soundeffekte (CC0, Freesound ueber Openverse; Quellen in sfx/LIZENZ.md).
# GEMESSEN 04.10.2026 am Vorbild (alan.buildz): 15 Schnitte in 58 s, im Einstieg
# 4 in 3 s - bei uns stand ein Bild 5-10 s. Profi-Shorts setzen ein „Whoosh"
# auf jeden Schnitt und ein „Pop", wenn etwas Neues erscheint.
SFX = Path(__file__).resolve().parent.parent / 'sfx'
# Ruhige Bewegung auf Illustrationen; Bildwechsel folgen inhaltlichen Beats.
ZOOM = '1+0.035*min(on/{n},1)'
LAYOUT = {}


def format_setzen(art='short'):
    """Getrennte Satzspiegel; alle Medien behalten ihr Seitenverhaeltnis."""
    global B, H
    if art not in ('short', 'lang'):
        raise ValueError('Unbekanntes Videoformat')
    B, H = (1920, 1080) if art == 'lang' else (1080, 1920)
    LAYOUT.clear()
    LAYOUT.update({'links': 80, 'rechts': 1840, 'mitte': 960, 'titel_y': 46,
                   'titel_font': 56, 'progress_y': 220, 'platz_y': 255, 'name_y': 355,
                   'karte': (80, 420, 1320, 840), 'foto': (80, 220, 1320, 840),
                   'akzent_y': 540, 'akzent_x': 1610, 'akzent_breite': 420,
                   'untertitel_y': 965, 'mini': (80, 270, 500, 405)}
                  if art == 'lang' else
                  {'links': 72, 'rechts': 900, 'mitte': 486, 'titel_y': 190,
                   'titel_font': 72, 'progress_y': 414, 'platz_y': 455, 'name_y': 605,
                   'karte': (72, 700, 900, 1180), 'foto': (48, 260, 960, 1180),
                   'akzent_y': 1250, 'untertitel_y': 1420, 'mini': (72, 480, 492, 650)})


format_setzen()


def akzent_farbe(s):
    wert = s.get('titel_farbe', '#20D2BE')
    if not isinstance(wert, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', wert):
        wert = '#20D2BE'
    return tuple(int(wert[i:i + 2], 16) for i in (1, 3, 5))


def einpassen(groesse, zone):
    x1, y1, x2, y2 = zone
    faktor = min((x2 - x1) / groesse[0], (y2 - y1) / groesse[1])
    w, h = max(1, int(groesse[0] * faktor)), max(1, int(groesse[1] * faktor))
    return (x1 + (x2 - x1 - w) // 2, y1 + (y2 - y1 - h) // 2, w, h)


def text_font(text, maximum=58, minimum=32, breite=None):
    breite = breite or LAYOUT['rechts'] - LAYOUT['links'] - 32
    for g in range(maximum, minimum - 1, -2):
        f = schrift(g)
        if f.getlength(text) <= breite:
            return f
    raise ValueError('Bildtext zu lang fuer lesbare Darstellung')


def bildtext_layout(text, profil=None):
    """Lange Videos: lesbarer Detail-Akzent neben dem Originalmaterial."""
    maximum = 50 if B > H else 60
    breite = LAYOUT.get('akzent_breite', LAYOUT['rechts'] - LAYOUT['links'] - 32)
    zeilen = [text]
    if B > H and schrift(maximum).getlength(text) > breite:
        woerter = text.split()
        if len(woerter) > 1:
            schnitt = min(range(1, len(woerter)), key=lambda i: max(
                schrift(maximum).getlength(' '.join(woerter[:i])),
                schrift(maximum).getlength(' '.join(woerter[i:]))))
            zeilen = [' '.join(woerter[:schnitt]), ' '.join(woerter[schnitt:])]
    f = text_font(max(zeilen, key=lambda z: schrift(maximum).getlength(z)), maximum, breite=breite)
    y = 1220 if profil == 'hoch' and H > B else LAYOUT['akzent_y']
    return f, zeilen, LAYOUT.get('akzent_x', LAYOUT['mitte']), y


def effekte_spur(ereignisse, laenge_s, rate, ziel, glitch=False, geraeusche=()):
    """Tonspur nur mit Effekten: [(sekunde, 'whoosh'|'pop'), ...]. Whoosh-Varianten
    wechseln sich ab (immer derselbe Klang wirkt billig). Begrenzte kurze Effekte,
    deutlich unter der Stimme. geraeusche: [(sekunde, mp3-Pfad)] passend zur Szene."""
    lade = {}
    spur_geraeusche = []
    for sek, pfad in geraeusche:
        try:
            roh = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(pfad), '-t', '2', '-f', 'f32le',
                                  '-ac', '1', '-ar', str(rate), '-'], capture_output=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            continue
        x = audioqualitaet.effekt(np.frombuffer(roh, dtype=np.float32), 'geraeusch', rate)
        aus_n = min(len(x), int(rate * 0.3))  # weich ausklingen statt hart abgeschnitten
        if aus_n:
            x[-aus_n:] *= np.linspace(1, 0, aus_n, dtype=np.float32)
        if 0 <= sek < laenge_s and len(x):
            spur_geraeusche.append((int(sek * rate), x))
    def klang(name):
        if name not in lade:
            roh = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', str(SFX / f'{name}.mp3'), '-f', 'f32le',
                                  '-ac', '1', '-ar', str(rate), '-'], capture_output=True, check=True).stdout
            x = np.frombuffer(roh, dtype=np.float32)
            lade[name] = audioqualitaet.effekt(x, name if not name.startswith('whoosh') else 'whoosh', rate)
        return lade[name]
    spur = np.zeros(int(laenge_s * rate) + rate, dtype=np.float32)
    whooshs = sorted(p.stem for p in SFX.glob('whoosh_*.mp3'))
    n = 0
    for sek, art in audioqualitaet.ereignisse(ereignisse, laenge_s):
        if art == 'whoosh':
            if not whooshs:
                continue
            # GEMESSEN (Vorbild Kien Nguyen): mehrere Effektarten uebereinander;
            # im KI-Kanal jeder 3. Schnitt ein digitales Glitch statt Whoosh.
            x = klang('glitch' if glitch and n % 3 == 2 else whooshs[n % len(whooshs)]); n += 1
            start = int(max(0, sek - 0.25) * rate)  # das Rauschen kommt kurz VOR dem Schnitt
        elif art == 'riser':  # Spannung: endet genau beim Ereignis
            x = klang('riser')
            ende_riser = int(sek * rate)
            if len(x) > ende_riser:
                x = x[-ende_riser:].copy()
                fade = min(len(x), max(1, int(rate * 0.005)))
                x[:fade] *= np.linspace(0, 1, fade)
            start = ende_riser - len(x)
        else:
            x = klang(art)
            start = int(sek * rate)
        ende = min(len(spur), start + len(x))
        spur[start:ende] += x[:ende - start]
    for start, x in spur_geraeusche:
        ende = min(len(spur), start + len(x))
        spur[start:ende] += x[:ende - start]
    spur = audioqualitaet.begrenzen(spur)
    with wave.open(str(ziel), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((np.clip(spur, -1, 1) * 32767).astype(np.int16).tobytes())


def messen(name):
    """Stufe stoppen: with messen('stimme'): ..."""
    class _M:
        def __enter__(self): self.t = time.time()
        def __exit__(self, *a): zeiten[name] = round(time.time() - self.t, 1)
    return _M()


def schrift(groesse, datei=None):
    return ImageFont.truetype(datei or SCHRIFT, groesse)


def hintergrund(nr):
    """Farbverlauf - Rueckfall, wenn kein Clip gefunden wurde."""
    farbton = (nr * 0.17) % 1.0
    oben = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(farbton, 0.55, 0.30))
    unten = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(farbton, 0.65, 0.08))
    verlauf = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(oben) * (1 - verlauf) + np.array(unten) * verlauf).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, B, axis=1)).convert('RGBA')


def schrift_text(img, xy, text, f, farbe=(255, 255, 255), rand=3):
    """Text mit weichem Schatten und duennem Rand. GEMELDET: dicke schwarze
    Raender (7 px, DejaVu) wirkten „sehr unprofessionell"."""
    schatten = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(schatten).text((xy[0] + 4, xy[1] + 6), text, font=f, fill=(0, 0, 0, 200),
                                  stroke_width=rand + 4, stroke_fill=(0, 0, 0, 200))
    img.alpha_composite(schatten.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(img).text(xy, text, font=f, fill=farbe, stroke_width=rand, stroke_fill=(0, 0, 0))


def titel_zeichnen(img, titel, akzent):
    """Titel: zwei Zeilen im Short, eine im Querformat, Schluesselwoerter farbig; die
    Groesse passt sich an (Probelauf 1: Zeile 2 war breiter als das Bild)."""
    d = ImageDraw.Draw(img)
    y = LAYOUT['titel_y']
    if B > H:
        titel = [' '.join(titel)]
    for zeile in titel:
        teile = [(w, w.strip('*') != w) for w in zeile.split(' ')]
        groesse = LAYOUT['titel_font']
        while True:
            f = schrift(groesse, TITEL_SCHRIFT)
            breite = sum(d.textlength(w.strip('*') + ' ', font=f) for w, _ in teile)
            if breite <= LAYOUT['rechts'] - LAYOUT['links'] - 24:
                break
            if groesse <= 32:
                raise ValueError('Titel zu lang fuer den Satzspiegel')
            groesse -= 4
        x = LAYOUT['mitte'] - breite / 2
        for w, betont in teile:
            wort = w.strip('*') + ' '
            schrift_text(img, (x, y), wort, f, akzent if betont else (255, 255, 255))
            x += d.textlength(wort, font=f)
        y += groesse + 22


def musik_holen(suchen):
    """Hintergrundmusik ueber Openverse (offizielle, kostenlose Suche nach frei
    lizenzierten Werken, u. a. Jamendo und Freesound).
    GEMELDET: „Brauchen die Videos keine Hintergrundmusik?" - und die Musik soll
    fuer YouTube UND TikTok gelten. GEPRUEFT 03.10.2026: YouTube-Audio-Library-
    Stuecke duerfen meist nur auf YouTube laufen. Darum nur CC0 und CC BY
    (gewerblich, jede Plattform, Kuenstler nennen); KEIN CC BY-SA - das wuerde
    verlangen, das ganze Video unter dieselbe Lizenz zu stellen.
    Gibt (pfad, nennung) oder (None, None) zurueck."""
    import random, urllib.parse, urllib.request
    PIXABAY_CACHE.mkdir(exist_ok=True)
    gesperrt = set(json.loads(MUSIK_SPERRE.read_text(encoding='utf-8'))) if MUSIK_SPERRE.exists() else set()
    for suche in random.sample(suchen, len(suchen)):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(
                'https://api.openverse.org/v1/audio/?' + urllib.parse.urlencode(
                    {'q': suche + ' instrumental', 'license_type': 'commercial', 'page_size': 20}), headers=WIKI_KENNUNG), timeout=30))
        except Exception as e:
            print('Openverse nicht erreichbar:', str(e)[:120])
            continue
        treffer = [r for r in d.get('results', [])
                   if r.get('license') in ('cc0', 'by') and r.get('url') and r['id'] not in gesperrt
                   and not re.search(r'\b(vocals?|lyrics?|speech|spoken|singing|a cappella)\b',
                                     str(r.get('title', '')), re.I)
                   and 45_000 <= (r.get('duration') or 0) <= 600_000]
        if not treffer:
            continue
        r = random.choice(treffer[:8])  # Abwechslung, aber aus den relevantesten
        ziel = PIXABAY_CACHE / f"musik_{r['id']}.mp3"
        try:
            if not ziel.exists():
                ziel.write_bytes(urllib.request.urlopen(urllib.request.Request(r['url'], headers=WIKI_KENNUNG),
                                                        timeout=60).read())
        except Exception as e:
            print('Musik-Download fehlgeschlagen:', str(e)[:120])
            continue
        lizenz = 'CC0' if r['license'] == 'cc0' else f"CC BY {r.get('license_version', '')}".strip()
        nennung = f"Music: \"{r['title']}\" by {r.get('creator') or 'unknown'} ({lizenz}, via {r.get('source')})"
        print('Musik:', nennung)
        return ziel, {'quelle': 'Musik', 'id': r['id'], 'nennung': nennung, 'seite': r.get('foreign_landing_url', '')}
    return None, None


def geraeusch_holen(suche):
    """Zur Szene passendes Geraeusch (z. B. Kasse, jubelnde Menge) ueber Openverse.

    GEMELDET 07.10.2026: Ton soll fesseln; Codex-Vorgabe: Geraeusche muessen
    inhaltlich passen. Bisher nur 6 allgemeine Effekte (sfx/). GEPRUEFT 07.10.2026:
    Openverse liefert Freesound-Klaenge mit CC0 (z. B. 89 Treffer 'cash register');
    der Filter category=sound_effect lieferte 0 Treffer, darum Quelle+Dauer pruefen.
    Nur CC0: keine Namensnennungspflicht, jede Plattform. Gibt (pfad, nennung) oder
    (None, None) - ein fehlendes Geraeusch kippt nie das Video.
    """
    import urllib.parse, urllib.request
    suche = re.sub(r'[^A-Za-z ]', ' ', str(suche or '')).strip()[:40]
    if len(suche.split()) < 1:
        return None, None
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(
            'https://api.openverse.org/v1/audio/?' + urllib.parse.urlencode(
                {'q': suche, 'license': 'cc0', 'page_size': 20}), headers=WIKI_KENNUNG), timeout=20))
        treffer = [r for r in d.get('results', []) if r.get('license') == 'cc0' and r.get('url')
                   and r.get('source') == 'freesound' and 300 <= (r.get('duration') or 0) <= 30_000
                   and not re.search(r'\b(music|song|loop|beat|vocals?|speech)\b', str(r.get('title', '')), re.I)]
        if not treffer:
            return None, None
        r = treffer[0]  # relevantester Treffer: das Geraeusch soll zur Szene passen
        PIXABAY_CACHE.mkdir(exist_ok=True)
        ziel = PIXABAY_CACHE / f"geraeusch_{re.sub(r'[^A-Za-z0-9-]', '', str(r['id']))[:60]}.mp3"
        if not ziel.exists():
            ziel.write_bytes(urllib.request.urlopen(urllib.request.Request(r['url'], headers=WIKI_KENNUNG),
                                                    timeout=30).read())
        nennung = f"Sound: \"{r.get('title', '')}\" by {r.get('creator') or 'unknown'} (CC0, via Freesound)"
        print('Geraeusch:', suche, '->', nennung[:100])
        return ziel, nennung
    except Exception as e:
        print('Geraeusch nicht geholt:', str(e)[:120])
        return None, None


def foto_fuer(bilder, satz, benutzt):
    """KI waehlt aus den freien Wikipedia-Fotos das zum Satz passende (oder
    keins). Jedes Foto hoechstens einmal je Video."""
    import urllib.request, hashlib
    frei = [b for b in bilder if b['titel'] not in benutzt]
    if not frei or not os.environ.get('GEMINI_API_KEY'):
        return None, None
    try:
        from skript import gemini, SEHEN
        # GEMESSEN (Nintendo-Lauf): Nur die ersten 8 von 32 Fotos wurden
        # gezeigt - alphabetisch Buerogebaeude und Game Boys; „Nintendo 1889"
        # und „NintendoCards" kamen nie dran -> Stock-Clips (Autobahn, Naeherei).
        # Jetzt: Vorauswahl ueber alle Titel/Beschreibungen, dann Vorschau.
        liste = '\n'.join(f"{n}: {b['titel'][5:]} - {b['beschreibung'][:120]}" for n, b in enumerate(frei))
        vor, _ = gemini(prompts.DATEN + f'Shortlist photos for this narration: {json.dumps(satz)}. '
                        'Match the actual person, product, place and period in the captions; do not choose '
                        'a modern company photo to represent its founding. Give at most 4 unique integer '
                        f'indices, best first; empty list if none clearly fits. Indexed metadata:\n{liste}',
                        {'type': 'OBJECT', 'properties': {'nummern': {'type': 'ARRAY', 'items': {'type': 'INTEGER'}}},
                         'required': ['nummern']}, temperatur=0.1,
                        modelle=SEHEN)
        frei = [frei[n] for n in dict.fromkeys(vor['nummern'])
                if type(n) is int and 0 <= n < len(frei)][:4]
        if not frei:
            return None, None
        vorschau = [urllib.request.urlopen(urllib.request.Request(b['klein'], headers=WIKI_KENNUNG),
                                           timeout=20).read() for b in frei]
        wahl, _ = gemini(
            prompts.auswahl('foto', satz, len(vorschau),
                [{'index': i, 'title': b['titel'], 'caption': b['beschreibung'][:500]}
                 for i, b in enumerate(frei)], regel_text(), 'lang' if B > H else 'short'),
            {'type': 'OBJECT', 'properties': {'nummer': {'type': 'INTEGER'}}, 'required': ['nummer']},
            temperatur=0.1, bilder=vorschau, modelle=SEHEN)
        n = wahl['nummer']
        if type(n) is not int or not 0 <= n < len(frei):
            return None, None
        b = frei[n]
        ziel = PIXABAY_CACHE / f"foto_{hashlib.sha1(b['gross'].encode()).hexdigest()[:12]}.jpg"
        if not ziel.exists():
            ziel.write_bytes(urllib.request.urlopen(urllib.request.Request(b['gross'], headers=WIKI_KENNUNG),
                                                    timeout=60).read())
        Image.open(ziel).convert('RGB').save(ziel, 'JPEG', quality=92)  # einheitlich JPEG
        benutzt.add(b['titel'])
        return ziel, {'quelle': 'Wikimedia Commons', 'seite': b['seite'], 'von': b['autor'], 'lizenz': b['lizenz']}
    except Exception as e:
        print('Fotowahl nicht moeglich:', str(e)[:120])
        return None, None


def mini_karte(karte, platz):
    """Kleine Karte + Platznummer oben, waehrend darunter der Praxis-Clip
    laeuft - so bleibt klar, um welches Werkzeug es geht."""
    k = Image.open(karte).convert('RGB')
    x, y, breite, hoehe = einpassen(k.size, LAYOUT['mini'])
    k = k.resize((breite, hoehe), Image.LANCZOS)
    img = Image.new('RGBA', (B, H), (0, 0, 0, 0))
    schatten = Image.new('RGBA', (B, H), (0, 0, 0, 0))
    ImageDraw.Draw(schatten).rounded_rectangle((x, y + 10, x + breite, y + 10 + k.height), 20, fill=(0, 0, 0, 190))
    img.alpha_composite(schatten.filter(ImageFilter.GaussianBlur(14)))
    maske = Image.new('L', k.size, 0)
    ImageDraw.Draw(maske).rounded_rectangle((0, 0, *k.size), 20, fill=255)
    img.paste(k, (x, y), maske)
    if platz:
        f = schrift(80, TITEL_SCHRIFT)
        t = f'#{platz}'
        schrift_text(img, (LAYOUT['rechts'] - ImageDraw.Draw(img).textlength(t, font=f) - 24,
                           LAYOUT['mini'][1] + 22), t, f, rand=3)
    return img


def bild_rgb(im):
    """Echte Transparenz sichtbar machen, statt verborgene RGB-Pixel anzuzeigen."""
    if 'A' not in im.getbands() and 'transparency' not in im.info:
        return im.convert('RGB')
    rgba = im.convert('RGBA')
    if rgba.getchannel('A').getextrema()[0] == 255:
        return rgba.convert('RGB')
    raster = Image.new('RGBA', rgba.size, (240, 240, 240, 255))
    d = ImageDraw.Draw(raster)
    block = max(12, min(rgba.size) // 16)
    for y in range(0, rgba.height, block):
        for x in range(0, rgba.width, block):
            if (x // block + y // block) % 2:
                d.rectangle((x, y, x + block - 1, y + block - 1), fill=(210, 210, 210, 255))
    return Image.alpha_composite(raster, rgba).convert('RGB')


def karten_ebene(karte, kasten=None):
    """Die Karte allein (abgerundet, mit Schatten) auf durchsichtigem Bild."""
    k = bild_rgb(Image.open(karte))
    x, y, w, h = einpassen(k.size, LAYOUT['foto'] if kasten else LAYOUT['karte'])
    k = k.resize((w, h), Image.LANCZOS)
    img = Image.new('RGBA', (B, H), (0, 0, 0, 0))
    schatten = Image.new('RGBA', (B, H), (0, 0, 0, 0))
    ImageDraw.Draw(schatten).rounded_rectangle((x, y + 14, x + k.width, y + 14 + k.height), 28,
                                              fill=(0, 0, 0, 170))
    img.alpha_composite(schatten.filter(ImageFilter.GaussianBlur(18)))
    maske = Image.new('L', k.size, 0)
    ImageDraw.Draw(maske).rounded_rectangle((0, 0, *k.size), 28, fill=255)
    img.paste(k, (x, y), maske)
    return img


def karten_filter(hg, ebene, kpfad):
    """ffmpeg-Eingaben und Filter fuer einen Karten-Abschnitt: Hintergrund
    abgedunkelt und weich, Karte gleitet in 0,35 s von unten herein und blendet
    auf (sichtbarer Wechsel je Platz), Schrift obenauf."""
    ist_bild = Path(hg).suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')
    if not Path(hg).suffix:  # heruntergeladene Demo-Bilder haben teils keinen Dateisuffix
        try:
            with Image.open(hg) as im:
                im.verify()
            ist_bild = True
        except (OSError, ValueError):
            pass
    hg_ein = (['-loop', '1', '-framerate', str(FPS), '-i', str(hg)] if ist_bild
              else ['-stream_loop', '-1', '-i', str(hg)])
    filt = (f'[0:v]scale={B}:{H}:force_original_aspect_ratio=increase,crop={B}:{H},setsar=1,fps={FPS},'
            f'eq=brightness=-0.12:saturation=0.95,gblur=sigma=18[bg];'
            f'[2:v]format=rgba,fade=in:st=0:d=0.35:alpha=1[k];'
            f"[bg][k]overlay=x=0:y='32*max(0,1-t/0.35)':eval=frame[b1];"
            f'[b1][1:v]overlay=0:0,format=yuv420p')
    if kpfad is None:  # Abschnitt ohne Karte: nur Hintergrund + Schrift
        return [*hg_ein, '-loop', '1', '-framerate', str(FPS), '-i', str(ebene)], filt.split('[2:v]')[0] +             '[bg][1:v]overlay=0:0,format=yuv420p'
    return [*hg_ein, '-loop', '1', '-framerate', str(FPS), '-i', str(ebene),
            '-loop', '1', '-framerate', str(FPS), '-i', str(kpfad)], filt


def hintergrund_holen(s, schon, dauer, quellen, aus):
    """Einmal je Video: bewegter, ruhiger Hintergrund (Kanal-Suchbegriff), den
    die KI aus den Pixabay-Vorschaubildern waehlt. Rueckfall: Farbverlauf."""
    suche = s.get('hintergrund_suche') or 'abstract technology background'
    clip, q = clip_fuer(suche, schon, dauer, f'calm, slow, dark {suche}, no text, no people, no logos')
    if clip:
        quellen.append(q)
        return clip
    pfad = aus / 'verlauf.png'
    verlauf_bild(akzent_farbe(s)).save(pfad)
    return pfad


def verlauf_bild(akzent):
    """Rueckfall-Hintergrund: dunkel in der Kanalfarbe. GEMESSEN: weisse
    GitHub-Karten unscharf als Hintergrund ergaben ein mattes Grau."""
    v = np.linspace(0, 1, H)[:, None, None]
    oben, unten = np.array(akzent) * 0.28, np.array((4, 6, 14))
    return Image.fromarray(np.repeat((oben * (1 - v) + unten * v).astype(np.uint8), B, axis=1))


FORTSCHRITT = {'plaetze': [], 'aktuell': None}  # in main() je Abschnitt gesetzt


def fortschritt_zeichnen(img, akzent):
    """GEMESSEN 04.10.2026 (Vorbild sprich.ai): eine Leiste oben zeigt, wo man in
    der Liste steht - der Zuschauer sieht, dass noch etwas kommt, und bleibt."""
    plaetze, akt = FORTSCHRITT['plaetze'], FORTSCHRITT['aktuell']
    if len(plaetze) < 3:
        return
    d = ImageDraw.Draw(img)
    y, breite = LAYOUT['progress_y'], min(700, 110 * (len(plaetze) - 1))
    xs = [LAYOUT['mitte'] - breite / 2 + breite * k / (len(plaetze) - 1) for k in range(len(plaetze))]
    grau = (110, 120, 135, 255)
    d.line((xs[0], y, xs[-1], y), fill=grau, width=5)
    if akt in plaetze:
        d.line((xs[0], y, xs[plaetze.index(akt)], y), fill=akzent + (255,), width=7)
    for x, p in zip(xs, plaetze):
        if p == akt:
            r = 24
            d.ellipse((x - r, y - r, x + r, y + r), fill=akzent + (255,), outline=(255, 255, 255, 255), width=4)
            f = schrift(30, TITEL_SCHRIFT)
            d.text((x - d.textlength(str(p), font=f) / 2, y - 19), str(p), font=f, fill=(8, 16, 24, 255))
        elif akt is not None and p > akt:  # schon gezeigt (Countdown)
            d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=akzent + (255,))
        else:
            d.ellipse((x - 11, y - 11, x + 11, y + 11), fill=(20, 26, 36, 255), outline=grau, width=4)


def bild_fuer(teil, titel, nr, gesamt, durchsichtig=False, karte=None, akzent=(32, 210, 190)):
    """Ebene je Abschnitt: Titel, Platz, Name.
    durchsichtig=True: nur Schrift + sanfte Abdunklung, als Ebene ueber einem
    Videoclip. karte: Vorschaubild der Quelle, gross in der Mitte."""
    if karte:
        # Nur Schrift - Hintergrund (bewegter Clip) und Karte (fliegt ein)
        # setzt ffmpeg darunter bzw. dazu. GEMELDET: „wirkt wie eine Diashow".
        img = Image.new('RGBA', (B, H), (0, 0, 0, 0))
        # Name gross unter der Platznummer - auf Hugging-Face-Karten ist er winzig.
        # GEMESSEN: unter der Karte klebte er an den Untertiteln (gelb ueber weiss).
        if teil.get('name'):
            fn = text_font(teil['name'], 52)
            nb = ImageDraw.Draw(img).textlength(teil['name'], font=fn)
            schrift_text(img, (LAYOUT['mitte'] - nb / 2, LAYOUT['name_y']), teil['name'], fn, akzent)
    elif durchsichtig:
        img = Image.new('RGBA', (B, H), (0, 0, 0, 0))
        schatten = np.zeros((H, B, 4), dtype=np.uint8)
        a = np.zeros(H)
        oben = min(H, LAYOUT['foto'][1] + 60)
        unten = LAYOUT['foto'][3]
        a[:oben] = np.linspace(160, 0, oben)
        a[unten:] = np.linspace(0, 150, H - unten)
        schatten[..., 3] = a[:, None].astype(np.uint8)
        img = Image.alpha_composite(img, Image.fromarray(schatten, 'RGBA'))
    else:
        img = hintergrund(nr)
    if nr == 0 or teil.get('platz'):
        titel_zeichnen(img, titel, akzent)
    fortschritt_zeichnen(img, akzent)
    d = ImageDraw.Draw(img)
    if teil.get('platz'):
        f = schrift(110, TITEL_SCHRIFT)
        t = f"#{teil['platz']}"
        schrift_text(img, (LAYOUT['mitte'] - d.textlength(t, font=f) / 2,
                           LAYOUT['platz_y']), t, f, rand=3)
    # GEMELDET 04.10.2026 (Flop-Video Skydance): Bei einer Geschichte schrieb die KI
    # „Part 1 ... Part 7" ins Namensfeld - eingeblendet wirkte das verwirrend.
    # Namen gehoeren nur zu Ranglisten-Plaetzen.
    if teil.get('name') and (teil.get('platz') or B > H) and not karte:
        f = text_font(teil['name'], 52 if teil.get('platz') else 42)
        y = LAYOUT['name_y'] if teil.get('platz') else 150
        schrift_text(img, (LAYOUT['mitte'] - d.textlength(teil['name'], font=f) / 2,
                           y), teil['name'], f, akzent)
    return img


PIXABAY_CACHE = Path('clips')
REGELN = []  # gelernte Regeln des Kanals (lernen.py), in main() gesetzt
# Stuecke, die eine Urheberrechts-Meldung ausgeloest haben - nie wieder nehmen
MUSIK_SPERRE = Path(__file__).resolve().parent.parent / 'musik_gesperrt.json'


def regel_text():
    return ('\nRules learned from earlier quality reviews: ' + ' | '.join(REGELN)) if REGELN else ''
# Eigene, ehrliche Kennung. GEMESSEN: Pixabays Schutzdienst blockt die
# Standard-Kennung „Python-urllib" (HTTP 403, Fehler 1010); mit Kennung: 200.
KENNUNG = {'User-Agent': 'Contentfabrik/1.0 (privates Video-Tool)'}
WIKI_KENNUNG = {'User-Agent': 'Contentfabrik/1.0 (private video tool; github.com/aKhaaaaaan)'}


# GEMESSEN 02.10.2026: Ein reiner Greenscreen-Clip landete als Hintergrund
# hinter „#2 LTX 2.5" - Rohmaterial zum Freistellen, nie als Bild brauchbar.
UNBRAUCHBAR = re.compile(r'green ?screen|chroma|blue ?screen', re.I)


def waehle(kandidaten, satz):
    """Die KI sieht die Vorschaubilder und nimmt das, was zum gesprochenen Satz
    passt. Passt keins oder faellt die Auswahl aus: [] statt beliebigem Material."""
    import urllib.request
    if not kandidaten or not satz or not os.environ.get('GEMINI_API_KEY'):
        return []
    try:
        bilder = [urllib.request.urlopen(urllib.request.Request(
            next(v['thumbnail'] for art in ('large', 'medium', 'small', 'tiny')
                 if (v := h['videos'].get(art, {})).get('thumbnail')), headers=KENNUNG), timeout=20).read()
                  for h in kandidaten]
        from skript import gemini, SEHEN
        wahl, _ = gemini(
            prompts.auswahl('stock', satz, len(bilder),
                            [{'index': i, 'tags': h.get('tags', '')} for i, h in enumerate(kandidaten)],
                            regel_text(), 'lang' if B > H else 'short'),
            {'type': 'OBJECT', 'properties': {'nummer': {'type': 'INTEGER'}}, 'required': ['nummer']},
            # GEMESSEN: mit dem grossen Modell ~60 s je Abschnitt (384 s je Video)
            temperatur=0.1, bilder=bilder, modelle=SEHEN)
        n = wahl['nummer']
        return [kandidaten[n]] if type(n) is int and 0 <= n < len(kandidaten) else []
    except Exception as e:
        print('Clip-Auswahl ausgefallen - anderes Bildmaterial verwenden:', type(e).__name__)
        return []


def kurz_zahl(n):
    return f'{n / 1e6:.1f}M' if n >= 1e6 else f'{n / 1e3:.1f}K' if n >= 1e3 else str(n)


def hf_karte(modell, ziel):
    """Eigene Karte aus den offiziellen Hugging-Face-Daten. GEMESSEN: Deren
    Vorschaubilder sind alle derselbe blau-orange Verlauf mit winzigem Namen -
    jeder Platz sah gleich aus. Jetzt: Name gross, Aufgabe, Likes, Downloads."""
    import urllib.request
    d = json.load(urllib.request.urlopen(urllib.request.Request(
        f'https://huggingface.co/api/models/{modell}', headers=KENNUNG), timeout=20))
    W, Hk = 1200, 640
    v = np.linspace(0, 1, W)[None, :, None]
    img = Image.fromarray(np.repeat((np.array((22, 30, 52)) * (1 - v) + np.array((10, 14, 28)) * v)
                                    .astype(np.uint8), Hk, axis=0))
    dr = ImageDraw.Draw(img)
    grau, akzent = (150, 160, 180), (32, 210, 190)
    dr.text((64, 56), d.get('author') or modell.split('/')[0], font=schrift(44), fill=grau)
    name = modell.split('/')[-1]
    groesse = 104
    while dr.textlength(name, font=schrift(groesse, TITEL_SCHRIFT)) > W - 128 and groesse > 48:
        groesse -= 4
    dr.text((64, 116), name, font=schrift(groesse, TITEL_SCHRIFT), fill=(255, 255, 255))
    aufgabe = (d.get('pipeline_tag') or '').replace('-to-', ' to ').replace('-', ' ').upper()
    if aufgabe:
        f = schrift(38)
        b = dr.textlength(aufgabe, font=f)
        dr.rounded_rectangle((64, 270, 64 + b + 48, 336), 33, fill=akzent)
        dr.text((88, 280), aufgabe, font=f, fill=(8, 16, 24))
    # GEFUNDEN von der KI-Pruefung: „0 Downloads" bei einem neuen Modell (zaehlt
    # nur 30 Tage) wirkt wie ein Fehler - eine 0 wird nicht gezeigt.
    werte = [(w, z) for w, z in (('LIKES', d.get('likes', 0)), ('DOWNLOADS', d.get('downloads', 0))) if z]
    for x, (wort, zahl) in zip((64, 520), werte):
        dr.text((x, 392), kurz_zahl(zahl), font=schrift(96, TITEL_SCHRIFT), fill=(255, 214, 10))
        dr.text((x + 4, 504), wort, font=schrift(34), fill=grau)
    f = schrift(32)
    dr.text((W - 64 - dr.textlength('huggingface.co', font=f), Hk - 72), 'huggingface.co', font=f, fill=grau)
    img.save(ziel)
    return ziel


def karte_fuer(url):
    """Offizielles Vorschaubild der Quelle (GitHub/Hugging Face) - zeigt genau
    das genannte Werkzeug mit Name, Beschreibung, Sternen. Die Plattformen
    stellen diese Bilder zum Teilen bereit."""
    import urllib.request, hashlib
    m = re.match(r'https?://(github\.com|huggingface\.co)/([\w.-]+/[\w.-]+)', url or '')
    if not m:
        return None
    adresse = (f'https://opengraph.githubassets.com/1/{m[2]}' if m[1] == 'github.com' else
               f'https://cdn-thumbnails.huggingface.co/social-thumbnails/models/{m[2]}.png')
    PIXABAY_CACHE.mkdir(exist_ok=True)
    ziel = PIXABAY_CACHE / f"karte_{hashlib.sha1(adresse.encode()).hexdigest()[:12]}.png"
    if m[1] == 'huggingface.co':
        try:  # Zahlen sind tagesaktuell - darum je Lauf neu zeichnen, nicht zwischenspeichern
            return hf_karte(m[2], PIXABAY_CACHE / f"karte_hf_{hashlib.sha1(m[2].encode()).hexdigest()[:12]}.png")
        except Exception as e:
            print('Eigene HF-Karte nicht moeglich, nehme Vorschaubild:', str(e)[:100])
    try:
        if not ziel.exists():
            ziel.write_bytes(urllib.request.urlopen(urllib.request.Request(adresse, headers=KENNUNG), timeout=30).read())
        Image.open(ziel).verify()
        return ziel
    except Exception as e:
        print('Vorschaubild fehlt:', adresse, str(e)[:100])
        return None


def demo_fuer(url, satz='', benutzt=None, gewollt=None):
    """Echtes Anwendungsbeispiel von der Modellseite statt Symbol-Clip.
    GEMELDET (KI-Analyse 04.10.2026): „Keine echten Anwendungsbeispiele - nur
    Grafiken, das gleiche Template 7-mal." Pixabay zeigt nie das echte Modell.
    Die Beschreibung (README) auf Hugging Face/GitHub enthaelt meist Beispiel-
    bilder (Ergebnisse, Oberflaeche). Die KI waehlt das, das zeigt, WAS das
    Werkzeug macht - keine Logos, Abzeichen oder Benchmark-Tabellen.
    Gibt (pfad, quelle) oder (None, None) zurueck."""
    import urllib.request, urllib.parse, hashlib
    m = re.match(r'https?://(github\.com|huggingface\.co)/([\w.-]+/[\w.-]+)', url or '')
    if not m:
        return None, None
    roh, basis = ((f'https://huggingface.co/{m[2]}/raw/main/README.md', f'https://huggingface.co/{m[2]}/resolve/main/')
                  if m[1] == 'huggingface.co' else
                  (f'https://raw.githubusercontent.com/{m[2]}/HEAD/README.md',
                   f'https://raw.githubusercontent.com/{m[2]}/HEAD/'))
    try:
        text = urllib.request.urlopen(urllib.request.Request(roh, headers=KENNUNG), timeout=20).read().decode(
            'utf-8', 'replace')
    except Exception as e:
        print('Keine Beschreibung fuer Beispielbilder:', m[2], str(e)[:80])
        return None, None
    links = re.findall(r'!\[[^\]]*\]\(\s*([^)\s]+)', text) + re.findall(r'<img[^>]+src=["\']([^"\']+)', text, re.I)
    kandidaten = []
    for l in links:
        l = urllib.parse.urljoin(basis, l.replace('/blob/', '/raw/'))
        if re.search(r'shields\.io|badge|logo|icon|avatar|\.svg(\?|$)|license|star-history|discord|twitter',
                     l, re.I) or l in kandidaten:
            continue
        kandidaten.append(l)
    kandidaten = [l for l in kandidaten if l not in (benutzt or set())]
    if m[2] == 'Qwen/Qwen-Image-2.1':
        kandidaten = [l for l in kandidaten if not l.endswith(('example-01.png', 'example-43.png'))]
    if gewollt:
        kandidaten = [l for l in kandidaten if l == gewollt]
    bilder, pfade = [], []
    PIXABAY_CACHE.mkdir(exist_ok=True)
    for l in kandidaten[:8]:
        ziel = PIXABAY_CACHE / f"demo_{hashlib.sha1(l.encode()).hexdigest()[:12]}"
        try:
            if not ziel.exists():
                ziel.write_bytes(urllib.request.urlopen(urllib.request.Request(l, headers=KENNUNG), timeout=30).read())
            with Image.open(ziel) as im:
                if im.width < 480 or im.height < 270:  # Vorschau-Schnipsel, Symbole
                    continue
                vorschau = bild_rgb(im)
                if ('A' in im.getbands() or 'transparency' in im.info):
                    sichtbar = ziel.with_name(ziel.name + '_sichtbar.jpg')
                    vorschau.save(sichtbar, 'JPEG', quality=95)
                    ziel = sichtbar
                vorschau.thumbnail((512, 512))
                import io
                puffer = io.BytesIO(); vorschau.save(puffer, 'JPEG', quality=80)
            bilder.append(puffer.getvalue()); pfade.append((ziel, l))
        except Exception:
            continue
    if not pfade:
        return None, None
    if gewollt:
        ziel, l = pfade[0]
        print('Beispielbild (redaktionelle Regie):', m[2], l[:90])
        return ziel, {'quelle': 'Beispielbild', 'seite': url, 'datei': l}
    # Sparsam: Die Wahl je Modellseite wird gespeichert - dasselbe Modell kommt
    # an mehreren Tagen vor, die KI muss nicht jedes Mal neu schauen.
    import hashlib as _h
    merk_key = json.dumps([prompts.VERSION, m[2], satz, [l for _, l in pfade],
                          'lang' if B > H else 'short'], ensure_ascii=False)
    merk = PIXABAY_CACHE / f"demo_wahl_{_h.sha1(merk_key.encode()).hexdigest()[:12]}.json"
    if merk.exists():
        alt = json.loads(merk.read_text(encoding='utf-8'))
        treffer = [(z, l) for z, l in pfade if l == alt.get('datei')]
        if treffer:
            return treffer[0][0], {'quelle': 'Beispielbild', 'seite': url, 'datei': alt['datei']}
        if alt.get('datei') is None:
            return None, None
    try:
        from skript import gemini, SEHEN
        wahl, _ = gemini(
            prompts.auswahl('demo', satz, len(bilder), [{'tool': m[2], 'source_url': url}],
                           regel_text(), 'lang' if B > H else 'short'),
            {'type': 'OBJECT', 'properties': {'nummer': {'type': 'INTEGER'}}, 'required': ['nummer']},
            temperatur=0.1, bilder=bilder, modelle=SEHEN)
        n = wahl['nummer']
    except Exception as e:
        print('Beispielbild-Auswahl ohne KI nicht moeglich:', str(e)[:120])
        return None, None
    if type(n) is not int or not 0 <= n < len(pfade):
        print('Kein brauchbares Beispielbild:', m[2])
        merk.write_text(json.dumps({'datei': None}), encoding='utf-8')
        return None, None
    ziel, l = pfade[n]
    merk.write_text(json.dumps({'datei': l}), encoding='utf-8')
    print('Beispielbild:', m[2], l[:90])
    # Bilder der Modellseite stehen unter der Lizenz des Projekts - Quelle nennen
    return ziel, {'quelle': 'Beispielbild', 'seite': url, 'datei': l}


def aufnahme_fuer(url, dauer, ziel):
    """Echte Bildschirmaufnahme der Modellseite (Hugging Face/GitHub).
    GEMESSEN 04.10.2026 an zwei Vorbildern: oben laeuft eine echte Aufnahme
    (Webseite, Mauszeiger, Scrollen) - das macht sie glaubwuerdig. Unsere
    Pixabay-Clips zeigten Archive, Straende, Augenaerzte statt des Werkzeugs.
    Ein unsichtbarer Browser (Playwright, Apache 2.0) oeffnet die Seite, ein
    Mauszeiger faehrt darueber, die Seite scrollt langsam zu den Beispielen.
    Gibt den mp4-Pfad oder None zurueck (dann wie bisher Beispielbild/Clip)."""
    import tempfile, shutil as _sh
    if not re.match(r'https?://(github\.com|huggingface\.co)/[\w.-]+/[\w.-]+', url or ''):
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    ordner = Path(tempfile.mkdtemp())
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # GEMESSEN (Probevideo 04.10.2026): 1280 px breit und Dunkelmodus = winzige
            # Schrift auf dunkler Flaeche, auf dem Handy nicht lesbar. Schmaler + hell.
            kontext = browser.new_context(viewport={'width': 900, 'height': 660}, device_scale_factor=1,
                                          record_video_dir=str(ordner), record_video_size={'width': 900, 'height': 660},
                                          color_scheme='light', locale='en-US')
            beginn = time.time()
            seite = kontext.new_page()
            # GEMESSEN: Auf GitHub zeigte die Aufnahme nur die Dateiliste - direkt zur
            # Beschreibung (README) springen, dort stehen Bilder und Erklaerung.
            seite.goto(url + ('#readme' if 'github.com' in url else ''), wait_until='domcontentloaded', timeout=30000)
            seite.wait_for_timeout(1500)
            geladen = time.time() - beginn
            # Sichtbarer Mauszeiger (die Aufnahme zeigt sonst keinen)
            seite.evaluate("""() => {
                const c = document.createElement('div');
                c.innerHTML = '<svg width="34" height="34" viewBox="0 0 24 24"><path d="M4 2l15 9-7 1.5L8.5 20z" '
                  + 'fill="white" stroke="black" stroke-width="1.5"/></svg>';
                Object.assign(c.style, {position: 'fixed', left: '260px', top: '180px', zIndex: 2147483647,
                  pointerEvents: 'none', transition: 'left 1.8s ease-in-out, top 1.8s ease-in-out'});
                document.body.appendChild(c);
                setTimeout(() => { c.style.left = '450px'; c.style.top = '320px'; }, 200);
                setTimeout(() => { c.style.left = '390px'; c.style.top = '400px'; }, 2200);
            }""")
            for _ in range(max(1, int(dauer * 10))):  # weich scrollen, ~280 px je Sekunde
                seite.mouse.wheel(0, 28)
                seite.wait_for_timeout(100)
            video = seite.video.path()
            kontext.close(); browser.close()
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f'{geladen:.2f}', '-i', str(video),
                        '-t', f'{dauer:.3f}', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
                        str(ziel)], check=True)
        return ziel if Path(ziel).exists() and Path(ziel).stat().st_size > 20000 else None
    except Exception as e:
        print('Bildschirmaufnahme nicht moeglich:', url, str(e)[:150])
        return None
    finally:
        _sh.rmtree(ordner, ignore_errors=True)


def demo_stueck(bild, ebene, mini, dauer, ziel):
    """Beispielbild oder Bildschirmaufnahme: unscharf vergroessert als
    Hintergrund, scharf in der Mitte (passt jede Form ein); Mini-Karte oben,
    Text darueber. GIFs laufen als Animation, mp4 (Aufnahme) als Video."""
    if str(bild).endswith('.mp4'):
        ein = ['-i', str(bild)]
    else:
        gif = Image.open(bild).format == 'GIF'
        ein = (['-ignore_loop', '0', '-i', str(bild)] if gif else
               ['-loop', '1', '-framerate', str(FPS), '-i', str(bild)])
    f = (f'[0:v]fps={FPS},split[a][b];'
         f'[a]scale={B}:{H}:force_original_aspect_ratio=increase,crop={B}:{H},boxblur=24:2,eq=brightness=-0.12[hg];'
         # Vordergrund bleibt zwischen Mini-Karte und sprachgebundenen Akzenten.
         f'[b]scale={LAYOUT["karte"][2] - LAYOUT["karte"][0]}:'
         f'{LAYOUT["karte"][3] - LAYOUT["karte"][1]}:force_original_aspect_ratio=decrease,setsar=1[vg];'
         f'[hg][vg]overlay={(LAYOUT["karte"][0] + LAYOUT["karte"][2]) / 2}-w/2:'
         f'{(LAYOUT["karte"][1] + LAYOUT["karte"][3]) / 2}-h/2[v];'
         f'[v][1:v]overlay=0:0[x];[x][2:v]overlay=0:0,format=yuv420p')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *ein,
                    '-loop', '1', '-framerate', str(FPS), '-i', str(ebene),
                    '-loop', '1', '-framerate', str(FPS), '-i', str(mini), '-filter_complex', f,
                    '-t', f'{dauer:.3f}', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', str(ziel)],
                   check=True)


def clip_fuer(suche, schon, laenge, satz=''):
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
        daten = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=KENNUNG), timeout=30))
        cache.write_text(json.dumps(daten))
    kandidaten = [h for h in daten.get('hits', [])
                  if h['id'] not in schon and h.get('duration', 0) >= 3 and not UNBRAUCHBAR.search(h.get('tags', ''))
                  and any((h['videos'].get(art) or {}).get('url') for art in ('large', 'medium', 'small'))][:6]
    for hit in waehle(kandidaten, satz):
        # Der zentrale Hochformat-Ausschnitt verliert viel Aufloesung: beste
        # angebotene Fassung nehmen; alte kleinere Cache-Dateien nicht verwechseln.
        v = next(hit['videos'][art] for art in ('large', 'medium', 'small')
                 if (hit['videos'].get(art) or {}).get('url'))
        variante = hashlib.sha1(v['url'].encode()).hexdigest()[:10]
        ziel = PIXABAY_CACHE / f"pixabay_{hit['id']}_{variante}.mp4"
        if not ziel.exists():
            with urllib.request.urlopen(urllib.request.Request(v['url'], headers=KENNUNG), timeout=60) as r:
                ziel.write_bytes(r.read())
        schon.add(hit['id'])
        return ziel, {'quelle': 'Pixabay', 'id': hit['id'], 'seite': hit['pageURL'], 'von': hit.get('user')}
    return None, None


def ass_zeit(s):
    h, r = divmod(s, 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def angleichen(woerter, skripttext):
    """Woerter aus dem SKRIPT, nur die Zeiten von Whisper. GEMESSEN: Whisper
    hoerte „Lightrix" statt „Lightricks" und „QN" statt „Qwen" - der richtige
    Text steht aber im Skript, die Stimme spricht genau ihn."""
    import difflib
    ziel = skripttext.split()
    norm = lambda x: re.sub(r'[^a-z0-9]', '', x.lower())
    sm = difflib.SequenceMatcher(None, [norm(w['w']) for w in woerter], [norm(z) for z in ziel], autojunk=False)
    aus = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            aus += [{**woerter[i1 + k], 'w': ziel[j1 + k]} for k in range(i2 - i1)]
        elif j2 > j1:  # ersetzt oder von Whisper ueberhoert: Zeit gleichmaessig verteilen
            if i2 > i1:
                s, e = woerter[i1]['s'], woerter[i2 - 1]['e']
            else:
                s = aus[-1]['e'] if aus else 0.0
                e = woerter[i1]['s'] if i1 < len(woerter) else s + 0.3 * (j2 - j1)
            if e <= s:
                e = s + 0.25 * (j2 - j1)
            d = (e - s) / (j2 - j1)
            aus += [{'w': ziel[j1 + k], 's': s + k * d, 'e': s + (k + 1) * d} for k in range(j2 - j1)]
    return aus


def kokoro_ton(s, tempo, laengenziel):
    """Bisherige Kokoro-Stimme je Teil; gemessene Dauer einmal ans Ziel anpassen."""
    from kokoro_onnx import Kokoro
    kokoro = Kokoro('modelle/kokoro-v1.0.onnx', 'modelle/voices-v1.0.bin')
    rate = 24000
    # Gemessene Dauer einmal anpassen; keine Beschleunigung jenseits
    # natuerlicher Grenzen, feste Pausen bleiben in der Rechnung.
    for runde in range(2):
        teile, laengen = [], []
        for t in s['teile']:
            audio, rate = audioqualitaet.sprechen(kokoro, t['text'], s.get('stimme', 'af_heart'), tempo)
            pause = np.zeros(int(rate * 0.25), dtype=np.float32)
            teile.append(np.concatenate([audio.astype(np.float32), pause]))
            laengen.append(len(teile[-1]) / rate)
        if runde:
            break
        neu = audioqualitaet.tempo_fuer(sum(laengen), laengenziel, tempo,
                                       dramaturgie.videoformat(s), .25 * len(s['teile']))
        if neu == tempo:
            break
        print(f'Ton {sum(laengen):.0f} s, Ziel {laengenziel} s - Tempo {tempo} -> {neu}')
        tempo = neu
    return np.concatenate(teile), rate, laengen, tempo


def erzaehlstimme(s):
    """Kanaleinstellung 'erzaehlstimme' (z. B. Gemini Orus) aus kanaele/*.json, sonst None."""
    for p in Path('kanaele').glob('*.json'):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if d.get('name') == s.get('kanal') and isinstance(d.get('erzaehlstimme'), dict):
            return d['erzaehlstimme']
    return None


def gemini_ton(s, wahl, grenzen):
    """Ganzes Skript in EINEM Gemini-TTS-Aufruf (Gratiskontingent knapp).

    GEMELDET 07.10.2026 nach Hoerprobe (Lauf 37680915854): „Stimme 4 ist schon
    dramatisch, ich denke das catcht die Aufmerksamkeit" = Gemini Orus mit
    Trailer-Regie. Kurze Pause vor der Wendung als Regie im Text. Zu lang ->
    tonhoehenerhaltend mit ffmpeg atempo, hoechstens 1,15. Gibt (ton, rate) oder None.
    """
    import stimme_gemini
    teile = []
    for i, t in enumerate(s['teile']):
        teile.append(('<short pause> ' if i and t.get('beat') == 'wendung' else '') + t['text'].strip())
    try:
        wav, modell = stimme_gemini.sprechen(' '.join(teile), wahl.get('stimme', 'Orus'), wahl.get('stil', ''))
    except (RuntimeError, OSError, KeyError) as e:
        print('Gemini-Stimme nicht verfuegbar, Kokoro spricht:', str(e)[:200])
        return None
    import io
    with wave.open(io.BytesIO(wav)) as w:
        rate = w.getframerate()
        ton = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    dauer = len(ton) / rate
    oben = grenzen[1]
    if dauer > oben:
        faktor = min(1.15, dauer / oben)
        roh = subprocess.run(['ffmpeg', '-loglevel', 'error', '-f', 'f32le', '-ar', str(rate), '-ac', '1', '-i', '-',
                              '-filter:a', f'atempo={faktor:.3f}', '-f', 'f32le', '-'],
                             input=ton.tobytes(), capture_output=True, check=True).stdout
        ton = np.frombuffer(roh, dtype=np.float32).copy()
        print(f'Gemini-Stimme {dauer:.0f} s > {oben} s - Tempo x{faktor:.2f}')
    print(f'Erzaehlstimme: Gemini {wahl.get("stimme")} ({modell}), {len(ton) / rate:.1f} s')
    return ton, rate


def laengen_aus_woertern(woerter, teile, gesamt):
    """Abschnittslaengen aus den Wortzeiten (angleichen() liefert genau die Skriptwoerter)."""
    starts, n = [], 0
    for t in teile:
        starts.append(woerter[n]['s'] if n < len(woerter) else gesamt)
        n += len(t['text'].split())
    grenzen = [0.0] + starts[1:] + [gesamt]
    return [max(0.3, b - a) for a, b in zip(grenzen, grenzen[1:])]


def musik_kette(pegel, laenge, pausen=(), stille=0.55):
    """ffmpeg-Filter fuer das Musikbett.

    GEMELDET 07.10.2026: Zuschauer sollen nicht wegwischen; rund 70 % entscheiden in
    den ersten 2 s. Darum kein 1-s-Einblenden mehr (Musik von Bild 1 an da), und vor
    jedem Wendepunkt setzt die Musik ~0,5 s ganz aus - die Stille vor Riser-Ende und
    Impact ist ein Musterbruch. Pausen in den ersten 2 s und am Ende entfallen.
    """
    fenster = [(max(0.0, t - stille), t) for t in sorted(set(pausen)) if 2.0 <= t <= laenge - 1.5]
    kette = (f'loudnorm=I=-18:TP=-3:LRA=7,aresample=48000,volume={pegel},afade=t=in:d=0.05,'
             f'afade=t=out:st={max(0, laenge - 1.2):.3f}:d=1.2')
    if fenster:
        bedingung = '+'.join(f'between(t,{a:.3f},{b:.3f})' for a, b in fenster)
        kette += f",volume=0:enable='{bedingung}'"
    return kette


def nachbar_bild(aus, i, vorherige_id):
    """Naechste schon gepruefte Illustration fuer Einstellung i, nie das Bild davor."""
    kandidaten = [p for p in Path(aus).glob('ill_*.jpg') if re.fullmatch(r'ill_\d\d\.jpg', p.name)
                  and p.name != f'ill_{i:02d}.jpg' and bildplan.material_id(p) != vorherige_id]
    return min(kandidaten, key=lambda p: abs(int(p.stem[4:]) - i)) if kandidaten else None


FIGUR_EINSETZEN = {'moeglich': True}  # gilt fuer einen bauen.py-Prozess (= einen Bauversuch)


def illustration_mit_ausweg(szene, ziel, kanal_slug, mit_figur, rand, videoformat):
    """Illustration; scheitert das Einsetzen der Kanalfigur, nicht das ganze Video verlieren.

    GEMESSEN 07.10.2026 (Run 37652008678, WeWork, Story 8/10): Figur in neue Szene
    einsetzen scheiterte 5x an Einstellung 0 (Hintergrund der Referenz blieb).
    Anfang/Ende (rand): freigegebenes Originalbild der Kanalfigur (wie modus
    'figur'); Mitte: gepruefte Szene ohne Figur. Kein fremder Hintergrundersatz.
    """
    import illustration
    def versuch(figur):
        try:
            return illustration.bild(szene, ziel, kanal_slug, figur=figur, videoformat=videoformat)
        except Exception as e:  # nie den ganzen Videobau kippen
            print('Illustration nicht moeglich:', str(e)[:120])
            return None
    # GEMESSEN 08.10.2026 (Lauf 37760482364): 7x 'Figur nicht einsetzbar', je ~2 min
    # (Szene + 2 Einsetzversuche + Pruefungen) - der Bau lief ins Zeitlimit. Nach dem
    # ersten Fehlschlag im Lauf nicht weiter versuchen.
    if mit_figur and not FIGUR_EINSETZEN['moeglich']:
        ill = None
    else:
        ill = versuch(mit_figur)
    if ill or not mit_figur:
        return ill
    FIGUR_EINSETZEN['moeglich'] = False
    original = illustration.FIGUREN / f'{kanal_slug}.jpg'
    if rand and original.is_file():
        print('Figur nicht einsetzbar - Originalbild der Kanalfigur')
        return original
    print('Figur nicht einsetzbar - gepruefte Szene ohne Figur')
    return versuch(False)


def untertitel(woerter, pfad, profil=None, akzente=()):
    """Wort-fuer-Wort-Untertitel: drei Woerter sichtbar, das gesprochene gelb."""
    # GEMESSEN 04.10.2026 am Vorbild (alan.buildz): schmale fette Schrift in
    # Grossbuchstaben, 2-3 Woerter, das gesprochene Wort mit farbigem KASTEN
    # (nicht nur eingefaerbt). Zwei Ebenen mit identischem Text: unten (K) nur
    # der Kasten des aktuellen Worts (BorderStyle 3 = Kasten, alle anderen
    # Woerter unsichtbar), oben (U) die weisse Schrift - so sitzt der Kasten
    # exakt hinter dem Wort. Anton (SIL OFL) liegt in schriften/.
    groesse, zeichen, gruppen_max = (64, 40, 7) if B > H else {
        'kompakt': (84, 14, 2)}.get(profil, (96, 18, 3))
    rand = H - LAYOUT['untertitel_y'] + (40 if profil == 'hoch' and H > B else 0)
    breite = LAYOUT['rechts'] - LAYOUT['links'] - 60
    akzent_groesse = 50 if B > H else 60
    kopf = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {B}\nPlayResY: {H}\nWrapStyle: 2\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
            "Bold, BorderStyle, Outline, Shadow, Alignment, MarginV\n"
            # MarginV 520: unten liegen bei TikTok/Shorts Beschreibung und Knoepfe
            f"Style: U,Anton,{groesse},&H00FFFFFF,&H00000000,&H96000000,0,1,5,2,2,{rand}\n"
            f"Style: K,Anton,{groesse},&HFF000000,&H005A2BFF,&HFF000000,0,3,12,0,2,{rand}\n"
            f"Style: A,Montserrat,{akzent_groesse},&H00FFFFFF,&H00140E0A,&H00140E0A,-1,3,10,0,5,0\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Text\n")
    # Whisper kann einzelne Funktionswoerter mit Null-Dauer markieren. Mit dem
    # unmittelbar benachbarten Wort zusammen zeigen, ohne Zeiten zu erfinden.
    normal, offen, letzter_start = [], [], -1
    for roh in woerter:
        w = dict(roh)
        if not isinstance(w['w'], str) or any(isinstance(w[k], bool) or not isinstance(w[k], (int, float))
                or not math.isfinite(w[k]) for k in ('s', 'e')) \
                or not 0 <= w['s'] <= w['e'] or w['s'] < letzter_start:
            raise ValueError('Unbrauchbare Wortzeiten fuer Untertitel')
        letzter_start = w['s']
        if w['s'] == w['e']:
            offen.append(w)
            continue
        if offen:
            if w['s'] - offen[0]['s'] > .7:
                raise ValueError('Null-Wortzeiten ohne nahes gesprochenes Wort')
            w['w'] = ' '.join(x['w'] for x in offen) + ' ' + w['w']
            w['s'] = offen[0]['s']
            offen = []
        if normal and w['s'] == normal[-1]['s']:
            # GEMESSEN 07.10.2026 (Run 37649294220, WeWork): zwei Woerter mit
            # gleichem Start brachen den fertig geprueften Bau ab. Wie bei
            # Null-Dauer gemeinsam zeigen statt Zeiten zu erfinden.
            normal[-1]['w'] += ' ' + w['w']
            normal[-1]['e'] = max(normal[-1]['e'], w['e'])
            continue
        normal.append(w)
    if offen:
        if not normal or offen[-1]['e'] - normal[-1]['e'] > .7:
            raise ValueError('Null-Wortzeiten ohne nahes gesprochenes Wort')
        normal[-1]['w'] += ' ' + ' '.join(x['w'] for x in offen)
        normal[-1]['e'] = max(normal[-1]['e'], offen[-1]['e'])
    # GEMESSEN: Whisper trennt Zahlen („16" + „,000") - wieder zusammenfuegen.
    zusammen = []
    for w in normal:
        if not isinstance(w['w'], str) or not 0 <= w['s'] < w['e'] \
                or (zusammen and w['s'] < zusammen[-1]['s']):
            raise ValueError('Unbrauchbare Wortzeiten fuer Untertitel')
        if zusammen and w['w'][:1] in ',.%' and len(w['w']) > 1:
            zusammen[-1] = {**zusammen[-1], 'w': zusammen[-1]['w'] + w['w'], 'e': w['e']}
        else:
            zusammen.append(dict(w))
    woerter = zusammen
    # GEMELDET: „Animationstext springt manchmal willkuerlich". Ursache: Das
    # gesprochene Wort wurde IN der zentrierten Zeile vergroessert - die
    # Nachbarwoerter rutschten bei jedem Wort; lange Dreiergruppen brachen um.
    # Jetzt: Gruppen nach Zeichen (max. 18, ohne Umbruch, Satzende = neue
    # Gruppe), das Wort nur farbig; ein „Pop" der GANZEN Zeile je neuer Gruppe.
    zeig = lambda x: re.sub(r'[{}\\\r\n]', '', x.strip('.,!?;:"')).upper()
    font = schrift(groesse, str(SCHRIFTEN / 'Anton-Regular.ttf'))
    gruppen, g = [], []
    for w in woerter:
        laenge = sum(len(zeig(x['w'])) + 1 for x in g) + len(zeig(w['w']))
        candidate = ' '.join(zeig(x['w']) for x in g + [w])
        if g and (laenge > zeichen or len(g) == gruppen_max or g[-1]['w'][-1:] in '.!?'
                  or w['s'] - g[-1]['e'] > .7 or font.getlength(candidate) > breite):
            gruppen.append(g)
            g = []
        g.append(w)
    if g:
        gruppen.append(g)
    zeilen = []
    index = 0
    for gruppe in gruppen:
        text = ' '.join(zeig(x['w']) for x in gruppe)
        gfont = groesse
        while schrift(gfont, str(SCHRIFTEN / 'Anton-Regular.ttf')).getlength(text) > breite and gfont > 52:
            gfont -= 2
        if schrift(gfont, str(SCHRIFTEN / 'Anton-Regular.ttf')).getlength(text) > breite:
            raise ValueError('Untertitel enthaelt ein zu langes Wort fuer lesbare Darstellung')
        position = f'{{\\an2\\pos({LAYOUT["mitte"]},{H - rand})\\fs{gfont}}}'
        for j, w in enumerate(gruppe):
            pop = position
            weg, da = '{\\3a&HFF&}', '{\\3a&H00&}'  # Kasten aus / an
            kasten = pop + (weg + ' ').join((da if x is w else weg) + zeig(x['w']) for x in gruppe)
            text = pop + ' '.join(zeig(x['w']) for x in gruppe)
            i = index
            index += 1
            ende = min(woerter[i + 1]['s'], w['e'] + .25) if i + 1 < len(woerter) else w['e'] + .25
            if ende <= w['s']:
                raise ValueError('Ueberlappende oder doppelte Wortzeiten')
            zeilen.append(f"Dialogue: 0,{ass_zeit(w['s'])},{ass_zeit(ende)},K,{kasten}")
            zeilen.append(f"Dialogue: 1,{ass_zeit(w['s'])},{ass_zeit(ende)},U,{text}")
    for a in akzente:
        text = re.sub(r'[{}\\\r\n]', '', a['text'])
        f, lines, ax, ay = bildtext_layout(text, profil)
        tags = f'{{\\an5\\pos({ax},{ay})\\fs{f.size}\\fad(100,150)}}'
        anzeige = r'\N'.join(lines)
        zeilen.append(f"Dialogue: 2,{ass_zeit(a['s'])},{ass_zeit(a['e'])},A,{tags}{anzeige}")
    Path(pfad).write_text(kopf + '\n'.join(zeilen) + '\n', encoding='utf-8')


def main(skript_pfad, aus, vorlage=None):
    import rendercache
    aus = Path(aus); aus.mkdir(parents=True, exist_ok=True)
    s = json.loads(Path(skript_pfad).read_text(encoding='utf-8'))
    format_setzen(dramaturgie.videoformat(s))
    REGELN[:] = s.get('regeln', [])
    beginn = time.time()
    zeiten.clear()
    code_key = hashlib.sha256(Path(__file__).read_bytes() + Path(prompts.__file__).read_bytes()
                             + Path(audioqualitaet.__file__).read_bytes()
                             + Path(dramaturgie.__file__).read_bytes()
                             + Path(__file__).with_name('illustration.py').read_bytes()
                             + Path(__file__).with_name('infografik.py').read_bytes()
                             + Path(__file__).with_name('bibliothek.py').read_bytes()
                             + (Path(__file__).resolve().parents[1] / 'assets/illustrationen/katalog.json').read_bytes()).hexdigest()
    cache = rendercache.laden(vorlage) if vorlage else {}
    if vorlage and Path(vorlage).resolve() == aus.resolve():
        raise ValueError('Korrektur braucht einen eigenen Ausgabeordner')
    if cache:
        for p in Path(vorlage).iterdir():
            if p.is_file() and ((p.suffix in ('.wav', '.png', '.jpg', '.mp4') and p.name != 'short.mp4')
                                or p.name == 'woerter.json'):
                shutil.copy2(p, aus / p.name)
    wahl = erzaehlstimme(s)
    # Andere Stimme = anderer Ton: eigener Cache-Schluessel (Kokoro-Ton nie fuer Gemini halten).
    akey = rendercache.audio_key(dict(s, stimme=f"gemini:{wahl.get('stimme')}") if wahl else s, code_key)
    audio_cache = cache.get('audio') or {}
    audio_ok = (audio_cache.get('key') == akey
                and rendercache.dateien_ok(aus, ['stimme.wav', 'woerter.json'])
                and len(audio_cache.get('laengen', [])) == len(s['teile']))
    zeiten['stimme_wiederverwendet'] = audio_ok

    if audio_ok:
        rate, laengen, tempo = audio_cache['rate'], audio_cache['laengen'], audio_cache['tempo']
        woerter = json.loads((aus / 'woerter.json').read_text(encoding='utf-8'))
    else:
        tempo = s.get('tempo', 1.05)
        laengenziel = dramaturgie.laengen(s)
        with messen('stimme'):
            gemini = gemini_ton(s, wahl, laengenziel) if wahl and wahl.get('anbieter') == 'gemini' else None
            if gemini:
                ton, rate = gemini
                laengen = None  # folgt aus den Wortzeiten
            else:
                if wahl:
                    akey = rendercache.audio_key(s, code_key)  # Rueckfall Kokoro: passender Schluessel
                ton, rate, laengen, tempo = kokoro_ton(s, tempo, laengenziel)
        with wave.open(str(aus / 'stimme.wav'), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
            w.writeframes((np.clip(ton, -1, 1) * 32767).astype(np.int16).tobytes())

        with messen('zeitmarken'):
            from faster_whisper import WhisperModel
            modell = WhisperModel('base.en', device='cpu', compute_type='int8')
            # Ton direkt aus dem Speicher (16 kHz); umgeht die PyAV-Dateilesung.
            n16 = int(len(ton) * 16000 / rate)
            ton16 = np.interp(np.linspace(0, len(ton) - 1, n16), np.arange(len(ton)), ton).astype(np.float32)
            segs, _ = modell.transcribe(ton16, word_timestamps=True)
            woerter = [{'w': x.word.strip(), 's': x.start, 'e': x.end} for seg in segs for x in seg.words]
        woerter = angleichen(woerter, ' '.join(t['text'] for t in s['teile']))
        (aus / 'woerter.json').write_text(json.dumps(woerter), encoding='utf-8')
        if laengen is None:  # Gemini: ein durchgehender Ton, Abschnitte aus den Wortzeiten
            laengen = laengen_aus_woertern(woerter, s['teile'], len(ton) / rate)
    zeiten['tempo'] = tempo
    shots, plan_cache = bildplan.vorbereiten(s, laengen, woerter, cache)
    visuell = dict(s, teile=[shot['teil'] for shot in shots])
    (aus / 'bildplan.json').write_text(json.dumps(shots, indent=2), encoding='utf-8')
    akzente = dramaturgie.akzente(s['teile'], woerter, laengen)
    untertitel(woerter, aus / 'untertitel.ass', s.get('untertitel_profil'), akzente)
    (aus / 'dramaturgie.json').write_text(json.dumps({
        'videoformat': dramaturgie.videoformat(s), 'akzente': akzente,
        'beats': [{'teil': i, 's': round(sum(laengen[:i]), 2), 'dauer_s': round(d, 2),
                   'beat': t.get('beat'), 'bildmodus': t.get('bildmodus', 'auto')}
                  for i, (t, d) in enumerate(zip(s['teile'], laengen))]}, indent=2), encoding='utf-8')
    zustand = {'audio': {'key': akey, 'rate': rate, 'laengen': laengen, 'tempo': tempo},
               'bildplan': plan_cache, 'stuecke': {}}
    # Auch bei einem spaeteren Bildfehler Stimme und Regie wiederverwenden.
    rendercache.speichern(aus, zustand)
    bildablauf = {'videoformat': dramaturgie.videoformat(s), 'einstellungen': []}
    zeiten['stuecke_wiederverwendet'] = 0
    zeiten['stuecke_neu'] = 0

    # Je Abschnitt ein eigenes Stueck: Clip (zugeschnitten auf 9:16) mit
    # Schrift-Ebene darueber - oder Farbverlauf, wenn kein Clip passt.
    quellen, schon, liste, hg_clip = [], set(), [], None
    benutzte_fotos = set()
    benutzte_demos = set()
    # Beanstandetes Material beim erneuten Auswaehlen ausschliessen.
    if cache:
        for e in cache.get('stuecke', {}).values():
            schon.update(q['id'] for q in e.get('quellen', []) if q.get('quelle') == 'Pixabay' and 'id' in q)
            benutzte_fotos.update(e.get('fotos', []))
            benutzte_demos.update(q['datei'] for q in e.get('quellen', [])
                                if q.get('quelle') == 'Beispielbild' and q.get('datei'))
    kartenvideo = any(str(t.get('quelle_url', '')).startswith('http') for t in s['teile'])
    with messen('clips_und_stuecke'):
        ereignisse = [(0.0, 'impact')] if H > B else []
        musikpausen = []  # Wendepunkte: Musik setzt kurz davor aus (Stille als Musterbruch)
        geraeusche = []  # (sekunde, mp3) passend zur Szene, hoechstens 3
        bild_ersatz = 0  # Einstellungen mit gepruefter Nachbar-Illustration statt eigenem Bild
        vorherige_id = None  # Bild-Fingerabdruck der direkt vorherigen Einstellung
        kanal_slug = re.sub(r'[^a-z0-9]+', '-', s.get('kanal', '').lower()).strip('-')
        FORTSCHRITT['plaetze'] = sorted((t['platz'] for t in s['teile'] if t.get('platz')), reverse=True)
        FORTSCHRITT['aktuell'] = None
        for i, shot in enumerate(shots):
            t, dauer, t0 = shot['teil'], shot['dauer_s'], shot['s']
            phasenstart = i == 0 or shots[i - 1]['phase'] != shot['phase']
            FORTSCHRITT['aktuell'] = t.get('platz') or FORTSCHRITT['aktuell']
            if phasenstart and (t.get('platz') == 1 or (i > 0 and t.get('beat') == 'wendung')):
                ereignisse += [(t0, 'riser'), (t0, 'impact')]
                musikpausen.append(t0)
            if phasenstart and i > 0 and str(t.get('geraeusch') or '').strip() and len(geraeusche) < 3:
                pfad, nennung = geraeusch_holen(t['geraeusch'])
                if pfad:
                    geraeusche.append((t0 + 0.15, pfad))
                    quellen.append({'quelle': 'Geraeusch', 'seite': 'Freesound via Openverse (CC0)',
                                    'nennung': nennung})
            key = rendercache.stueck_key(visuell, i, dauer, code_key)
            alt = cache.get('stuecke', {}).get(str(i), {})
            if alt.get('key') == key and rendercache.dateien_ok(aus, alt.get('dateien', [])):
                liste += [f"file '{n}'" for n in alt['dateien']]
                quellen += alt.get('quellen', [])
                ereignisse += [(t0 + sek, art) for sek, art in alt.get('ereignisse', [])]
                zustand['stuecke'][str(i)] = alt
                bildablauf['einstellungen'].append(dict(shot, teil=None,
                    material_id=alt.get('material_id'), material_art=alt.get('material_art')))
                zeiten['stuecke_wiederverwendet'] += 1
                vorherige_id = alt.get('material_id')
                rendercache.speichern(aus, zustand)
                continue
            zeiten['stuecke_neu'] += 1
            l0, q0, e0 = len(liste), len(quellen), len(ereignisse)
            fotos0 = set(benutzte_fotos)
            def merken():
                zustand['stuecke'][str(i)] = {'key': key,
                    'dateien': [z[6:-1] for z in liste[l0:]], 'quellen': quellen[q0:],
                    'ereignisse': [(sek - t0, art) for sek, art in ereignisse[e0:]],
                    'fotos': sorted(benutzte_fotos - fotos0),
                    'material_id': material_hash, 'material_art': material_art}
                bildablauf['einstellungen'].append(dict(shot, teil=None,
                    material_id=material_hash, material_art=material_art))
                (aus / 'bildablauf.json').write_text(json.dumps(bildablauf, indent=2), encoding='utf-8')
                rendercache.speichern(aus, zustand)
            stueck = aus / f'stueck_{i:02d}.mp4'
            ebene = aus / f'ebene_{i:02d}.png'
            modus = t.get('bildmodus', 'auto')
            karte = karte_fuer(t.get('quelle_url')) if modus in ('auto', 'karte') else None
            foto, fq = ((None, None) if karte or modus in ('stock', 'illustration', 'demo', 'figur', 'grafik', 'asset')
                        else foto_fuer(s.get('bilder') or [], t['text'] + ' Visual: ' + t.get('szene', ''), benutzte_fotos))
            if modus == 'demo':
                demo, fq = demo_fuer(t.get('quelle_url'), t['text'] + ' Visual: ' + t.get('szene', ''),
                                    benutzte_demos, t.get('demo_url'))
                if demo:
                    foto = demo
                    benutzte_demos.add(fq['datei'])
                else:
                    # GEMESSEN 08.10.2026 (Lauf 37774195592): Kritik verlangte echte Software-
                    # Aufnahmen, die Korrektur plante 'demo' - das Repo hatte keine Beispielbilder,
                    # der Bau brach ab. Dann die echte Quellseite als Karte zeigen (authentisch).
                    karte = karte_fuer(t.get('quelle_url'))
                    if not karte:
                        raise ValueError(f'Phase {shot["phase"]}: kein echtes Tool-Beispiel fuer {t.get("quelle_url")}')
                    print(f'Einstellung {i}: kein Tool-Beispielbild - echte Quellseite als Karte')
            # GEMELDET: „wirkt langweilig und eiskalt" - Illustrationen im Spiel-Plakat-Stil
            # (fabrik/illustration.py): die Kanalfigur im Einstieg und am Schluss; sonst eine
            # Szene nur dort, wo kein echtes Foto passt - echte Fotos bleiben fuer Fakten.
            # Spart nebenbei die Pixabay-Suche samt KI-Clipwahl.
            ill = None
            letzt = i == len(shots) - 1 and not t.get('platz')
            if modus == 'asset':
                import bibliothek
                ill = bibliothek.bild(t.get('asset'), s.get('kanal'))
                quellen.append({'quelle': 'Illustration', 'seite': 'Eigene sichtgepruefte KI-Illustration (built-in image_gen)',
                                'asset': t['asset'], 'sha256': bildplan.material_id(ill)})
            if modus == 'grafik':
                if s.get('thema') != 'Nintendo: The Problem with Durable Cards':
                    raise ValueError('Diese Vergleichsgrafik passt ausschliesslich zur belegten Karten-Geschichte')
                import infografik
                ill = infografik.karten(aus / f'ill_{i:02d}.jpg', t.get('grafik_variante', 0), B, H)
                quellen.append({'quelle': 'Illustration', 'seite': 'Eigene redaktionelle Vergleichsgrafik, keine historische Aufnahme'})
            if modus == 'figur':
                import illustration
                ill = illustration.FIGUREN / f'{kanal_slug}.jpg'
                if not ill.is_file():
                    raise ValueError('Keine vorhandene originale Kanalfigur')
                quellen.append({'quelle': 'Illustration', 'seite': 'Originale Kanalfigur: vorhandenes Referenzbild'})
            if os.environ.get('CLOUDFLARE_AI_TOKEN') and modus in ('auto', 'illustration', 'foto') \
                    and not karte and not foto:
                import illustration
                if i == 0 or letzt:
                    szene = t.get('szene') or ('pointing straight at the viewer with a confident grin, close-up, '
                                               'city street at sunset' if i == 0 else 'giving a confident nod to '
                                               'the viewer, half body, rooftop at golden hour')
                else:  # aeltere Skripte ohne Feld szene: Bildsuche + Satz als Szene
                    szene = t.get('szene') or f"{t.get('suche', '')}, {t['text'][:120]}"
                if modus == 'foto':
                    szene = ('A clearly illustrative reconstruction of a generic period-appropriate '
                             'setting or object, not an actual archive photograph and not a likeness '
                             'of a named historical person. ' + szene)
                ill = illustration_mit_ausweg(szene, aus / f'ill_{i:02d}.jpg', kanal_slug,
                                              t.get('figur', i == 0 or letzt), i == 0 or letzt,
                                              dramaturgie.videoformat(s))
                if ill:
                    karte, foto = None, None
                    quellen.append({'quelle': 'Illustration', 'seite': 'KI-generiert (Cloudflare Workers AI, FLUX)'})
            # GEMESSEN: Im Kartenvideo holte der Schluss einen fremden Clip
            # (halber „Subscribe"-Knopf) - dort gilt jetzt derselbe Hintergrund.
            clip, quelle = ((None, None) if karte or foto or ill or (kartenvideo and modus == 'auto') else
                            clip_fuer(t.get('suche') or s.get('suche'), schon, dauer,
                                      t['text'] + ' Visual: ' + t.get('szene', '')))
            material = ill or foto or karte or clip
            if not material and bild_ersatz < 2:
                # GEMESSEN 08.10.2026 (Lauf 37753715598): eine einzige Einstellung ohne
                # bestandenes Bild kippte das ganze Video (3x). Hoechstens zweimal ein schon
                # GEPRUEFTES Bild des naechsten Abschnitts - kein beliebiger Hintergrund wie
                # beim abgelehnten Nintendo-Short (27 s Kerzen).
                # GEMESSEN 08.10.2026 (Lauf 37760482364, Business): Einstellung 15 UND 16
                # bekamen beide ill_13 -> 'Gleiches Motiv zu lange gehalten', Video gesperrt.
                # Nie das Bild der direkt vorherigen Einstellung wiederholen.
                ersatz = nachbar_bild(aus, i, vorherige_id)
                if ersatz:
                    ill = material = ersatz
                    bild_ersatz += 1
                    print(f'Einstellung {i}: kein Bild bestanden - gepruefte Nachbar-Illustration {ill.name}')
            if not material:
                raise ValueError(f'Phase {shot["phase"]}, Einstellung {i}: kein passendes Hauptbild; kein Hintergrundersatz')
            material_hash = bildplan.material_id(material)
            vorherige_id = material_hash
            material_art = 'illustration' if ill else 'foto' if foto else 'karte' if karte else 'clip'
            bild_fuer(t, s['titel'], i, len(shots), durchsichtig=not karte,
                     karte=karte, akzent=akzent_farbe(s)).save(ebene)
            if ill:
                with Image.open(ebene) as im:
                    im = im.convert('RGBA')
                schrift_text(im, (LAYOUT['links'], H * .12), 'ILLUSTRATION', schrift(28), (210, 210, 210))
                im.save(ebene)
            elif modus == 'demo':
                with Image.open(ebene) as im:
                    im = im.convert('RGBA')
                schrift_text(im, (LAYOUT['links'], H * .12), 'MODEL CARD EXAMPLE', schrift(28), (210, 210, 210))
                im.save(ebene)
            if ill and B > H:
                kpfad = aus / f'karte_{i:02d}.png'
                karten_ebene(ill, kasten=True).save(kpfad)
                hg_clip = hg_clip or hintergrund_holen(s, schon, dauer, quellen, aus)
                ein, filt = karten_filter(hg_clip, ebene, kpfad)
            elif ill:
                n = max(1, int(dauer * FPS))
                filt = (f'[0:v]scale={B}:{H}:force_original_aspect_ratio=increase,crop={B}:{H},setsar=1,'
                        f"fps={FPS},zoompan=z='" + ZOOM.format(n=n) + f"':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                        f':d=1:s={B}x{H}:fps={FPS}[v];[v][1:v]overlay=0:0,format=yuv420p')
                ein = ['-loop', '1', '-framerate', str(FPS), '-i', str(ill), '-i', str(ebene)]
            elif foto:
                quellen.append(fq)
                kpfad = aus / f'karte_{i:02d}.png'
                karten_ebene(foto, kasten=True).save(kpfad)
                ein, filt = karten_filter(foto, ebene, kpfad)
            elif karte:
                kpfad = None
                if karte:
                    quellen.append({'quelle': 'Vorschaubild', 'seite': t['quelle_url']})
                    kpfad = aus / f'karte_{i:02d}.png'
                    karten_ebene(karte).save(kpfad)
                ein, filt = karten_filter(karte, ebene, kpfad)
            elif clip:
                quellen.append(quelle)
                filt = (f'[0:v]scale={B}:{H}:force_original_aspect_ratio=increase,crop={B}:{H},setsar=1,'
                        f'fps={FPS}[v];[v][1:v]overlay=0:0,format=yuv420p')
                ein = ['-stream_loop', '-1', '-i', str(clip), '-i', str(ebene)]
            else:
                # GEMELDET (KI-Analyse): „Blackscreens", „dunkler leerer
                # Hintergrund mit Text" - passte kein Clip, blieb eine leere
                # Flaeche. Jetzt der bewegte Kanal-Hintergrund.
                raise ValueError('Kein geeignetes Bildmaterial')
            # GEMELDET (KI-Analyse): „Ablauf ueber 1,5 Minuten exakt gleich",
            # „Praxisbeispiele wuerden es lebendiger machen". Je Platz zwei
            # Stuecke: erst die Karte (2,8 s, Einflug), dann ein Clip, der zeigt,
            # WAS das Werkzeug macht (KI waehlt nach Vorschau) - Karte klein oben.
            if karte and t.get('platz') and dauer > 5.5:
                a = 2.8
                # Erst ein echtes Beispiel von der Modellseite, nur sonst Pixabay
                demo, q_d = demo_fuer(t.get('quelle_url'), t['text'])
                # Echte Bildschirmaufnahme der Modellseite (siehe aufnahme_fuer)
                aufn = aufnahme_fuer(t.get('quelle_url'), dauer - a, aus / f'aufnahme_{i:02d}.mp4')
                if demo or aufn:
                    if demo:
                        quellen.append(q_d)
                    if aufn:
                        quellen.append({'quelle': 'Bildschirmaufnahme', 'seite': t['quelle_url']})
                    st_a, st_b = aus / f'stueck_{i:02d}a.mp4', aus / f'stueck_{i:02d}b.mp4'
                    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *ein, '-filter_complex', filt,
                                    '-t', f'{a:.3f}', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                                    str(st_a)], check=True)
                    eb, mk = aus / f'ebene_{i:02d}b.png', aus / f'mini_{i:02d}.png'
                    bild_fuer({}, s['titel'], i, len(s['teile']), durchsichtig=True,
                             akzent=akzent_farbe(s)).save(eb)
                    mini_karte(karte, t['platz']).save(mk)
                    rest = dauer - a
                    ereignisse += [(t0, 'pop'), (t0 + a, 'whoosh')]
                    # Beides da und genug Zeit: erst die Aufnahme, dann das Beispiel -
                    # ein Schnitt mehr (Vorbild: Wechsel alle ~4 s).
                    if demo and aufn and rest >= 5:
                        st_c = aus / f'stueck_{i:02d}c.mp4'
                        demo_stueck(aufn, eb, mk, rest / 2, st_b)
                        demo_stueck(demo, eb, mk, rest - rest / 2, st_c)
                        liste += [f"file '{st_a.name}'", f"file '{st_b.name}'", f"file '{st_c.name}'"]
                        ereignisse.append((t0 + a + rest / 2, 'whoosh'))
                    else:
                        demo_stueck(aufn or demo, eb, mk, rest, st_b)
                        liste += [f"file '{st_a.name}'", f"file '{st_b.name}'"]
                    merken()
                    continue
                clip_b, q_b = clip_fuer(t.get('suche') or s.get('suche'), schon, dauer - a, t['text'])
                if clip_b:
                    quellen.append(q_b)
                    st_a, st_b = aus / f'stueck_{i:02d}a.mp4', aus / f'stueck_{i:02d}b.mp4'
                    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *ein, '-filter_complex', filt,
                                    '-t', f'{a:.3f}', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                                    str(st_a)], check=True)
                    eb, mk = aus / f'ebene_{i:02d}b.png', aus / f'mini_{i:02d}.png'
                    bild_fuer({}, s['titel'], i, len(s['teile']), durchsichtig=True,
                             akzent=akzent_farbe(s)).save(eb)
                    mini_karte(karte, t['platz']).save(mk)
                    fb = (f'[0:v]scale={B}:{H}:force_original_aspect_ratio=increase,crop={B}:{H},setsar=1,'
                          f'fps={FPS}[v];[v][1:v]overlay=0:0[x];[x][2:v]overlay=0:0,format=yuv420p')
                    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-stream_loop', '-1', '-i', str(clip_b),
                                    '-loop', '1', '-framerate', str(FPS), '-i', str(eb),
                                    '-loop', '1', '-framerate', str(FPS), '-i', str(mk), '-filter_complex', fb,
                                    '-t', f'{dauer - a:.3f}', '-an', '-c:v', 'libx264', '-preset', 'veryfast',
                                    '-crf', '18', str(st_b)], check=True)
                    liste += [f"file '{st_a.name}'", f"file '{st_b.name}'"]
                    ereignisse += [(t0, 'pop'), (t0 + a, 'whoosh')]
                    merken()
                    continue
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *ein, '-filter_complex', filt,
                            '-t', f'{dauer:.3f}', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                            str(stueck)], check=True)
            liste.append(f"file '{stueck.name}'")
            if i and phasenstart and (H > B or t.get('name') or t.get('beat') == 'wendung'):
                ereignisse.append((t0, 'whoosh'))
            merken()
        (aus / 'stuecke.txt').write_text('\n'.join(liste) + '\n', encoding='utf-8')
    bildpruefung = bildplan.pruefen(bildablauf, sum(laengen), dramaturgie.videoformat(s))
    (aus / 'bildablauf.json').write_text(json.dumps(bildablauf, indent=2), encoding='utf-8')
    if bildpruefung['befunde']:
        raise ValueError('Bildablauf gesperrt: ' + '; '.join(bildpruefung['befunde']))
    zeiten['bildpruefung'] = bildpruefung
    # Quellen je Video festhalten (Rechte-Regeln, Konzept 2c) - und fuer
    # die Beschreibung („Clips: Pixabay", Bitte von Pixabay).
    musik_key = rendercache.signatur([s.get('musik_suche'), s.get('musik', True)])
    if cache.get('musik_key') == musik_key and 'musik' in cache \
            and (not cache['musik'] or Path(cache['musik']).is_file()):
        musik, musik_q = cache['musik'], cache.get('musik_quelle')
    else:
        musik, musik_q = musik_holen(s.get('musik_suche') or ['calm ambient background']) \
            if s.get('musik', True) else (None, None)
    if not musik and s.get('musik', True):
        musik = audioqualitaet.musikbett(aus / 'musikbett.wav', technisch=s.get('kanal') == 'AI Tools Explained')
        musik_q = {'quelle': 'Musik', 'seite': 'Contentfabrik: eigene synthetische Instrumentalmusik',
                   'nennung': 'Music: original instrumental generated by Contentfabrik (no third-party samples)'}
    zustand.update(musik_key=musik_key, musik=str(Path(musik).resolve()) if musik else None, musik_quelle=musik_q)
    if musik_q:
        quellen.append(musik_q)
    (aus / 'quellen.json').write_text(json.dumps(quellen, indent=2, ensure_ascii=False), encoding='utf-8')
    ereignisse = audioqualitaet.ereignisse(ereignisse, sum(laengen))
    effekte_spur(ereignisse, sum(laengen), rate, aus / 'effekte.wav',
                 glitch=bool(FORTSCHRITT['plaetze']) and 'AI' in s.get('kanal', ''), geraeusche=geraeusche)
    zeiten['effekte'] = len(ereignisse)
    # Effekte nicht in die Sidechain: nur die Stimme senkt die Musik ab
    fx = 3 if musik else 2
    musik_pegel = max(0, min(0.15, float(s.get('musik_pegel', 0.1))))
    effekt_pegel = max(0, min(1.0, float(s.get('effekt_pegel', 1.0))))

    with messen('rendern'):
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'stuecke.txt',
            '-i', 'stimme.wav',
            *(['-stream_loop', '-1', '-i', str(Path(musik).resolve())] if musik else []),
            '-i', 'effekte.wav',
            # Einheitlicher Look ueber Clips verschiedener Herkunft: etwas mehr
            # Kontrast/Saettigung, leicht dunklere Raender - VOR den Untertiteln.
            '-vf', f"fps={FPS},eq=contrast=1.06:saturation=1.12,vignette=PI/5,format=yuv420p,"
                   f"ass=untertitel.ass:fontsdir='{SCHRIFTEN.as_posix()}'",
            # Musik: Grundpegel -20 dB, unter der Stimme automatisch weitere ~10 dB
            # leiser (Sidechain) - die Stimme bleibt immer klar verstaendlich.
            '-filter_complex',
            ((f'[2:a]{musik_kette(musik_pegel, sum(laengen), musikpausen)}[m];'
              '[1:a]aresample=48000,asplit=2[v][sc];'
              '[m][sc]sidechaincompress=threshold=0.015:ratio=6:attack=15:release=350[md];'
              f'[{fx}:a]aresample=48000,volume={effekt_pegel}[fx];'
              '[v][md][fx]amix=inputs=3:duration=first:normalize=0,') if musik else
             (f'[1:a]aresample=48000[v];[{fx}:a]aresample=48000,volume={effekt_pegel}[fx];'
              '[v][fx]amix=inputs=2:duration=first:normalize=0,'))
            + 'loudnorm=I=-14:TP=-1.5:LRA=11[a]',  # Plattformnorm (Konzept 4a, Punkt 6)
            '-map', '0:v', '-map', '[a]',
            # 48 kHz Stereo: loudnorm rechnet intern hoch, und das Ergebnis
            # (96 kHz Mono) spielten Handy-Player nicht ab - gemeldet: „keine
            # Stimme hörbar", obwohl die Tonspur laut genug war (−15 dB).
            '-ar', '48000', '-ac', '2',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-c:a', 'aac', '-b:a', '160k',
            '-shortest', '-movflags', '+faststart', 'short.mp4'], cwd=aus, check=True)

    zeiten['gesamt'] = round(time.time() - beginn, 1)
    zeiten['videolaenge_s'] = round(sum(laengen), 1)
    zeiten['abschnitte_s'] = [round(x, 2) for x in laengen]  # Absprung je Abschnitt (erfolg.py)
    zeiten['woerter'] = len(woerter)
    rendercache.speichern(aus, zustand)
    (aus / 'messung.json').write_text(json.dumps(zeiten, indent=2), encoding='utf-8')
    print(json.dumps(zeiten, indent=2))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
