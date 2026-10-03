"""Video-Bauer, Probelauf 1: Skript (JSON) -> Stimme -> Untertitel -> Short.

Misst jede Stufe, damit klar wird, was ein Video an Rechenzeit kostet
(KONZEPT.md, Abschnitt 5a: Rechenminuten je Video = m).

Bausteine (alle kostenlos, gewerblich frei):
  Stimme      Kokoro-82M (Apache 2.0) ueber kokoro-onnx
  Zeitmarken  faster-whisper (MIT) - Wort fuer Wort
  Bild/Ton    Pillow + ffmpeg

Aufruf:  python fabrik/bauen.py skripte/probe.json ausgabe/
"""
import json, os, re, sys, time, subprocess, wave, colorsys
from PIL import ImageFilter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

B, H, FPS = 1080, 1920, 30
# Montserrat (SIL OFL, gewerblich frei) liegt im Projekt - GEMELDET: DejaVu
# wirkte „sehr unprofessionell".
SCHRIFTEN = Path(__file__).resolve().parent.parent / 'schriften'
SCHRIFT = str(SCHRIFTEN / 'Montserrat-ExtraBold.ttf')
TITEL_SCHRIFT = str(SCHRIFTEN / 'Montserrat-Black.ttf')
zeiten = {}


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
    """Titel: genau zwei Zeilen, Schluesselwoerter farbig (Konzept 2b); die
    Groesse passt sich an (Probelauf 1: Zeile 2 war breiter als das Bild)."""
    d = ImageDraw.Draw(img)
    y = 190
    for zeile in titel:
        teile = [(w, w.strip('*') != w) for w in zeile.split(' ')]
        groesse = 78
        while True:
            f = schrift(groesse, TITEL_SCHRIFT)
            breite = sum(d.textlength(w.strip('*') + ' ', font=f) for w, _ in teile)
            if breite <= B - 120 or groesse <= 40:
                break
            groesse -= 4
        x = (B - breite) / 2
        for w, betont in teile:
            wort = w.strip('*') + ' '
            schrift_text(img, (x, y), wort, f, akzent if betont else (255, 255, 255))
            x += d.textlength(wort, font=f)
        y += groesse + 22


KARTE_Y = 700


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
    gesperrt = set(json.loads(MUSIK_SPERRE.read_text(encoding='utf-8'))) if MUSIK_SPERRE.exists() else set()
    for suche in random.sample(suchen, len(suchen)):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(
                'https://api.openverse.org/v1/audio/?' + urllib.parse.urlencode(
                    {'q': suche, 'license_type': 'commercial', 'page_size': 20}), headers=WIKI_KENNUNG), timeout=30))
        except Exception as e:
            print('Openverse nicht erreichbar:', str(e)[:120])
            continue
        treffer = [r for r in d.get('results', [])
                   if r.get('license') in ('cc0', 'by') and r.get('url') and r['id'] not in gesperrt
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


def foto_fuer(bilder, satz, benutzt):
    """KI waehlt aus den freien Wikipedia-Fotos das zum Satz passende (oder
    keins). Jedes Foto hoechstens einmal je Video."""
    import urllib.request, hashlib
    frei = [b for b in bilder if b['titel'] not in benutzt]
    if not frei or not os.environ.get('GEMINI_API_KEY'):
        return None, None
    try:
        from skript import gemini
        # GEMESSEN (Nintendo-Lauf): Nur die ersten 8 von 32 Fotos wurden
        # gezeigt - alphabetisch Buerogebaeude und Game Boys; „Nintendo 1889"
        # und „NintendoCards" kamen nie dran -> Stock-Clips (Autobahn, Naeherei).
        # Jetzt: Vorauswahl ueber alle Titel/Beschreibungen, dann Vorschau.
        liste = '\n'.join(f"{n}: {b['titel'][5:]} - {b['beschreibung'][:120]}" for n, b in enumerate(frei))
        vor, _ = gemini(f'A narrator says:\n"{satz}"\nWhich of these Wikimedia photos could show exactly that '
                        f'(person, place, product, era)? Give up to 4 numbers, best first; empty list if none.\n{liste}',
                        {'type': 'OBJECT', 'properties': {'nummern': {'type': 'ARRAY', 'items': {'type': 'INTEGER'}}},
                         'required': ['nummern']}, temperatur=0.1,
                        modelle=['gemini-flash-lite-latest', 'gemini-flash-latest'])
        frei = [frei[n] for n in vor['nummern'] if 0 <= n < len(frei)][:4]
        if not frei:
            return None, None
        vorschau = [urllib.request.urlopen(urllib.request.Request(b['klein'], headers=WIKI_KENNUNG),
                                           timeout=20).read() for b in frei]
        wahl, _ = gemini(
            f'These are {len(vorschau)} photos (0 to {len(vorschau) - 1}) from the Wikipedia article. A narrator '
            f'says:\n"{satz}"\nPick the photo that clearly shows what is said (person, place, product, era). '
            'Reject flags, maps, logos-only, charts and unrelated photos. If none fits clearly, answer -1.'
            + regel_text(),
            {'type': 'OBJECT', 'properties': {'nummer': {'type': 'INTEGER'}}, 'required': ['nummer']},
            temperatur=0.1, bilder=vorschau, modelle=['gemini-flash-lite-latest', 'gemini-flash-latest'])
        n = wahl['nummer']
        if not 0 <= n < len(frei):
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
    breite = 560
    k = k.resize((breite, int(k.height * breite / k.width)), Image.LANCZOS)
    img = Image.new('RGBA', (B, H), (0, 0, 0, 0))
    x, y = (B - breite) // 2, 520
    schatten = Image.new('RGBA', (B, H), (0, 0, 0, 0))
    ImageDraw.Draw(schatten).rounded_rectangle((x, y + 10, x + breite, y + 10 + k.height), 20, fill=(0, 0, 0, 190))
    img.alpha_composite(schatten.filter(ImageFilter.GaussianBlur(14)))
    maske = Image.new('L', k.size, 0)
    ImageDraw.Draw(maske).rounded_rectangle((0, 0, *k.size), 20, fill=255)
    img.paste(k, (x, y), maske)
    if platz:
        f = schrift(110, TITEL_SCHRIFT)
        t = f'#{platz}'
        schrift_text(img, ((B - ImageDraw.Draw(img).textlength(t, font=f)) / 2, 395), t, f, rand=4)
    return img


def karten_ebene(karte, kasten=None):
    """Die Karte allein (abgerundet, mit Schatten) auf durchsichtigem Bild."""
    k = Image.open(karte).convert('RGB')
    breite = B - 80
    if kasten:  # Foto: in den Kasten zwischen Titel und Untertiteln einpassen
        f = min(kasten[0] / k.width, kasten[1] / k.height)
        k = k.resize((int(k.width * f), int(k.height * f)), Image.LANCZOS)
    else:
        k = k.resize((breite, int(k.height * breite / k.width)), Image.LANCZOS)
    x = (B - k.width) // 2
    y = KARTE_Y if not kasten else 430 + (kasten[1] - k.height) // 2
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
    hg_ein = (['-loop', '1', '-framerate', str(FPS), '-i', str(hg)] if Path(hg).suffix == '.png'
              else ['-stream_loop', '-1', '-i', str(hg)])
    filt = (f'[0:v]scale={B}:{H}:force_original_aspect_ratio=increase,crop={B}:{H},setsar=1,fps={FPS},'
            f'eq=brightness=-0.22:saturation=0.8,gblur=sigma=4[bg];'
            f'[2:v]format=rgba,fade=in:st=0:d=0.35:alpha=1[k];'
            f"[bg][k]overlay=x=0:y='140*max(0,1-t/0.35)':eval=frame[b1];"
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
    verlauf_bild((32, 210, 190)).save(pfad)
    return pfad


def verlauf_bild(akzent):
    """Rueckfall-Hintergrund: dunkel in der Kanalfarbe. GEMESSEN: weisse
    GitHub-Karten unscharf als Hintergrund ergaben ein mattes Grau."""
    v = np.linspace(0, 1, H)[:, None, None]
    oben, unten = np.array(akzent) * 0.28, np.array((4, 6, 14))
    return Image.fromarray(np.repeat((oben * (1 - v) + unten * v).astype(np.uint8), B, axis=1))


def bild_fuer(teil, titel, nr, gesamt, durchsichtig=False, karte=None, akzent=(32, 210, 190)):
    """Ebene je Abschnitt: Titel, Platz, Name.
    durchsichtig=True: nur Schrift + sanfte Abdunklung, als Ebene ueber einem
    Videoclip. karte: Vorschaubild der Quelle, gross in der Mitte."""
    if karte:
        # Nur Schrift - Hintergrund (bewegter Clip) und Karte (fliegt ein)
        # setzt ffmpeg darunter bzw. dazu. GEMELDET: „wirkt wie eine Diashow".
        img = Image.new('RGBA', (B, H), (0, 0, 0, 0))
        with Image.open(karte) as k:
            hoehe = int(k.height * (B - 80) / k.width)
        # Name gross unter der Platznummer - auf Hugging-Face-Karten ist er winzig.
        # GEMESSEN: unter der Karte klebte er an den Untertiteln (gelb ueber weiss).
        if teil.get('name'):
            fn = schrift(58)
            nb = ImageDraw.Draw(img).textlength(teil['name'], font=fn)
            schrift_text(img, ((B - nb) / 2, 612), teil['name'], fn, (255, 214, 10))
    elif durchsichtig:
        img = Image.new('RGBA', (B, H), (0, 0, 0, 0))
        schatten = np.zeros((H, B, 4), dtype=np.uint8)
        a = np.zeros(H)
        a[:620] = np.linspace(150, 0, 620)            # oben dunkler fuer den Titel
        a[1200:] = np.linspace(0, 150, H - 1200)      # unten dunkler fuer Untertitel
        schatten[..., 3] = a[:, None].astype(np.uint8)
        img = Image.alpha_composite(img, Image.fromarray(schatten, 'RGBA'))
    else:
        img = hintergrund(nr)
    titel_zeichnen(img, titel, akzent)
    d = ImageDraw.Draw(img)
    if teil.get('platz'):
        f = schrift(150 if karte else 220, TITEL_SCHRIFT)
        t = f"#{teil['platz']}"
        schrift_text(img, ((B - d.textlength(t, font=f)) / 2, 440 if karte else 600), t, f, rand=4)
    if teil.get('name') and not karte:  # bei der Karte steht der Name schon drauf
        f = schrift(84)
        schrift_text(img, ((B - d.textlength(teil['name'], font=f)) / 2, 880), teil['name'], f, (255, 214, 10))
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
    passt. GEMELDET: Die Bilder passten nicht zum Text - die Pixabay-Suche
    allein liefert nach Beliebtheit, nicht nach Inhalt. Passt keins: [] (dann
    eigenes Bild statt falschem). Ohne KI: alte Reihenfolge."""
    import urllib.request
    if not kandidaten or not satz or not os.environ.get('GEMINI_API_KEY'):
        return kandidaten
    try:
        bilder = [urllib.request.urlopen(urllib.request.Request(
            (h['videos'].get('tiny') or h['videos']['small'])['thumbnail'], headers=KENNUNG), timeout=20).read()
                  for h in kandidaten]
        from skript import gemini
        wahl, _ = gemini(
            f'These are {len(bilder)} preview frames of stock videos, numbered 0 to {len(bilder) - 1} in order. '
            f'They will be the background while a narrator says:\n"{satz}"\n'
            'Pick the frame a viewer would find clearly fitting to this sentence. Reject abstract, unrelated, '
            'green-screen or text-heavy frames. If none fits clearly, answer -1.' + regel_text(),
            {'type': 'OBJECT', 'properties': {'nummer': {'type': 'INTEGER'}}, 'required': ['nummer']},
            # GEMESSEN: mit dem grossen Modell ~60 s je Abschnitt (384 s je Video)
            temperatur=0.1, bilder=bilder, modelle=['gemini-flash-lite-latest', 'gemini-flash-latest'])
        n = wahl['nummer']
        return [kandidaten[n]] if 0 <= n < len(kandidaten) else []
    except Exception as e:  # KI nicht erreichbar: lieber Clip als kein Video
        print('Clip-Auswahl ohne KI:', str(e)[:200])
        return kandidaten


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
                  and (h['videos'].get('medium') or h['videos'].get('small') or {}).get('url')][:6]
    for hit in waehle(kandidaten, satz):
        v = hit['videos'].get('medium') or hit['videos'].get('small')
        ziel = PIXABAY_CACHE / f"pixabay_{hit['id']}.mp4"
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


def untertitel(woerter, pfad):
    """Wort-fuer-Wort-Untertitel: drei Woerter sichtbar, das gesprochene gelb."""
    kopf = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, "
            "Bold, Outline, Shadow, Alignment, MarginV\n"
            # MarginV 520: unten liegen bei TikTok/Shorts Beschreibung und Knoepfe
            "Style: U,Montserrat,84,&H00FFFFFF,&H00000000,&H96000000,1,4,3,2,520\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Text\n")
    # GEMESSEN: Whisper trennt Zahlen („16" + „,000") - wieder zusammenfuegen.
    zusammen = []
    for w in woerter:
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
    zeig = lambda x: x.strip('.,!?;:"').upper()  # Satzzeichen stoeren im Einzelwort
    gruppen, g = [], []
    for w in woerter:
        laenge = sum(len(zeig(x['w'])) + 1 for x in g) + len(zeig(w['w']))
        if g and (laenge > 18 or len(g) == 3 or g[-1]['w'][-1:] in '.!?'):
            gruppen.append(g)
            g = []
        g.append(w)
    if g:
        gruppen.append(g)
    zeilen = []
    for gruppe in gruppen:
        for j, w in enumerate(gruppe):
            pop = '{\\fscx108\\fscy108\\t(0,110,\\fscx100\\fscy100)}' if j == 0 else ''
            text = pop + ' '.join(('{\\c&H0AD6FF&}' + zeig(x['w']) + '{\\c&HFFFFFF&}') if x is w else zeig(x['w'])
                                  for x in gruppe)
            i = woerter.index(w)
            ende = woerter[i + 1]['s'] if i + 1 < len(woerter) else w['e'] + 0.3
            zeilen.append(f"Dialogue: 0,{ass_zeit(w['s'])},{ass_zeit(ende)},U,{text}")
    Path(pfad).write_text(kopf + '\n'.join(zeilen) + '\n', encoding='utf-8')


def main(skript_pfad, aus):
    aus = Path(aus); aus.mkdir(parents=True, exist_ok=True)
    s = json.loads(Path(skript_pfad).read_text(encoding='utf-8'))
    REGELN[:] = s.get('regeln', [])
    beginn = time.time()

    with messen('stimme_laden'):
        from kokoro_onnx import Kokoro
        kokoro = Kokoro('modelle/kokoro-v1.0.onnx', 'modelle/voices-v1.0.bin')
    teile, rate, laengen = [], 24000, []
    tempo = s.get('tempo', 1.05)
    hoechst = (s.get('laenge_s') or [62, 90])[1]
    with messen('stimme'):
        # GEMESSEN 03.10.2026: Die Stimme bm_george spricht ~2,05 Woerter/s
        # (andere ~2,7) - 249 Woerter wurden 121 s statt hoechstens 90 s, die
        # Datei 56 MB und damit zu gross fuer Telegram. Ist der Ton zu lang,
        # wird EINMAL schneller gesprochen (hoechstens +20 %, sonst unnatuerlich).
        for runde in range(2):
            teile, laengen = [], []
            for t in s['teile']:
                audio, rate = kokoro.create(t['text'], voice=s.get('stimme', 'af_heart'), speed=tempo, lang='en-us')
                pause = np.zeros(int(rate * 0.25), dtype=np.float32)
                teile.append(np.concatenate([audio.astype(np.float32), pause]))
                laengen.append(len(teile[-1]) / rate)
            if runde or sum(laengen) <= hoechst + 5:
                break
            neu = round(min(tempo * 1.2, tempo * sum(laengen) / hoechst), 3)
            print(f'Ton {sum(laengen):.0f} s > {hoechst} s - Tempo {tempo} -> {neu}')
            tempo = neu
    zeiten['tempo'] = tempo
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
    woerter = angleichen(woerter, ' '.join(t['text'] for t in s['teile']))
    untertitel(woerter, aus / 'untertitel.ass')

    # Je Abschnitt ein eigenes Stueck: Clip (zugeschnitten auf 9:16) mit
    # Schrift-Ebene darueber - oder Farbverlauf, wenn kein Clip passt.
    quellen, schon, liste, hg_clip = [], set(), [], None
    benutzte_fotos = set()
    kartenvideo = any(str(t.get('quelle_url', '')).startswith('http') for t in s['teile'])
    with messen('clips_und_stuecke'):
        for i, t in enumerate(s['teile']):
            dauer = laengen[i]
            stueck = aus / f'stueck_{i:02d}.mp4'
            ebene = aus / f'ebene_{i:02d}.png'
            karte = karte_fuer(t.get('quelle_url'))
            foto, fq = (None, None) if karte else foto_fuer(s.get('bilder') or [], t['text'], benutzte_fotos)
            # GEMESSEN: Im Kartenvideo holte der Schluss einen fremden Clip
            # (halber „Subscribe"-Knopf) - dort gilt jetzt derselbe Hintergrund.
            clip, quelle = ((None, None) if karte or foto or kartenvideo else
                            clip_fuer(t.get('suche') or s.get('suche'), schon, dauer, t['text']))
            bild_fuer(t, s['titel'], i, len(s['teile']), durchsichtig=not karte,
                     karte=karte).save(ebene)
            if foto:
                quellen.append(fq)
                kpfad = aus / f'karte_{i:02d}.png'
                karten_ebene(foto, kasten=(B - 80, 860)).save(kpfad)
                hg_clip = hg_clip or hintergrund_holen(s, schon, dauer, quellen, aus)
                ein, filt = karten_filter(hg_clip, ebene, kpfad)
            elif karte or kartenvideo:
                kpfad = None
                if karte:
                    quellen.append({'quelle': 'Vorschaubild', 'seite': t['quelle_url']})
                    kpfad = aus / f'karte_{i:02d}.png'
                    karten_ebene(karte).save(kpfad)
                hg_clip = hg_clip or hintergrund_holen(s, schon, dauer, quellen, aus)
                ein, filt = karten_filter(hg_clip, ebene, kpfad)
            elif clip:
                quellen.append(quelle)
                # Langsamer Zoom (6 %) auf JEDEM Clip. GEMELDET (KI-Analyse):
                # „Standbild von Schulkindern ohne jede Kamerabewegung".
                n = max(1, int(dauer * FPS))
                filt = (f'[0:v]scale={B}:{H}:force_original_aspect_ratio=increase,crop={B}:{H},setsar=1,'
                        f"fps={FPS},zoompan=z='1+0.06*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                        f':d=1:s={B}x{H}:fps={FPS}[v];[v][1:v]overlay=0:0,format=yuv420p')
                ein = ['-stream_loop', '-1', '-i', str(clip), '-i', str(ebene)]
            else:
                # GEMELDET (KI-Analyse): „Blackscreens", „dunkler leerer
                # Hintergrund mit Text" - passte kein Clip, blieb eine leere
                # Flaeche. Jetzt der bewegte Kanal-Hintergrund.
                hg_clip = hg_clip or hintergrund_holen(s, schon, dauer, quellen, aus)
                ein, filt = karten_filter(hg_clip, ebene, None)
            # GEMELDET (KI-Analyse): „Ablauf ueber 1,5 Minuten exakt gleich",
            # „Praxisbeispiele wuerden es lebendiger machen". Je Platz zwei
            # Stuecke: erst die Karte (2,8 s, Einflug), dann ein Clip, der zeigt,
            # WAS das Werkzeug macht (KI waehlt nach Vorschau) - Karte klein oben.
            if karte and t.get('platz') and dauer > 5.5:
                a = 2.8
                clip_b, q_b = clip_fuer(t.get('suche') or s.get('suche'), schon, dauer - a, t['text'])
                if clip_b:
                    quellen.append(q_b)
                    st_a, st_b = aus / f'stueck_{i:02d}a.mp4', aus / f'stueck_{i:02d}b.mp4'
                    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *ein, '-filter_complex', filt,
                                    '-t', f'{a:.3f}', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                                    str(st_a)], check=True)
                    eb, mk = aus / f'ebene_{i:02d}b.png', aus / f'mini_{i:02d}.png'
                    bild_fuer({}, s['titel'], i, len(s['teile']), durchsichtig=True).save(eb)
                    mini_karte(karte, t['platz']).save(mk)
                    nb = max(1, int((dauer - a) * FPS))
                    fb = (f'[0:v]scale={B}:{H}:force_original_aspect_ratio=increase,crop={B}:{H},setsar=1,'
                          f"fps={FPS},zoompan=z='1+0.06*on/{nb}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                          f':d=1:s={B}x{H}:fps={FPS}[v];[v][1:v]overlay=0:0[x];[x][2:v]overlay=0:0,format=yuv420p')
                    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-stream_loop', '-1', '-i', str(clip_b),
                                    '-loop', '1', '-framerate', str(FPS), '-i', str(eb),
                                    '-loop', '1', '-framerate', str(FPS), '-i', str(mk), '-filter_complex', fb,
                                    '-t', f'{dauer - a:.3f}', '-an', '-c:v', 'libx264', '-preset', 'veryfast',
                                    '-crf', '18', str(st_b)], check=True)
                    liste += [f"file '{st_a.name}'", f"file '{st_b.name}'"]
                    continue
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *ein, '-filter_complex', filt,
                            '-t', f'{dauer:.3f}', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                            str(stueck)], check=True)
            liste.append(f"file '{stueck.name}'")
        (aus / 'stuecke.txt').write_text('\n'.join(liste) + '\n', encoding='utf-8')
    # Quellen je Video festhalten (Rechte-Regeln, Konzept 2c) - und fuer
    # die Beschreibung („Clips: Pixabay", Bitte von Pixabay).
    musik, musik_q = musik_holen(s.get('musik_suche') or ['calm ambient background']) \
        if s.get('musik', True) else (None, None)
    if musik_q:
        quellen.append(musik_q)
    (aus / 'quellen.json').write_text(json.dumps(quellen, indent=2, ensure_ascii=False), encoding='utf-8')

    with messen('rendern'):
        subprocess.run([
            'ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'stuecke.txt',
            '-i', 'stimme.wav',
            *(['-stream_loop', '-1', '-i', str(Path(musik).resolve())] if musik else []),
            # Einheitlicher Look ueber Clips verschiedener Herkunft: etwas mehr
            # Kontrast/Saettigung, leicht dunklere Raender - VOR den Untertiteln.
            '-vf', f"fps={FPS},eq=contrast=1.06:saturation=1.12,vignette=PI/5,format=yuv420p,"
                   f"ass=untertitel.ass:fontsdir='{SCHRIFTEN.as_posix()}'",
            # Musik: Grundpegel -20 dB, unter der Stimme automatisch weitere ~10 dB
            # leiser (Sidechain) - die Stimme bleibt immer klar verstaendlich.
            *(['-filter_complex',
               '[2:a]aresample=48000,volume=0.1,afade=t=in:d=1[m];'
               '[1:a]aresample=48000,asplit=2[v][sc];'
               '[m][sc]sidechaincompress=threshold=0.015:ratio=6:attack=15:release=350[md];'
               '[v][md]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]',
               '-map', '0:v', '-map', '[a]'] if musik else
              ['-af', 'loudnorm=I=-14:TP=-1.5:LRA=11']),  # Plattformnorm (Konzept 4a, Punkt 6)
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
    (aus / 'messung.json').write_text(json.dumps(zeiten, indent=2), encoding='utf-8')
    print(json.dumps(zeiten, indent=2))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
