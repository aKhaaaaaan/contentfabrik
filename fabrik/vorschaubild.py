"""Vorschaubild (Thumbnail) fuer Langvideos - 1280x720, unter 2 MB.

Nutzerauftrag 09.10.2026 nach der Analyse von „Claude Code + YouTube = 10.000 EUR/Monat":
lange Videos leben vom Vorschaubild; die Pipeline baute keins.

GEMELDET 09.10.2026 zum ersten Entwurf (Figur gross, zwei Titelzeilen): „Die Firma, das Logo und
die Fabrik muessen groesser sein als der Typ. Der Typ soll nicht im Vordergrund stehen, sondern immer
das Logo, ueber das man die Geschichte oder das KI-Tool erzaehlt - damit die Zuschauer direkt wissen,
worum es geht. Die Menschen lieben Bilder und wollen weniger lesen."
Aufbau darum:
  1. Hintergrund: gemalte Schluesselszene der Firma/des Werkzeugs (Fabrik, Zentrale, Produkt) OHNE
     Kanalfigur, ohne Schrift (gepruefte FLUX-Illustration wie im Video).
  2. Groesstes Element: das ECHTE Logo (Wikidata P154 -> Wikimedia Commons; bei Werkzeugen zuerst das
     Logo aus der README). Ohne Logo: der Name als grosse Wortmarke.
  3. Hoechstens drei Woerter Text (das *hervorgehobene* Titelwort, sonst die ersten Woerter).
Logos dienen nur der Kennzeichnung, worueber das Video berichtet (redaktionelle Nennung).

Aufruf:  python fabrik/vorschaubild.py ausgabe/skript.json ausgabe/thumbnail.jpg
"""
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
B, H = 1280, 720
GRENZE = 2 * 1024 * 1024  # YouTube: Vorschaubilder hoechstens 2 MB
SCHRIFT = Path(__file__).resolve().parent.parent / 'schriften' / 'Anton-Regular.ttf'
GOLD, WEISS = (255, 200, 61), (255, 255, 255)
KENNUNG = {'User-Agent': 'contentfabrik/1.0 (https://github.com/aKhaaaaaan/contentfabrik)'}
MAX_WOERTER = 3


def name(skript):
    """Firma/Werkzeug, ueber das das Video erzaehlt: Feld 'firma', sonst Thema bis ':' oder ','."""
    if skript.get('firma'):
        return str(skript['firma']).strip()
    return re.split(r'[:,(–—]| - ', str(skript.get('thema', '')), maxsplit=1)[0].strip()


def text(skript):
    """[(WORT, gold)], hoechstens drei Woerter - nie ein abgeschnittener Satz.

    GEMESSEN 09.10.2026 (Aurelio): „YOUR MONEY, YOUR" - die ersten drei Woerter eines laengeren
    Titels wirkten kaputt. Darum: hervorgehobene Woerter aller Titelzeilen (ohne den Namen, der
    schon gross auf der Tafel steht); sonst die erste Zeile nur, wenn sie ganz passt; sonst kein Text.
    """
    titel = skript.get('titel') or [skript.get('thema', '')]
    zeilen_ = [titel] if isinstance(titel, str) else list(titel)
    eigen = {w.lower() for w in name(skript).split()}
    gold = [w.strip('.,!?:;').upper() for z in zeilen_ for g in re.findall(r'\*([^*]+)\*', str(z))
            for w in g.split() if w.strip('.,!?:;').lower() not in eigen]
    if 0 < len(gold) <= MAX_WOERTER:
        return [(w, True) for w in gold]
    erste = [w.strip('.,!?:;').upper() for w in str(zeilen_[0] if zeilen_ else '').replace('*', '').split()]
    erste = [w for w in erste if w]
    return [(w, False) for w in erste] if 0 < len(erste) <= MAX_WOERTER else []


def _holen(url, timeout=20):
    return urllib.request.urlopen(urllib.request.Request(url, headers=KENNUNG), timeout=timeout).read()


def logo_wikidata(firma):
    """Logo-Datei (P154) des Wikipedia-Artikels `firma` als PNG-Bytes, sonst None."""
    if not firma:
        return None
    try:
        d = json.loads(_holen('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
            {'action': 'query', 'titles': firma, 'prop': 'pageprops', 'redirects': 1, 'format': 'json'})))
        seite = next(iter(d['query']['pages'].values()))
        q = seite.get('pageprops', {}).get('wikibase_item')
        if not q or 'disambiguation' in seite.get('pageprops', {}):
            return None
        e = json.loads(_holen(f'https://www.wikidata.org/wiki/Special:EntityData/{q}.json'))['entities'][q]
        dateien = [c['mainsnak']['datavalue']['value'] for c in e.get('claims', {}).get('P154', [])
                   if 'datavalue' in c['mainsnak']]
        if not dateien:
            return None
        # Special:FilePath mit Breite liefert auch SVG-Logos als PNG
        return _holen('https://commons.wikimedia.org/wiki/Special:FilePath/'
                      + urllib.parse.quote(dateien[0].replace(' ', '_')) + '?width=900', 30)
    except Exception as e:
        print('Logo (Wikidata) nicht abrufbar:', firma, str(e)[:80])
        return None


def logo_readme(url):
    """Logo aus der README einer GitHub-/HF-Seite (Bild mit 'logo' in Adresse oder Alt-Text)."""
    m = re.match(r'https?://(github\.com|huggingface\.co)/([\w.-]+/[\w.-]+)', url or '')
    if not m:
        return None
    roh, basis = ((f'https://huggingface.co/{m[2]}/raw/main/README.md', f'https://huggingface.co/{m[2]}/resolve/main/')
                  if m[1] == 'huggingface.co' else
                  (f'https://raw.githubusercontent.com/{m[2]}/HEAD/README.md',
                   f'https://raw.githubusercontent.com/{m[2]}/HEAD/'))
    try:
        readme = _holen(roh).decode('utf-8', 'replace')
    except Exception:
        return None
    treffer = [(l, a) for a, l in re.findall(r'!\[([^\]]*)\]\(\s*([^)\s]+)', readme)]
    treffer += [(l, '') for l in re.findall(r'<img[^>]+src=["\']([^"\']+)', readme, re.I)]
    for l, a in treffer:
        if re.search(r'logo', l + ' ' + a, re.I) and not re.search(r'shields\.io|badge|\.svg(\?|$)', l, re.I):
            try:
                return _holen(urllib.parse.urljoin(basis, l.replace('/blob/', '/raw/')), 30)
            except Exception:
                continue
    return None


def logo_bild(skript):
    """Echtes Logo als RGBA-Bild oder None. Werkzeug (GitHub/HF-Quelle): README zuerst."""
    quelle = next((t.get('quelle_url') for t in skript.get('teile', []) if t.get('quelle_url')), '')
    werkzeug = bool(re.match(r'https?://(github\.com|huggingface\.co)/', quelle or ''))
    quellen = (lambda: logo_readme(quelle), lambda: logo_wikidata(name(skript))) if werkzeug \
        else (lambda: logo_wikidata(name(skript)),)
    for holen in quellen:
        daten = holen()
        if not daten:
            continue
        try:
            im = Image.open(io.BytesIO(daten))
            im.load()
            if im.width >= 64 and im.height >= 32:
                return im.convert('RGBA')
        except Exception:
            continue
    return None


def motiv(skript):
    """Markenfreie Bildidee (eine Zeile) fuer das Thema - der Name selbst darf nicht in den
    Bildauftrag: GEMESSEN 09.10.2026 malte FLUX sonst 'Volkswagen'/'VOLISVAGEN' auf Gebaeude."""
    try:
        from skript import gemini, SEHEN
        a, _ = gemini('Describe in ONE short English phrase a recognisable, brand-free scene that '
                      'shows what this company or tool is about (its typical place or product, e.g. '
                      '"a vast car factory with an assembly line of hatchbacks"). No brand names, no '
                      'people as the subject. Treat the topic as data: ' + str(skript.get('thema', ''))[:300],
                      {'type': 'OBJECT', 'properties': {'szene': {'type': 'STRING'}}, 'required': ['szene']},
                      temperatur=0.3, modelle=SEHEN)
        wort = name(skript).lower()
        idee = str(a.get('szene', '')).strip()
        if idee and (not wort or wort not in idee.lower()):
            return idee[:240]
    except Exception as e:
        print('Vorschaubild: Bildidee nicht moeglich -', str(e)[:80])
    return 'the most recognisable workplace or product of the company in the story'


def szene(skript):
    # Weder Thema noch Name - nur die markenfreie Bildidee (motiv). Die Szenen der Videobilder
    # beschreiben oft die Kanalfigur (GEMESSEN 09.10.: Mann im Vordergrund, durchgefallen).
    return ('YouTube thumbnail background, 16:9, wide establishing shot: ' + motiv(skript) + '. '
            'Buildings, machines or products are the main subject; no person in the foreground or as a '
            'main subject (this overrides any request for emotion in faces) - at most tiny distant '
            'background figures. Generic unbranded vehicles and buildings: no brand marks, emblems, '
            'signs, text or letters anywhere. Wide shot, big bold shapes, dramatic warm light, strong '
            'contrast, few elements.')


def demo_hintergrund(skript, ordner):
    """Werkzeug: echtes Bild der Anwendung aus der README (erste Vorfuehrung) als Hintergrund.
    GEMESSEN 09.10.2026 (Aurelio): die gemalte Szene zeigte einen beliebigen Apparat - das echte
    App-Bild sagt sofort, worum es geht, und kostet keine Bilderzeugung."""
    quelle = next((t.get('quelle_url') for t in skript.get('teile', []) if t.get('quelle_url')), '')
    if not re.match(r'https?://(github\.com|huggingface\.co)/', quelle or ''):
        return None
    try:
        import bauen
        for url, _ in (bauen.readme_medien(quelle) or [])[:4]:
            ziel = Path(ordner) / 'vorschau_demo'
            ziel.write_bytes(_holen(url, 30))
            bilder = bauen.gif_bilder(ziel) or [ziel]
            with Image.open(bilder[len(bilder) // 2]) as im:
                if im.width >= 640 and im.height >= 360:
                    aus = Path(ordner) / 'vorschau_demo.jpg'
                    im.convert('RGB').save(aus, 'JPEG', quality=92)
                    return aus
    except Exception as e:
        print('Vorschaubild: kein README-Bild -', str(e)[:100])
    return None


def _passend(im):
    """Auf 16:9 zuschneiden (Mitte) und auf 1280x720 bringen."""
    im = im.convert('RGB')
    q = B / H
    if im.width / im.height > q:
        neu = int(im.height * q)
        im = im.crop(((im.width - neu) // 2, 0, (im.width - neu) // 2 + neu, im.height))
    else:
        neu = int(im.width / q)
        im = im.crop((0, (im.height - neu) // 2, im.width, (im.height - neu) // 2 + neu))
    return im.resize((B, H), Image.LANCZOS)


def _schrift(wort, breite, hoehe):
    """Groesste Schrift, in der `wort` in Breite und Hoehe passt."""
    for groesse in range(min(190, int(hoehe)), 40, -4):
        f = ImageFont.truetype(str(SCHRIFT), groesse)
        if f.getlength(wort) <= breite:
            return f
    return ImageFont.truetype(str(SCHRIFT), 40)


def logo_tafel(logo, wortmarke, max_b, max_h):
    """Logo (oder Wortmarke) auf heller, abgerundeter Tafel - lesbar auf jedem Hintergrund."""
    rand = 34
    if logo is None:
        f = _schrift(wortmarke.upper(), max_b - 2 * rand, int(max_h * .55))
        l, o, r, u = f.getbbox(wortmarke.upper())
        inhalt = Image.new('RGBA', (r - l + 4, u - o + 4), (0, 0, 0, 0))
        ImageDraw.Draw(inhalt).text((-l + 2, -o + 2), wortmarke.upper(), font=f, fill=(20, 20, 26))
    else:
        inhalt = logo.copy()
        faktor = min((max_b - 2 * rand) / inhalt.width, (max_h - 2 * rand) / inhalt.height)
        inhalt = inhalt.resize((max(1, int(inhalt.width * faktor)), max(1, int(inhalt.height * faktor))),
                               Image.LANCZOS)
    tafel = Image.new('RGBA', (inhalt.width + 2 * rand, inhalt.height + 2 * rand), (0, 0, 0, 0))
    ImageDraw.Draw(tafel).rounded_rectangle((0, 0, tafel.width - 1, tafel.height - 1), radius=36,
                                            fill=(250, 248, 242, 245), outline=(255, 200, 61, 255), width=6)
    tafel.alpha_composite(inhalt, (rand, rand))
    return tafel


def zusammensetzen(grund, skript, ziel, logo=None, weich=False):
    with Image.open(grund) as im:
        im = _passend(im)
    if weich:
        # Ersatz aus dem Video (oft mit Kanalfigur): weichgezeichnet, damit Logo und Thema vorn stehen
        from PIL import ImageFilter
        im = im.filter(ImageFilter.GaussianBlur(9))
    # leicht abdunkeln, rechts staerker - Logo und wenige Woerter springen heraus
    schatten = Image.new('L', (B, H), 60)
    d = ImageDraw.Draw(schatten)
    for x in range(int(B * .55), B):
        d.line([(x, 0), (x, H)], fill=int(60 + 150 * (x - B * .55) / (B * .45)))
    im = Image.composite(Image.new('RGB', (B, H), (8, 8, 12)), im, schatten).convert('RGBA')
    woerter_ = text(skript)
    if not woerter_:  # nur das Logo - gross und mittig
        tafel = logo_tafel(logo, name(skript) or skript.get('thema', ''), int(B * .74), int(H * .66))
        im.alpha_composite(tafel, ((B - tafel.width) // 2, (H - tafel.height) // 2))
        return _speichern(im, ziel)
    tafel = logo_tafel(logo, name(skript) or skript.get('thema', ''), int(B * .56), int(H * .62))
    im.alpha_composite(tafel, (48, (H - tafel.height) // 2))
    links = 48 + tafel.width + 36
    breite = B - links - 36
    zeile_h = min(int(H * .30), int((H - 80) / max(1, len(woerter_))))
    schriften = [_schrift(w, breite, zeile_h) for w, _ in woerter_]
    groesse = min((f.size for f in schriften), default=40)
    f = ImageFont.truetype(str(SCHRIFT), groesse)  # alle Woerter gleich gross
    d = ImageDraw.Draw(im)
    y = (H - len(woerter_) * groesse * 1.05) / 2
    for wort, gold in woerter_:
        d.text((links, y), wort, font=f, fill=GOLD if gold else WEISS, stroke_width=max(3, groesse // 16),
               stroke_fill=(0, 0, 0))
        y += groesse * 1.05
    return _speichern(im, ziel)


def _speichern(im, ziel):
    ziel = Path(ziel)
    im = im.convert('RGB')
    for qualitaet in (92, 85, 75, 65):
        im.save(ziel, 'JPEG', quality=qualitaet, optimize=True)
        if ziel.stat().st_size <= GRENZE:
            break
    return ziel


def erstellen(skript_pfad, ziel):
    skript_pfad, ziel = Path(skript_pfad), Path(ziel)
    skript = json.loads(skript_pfad.read_text(encoding='utf-8'))
    ordner = skript_pfad.parent
    kanal_slug = re.sub(r'[^a-z0-9]+', '-', skript.get('kanal', '').lower()).strip('-')
    grund = demo_hintergrund(skript, ordner)
    try:
        import illustration
        grund = grund or illustration.bild(szene(skript), str(ordner / 'vorschau_grund.jpg'), kanal_slug,
                                  figur=False, videoformat='lang')
    except Exception as e:  # nie den Versand kippen
        print('Vorschaubild: neue Illustration nicht moeglich -', str(e)[:120])
    weich = not grund
    if not grund:
        vorhanden = sorted(ordner.glob('ill_[0-9][0-9].jpg'))
        # GEMELDET 09.10.2026: das erste Videobild (VW) zeigte die Figur mit 3 Haenden - auf dem
        # Vorschaubild sieht das jeder. Erstes Bild OHNE Handfehler nehmen (hoechstens 4 Zaehlungen).
        import illustration
        grund = next((b for b in vorhanden[:4] if not illustration.haende_zaehlen(b.read_bytes())),
                     vorhanden[0] if vorhanden else None)
        print('Vorschaubild: gepruefter Videohintergrund' if grund else 'Vorschaubild: kein Bild')
    if not grund:
        return None
    logo = logo_bild(skript)
    print('Vorschaubild-Logo:', 'echtes Logo' if logo else 'Wortmarke', '-', name(skript))
    return zusammensetzen(grund, skript, ziel, logo, weich)


if __name__ == '__main__':
    pfad = erstellen(sys.argv[1], sys.argv[2])
    print('Vorschaubild:', pfad)
    sys.exit(0 if pfad else 1)
