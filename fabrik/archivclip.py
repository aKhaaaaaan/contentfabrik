"""Gemeinfreie Archivclips zwischen den gemalten Motiven (Nutzerentscheidung 29.10.2026).

Nutzer: "kleine Clips einfuegen, eingefaerbt und gemalt", "Motivzahl behalten" - allgemeine Szenen (Fabrik, Zug,
Naehsaal, Buero, Strasse) werden echte Filmaufnahmen aus der Epoche statt eines gemalten Bildes. Das spart
Cloudflare-Bildkontingent und Bildkorrekturrunden; konkrete Saetze ("sechs Naehmaschinen") bleiben gemalt.

Quelle: Internet Archive, Sammlung Prelinger, NUR Filme mit ausdruecklicher Public-Domain-Kennzeichnung
(licenseurl). Die KI waehlt aus mehreren Standbildern die passende Stelle; unter MIN_NOTE kein Clip.
Einfaerben (DDColor) und Malen (wie "Gemalt+", Probe 28.10.) in farbe(); jeder Fehler -> None = gemaltes Bild.
"""
import io
import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

# 30.10.2026: Wikimedia antwortet ohne Kontaktangabe im User-Agent mit 429 (Richtlinie fuer Bots)
KENNUNG = {'User-Agent': 'contentfabrik/1.0 (https://github.com/aKhaaaaaan/contentfabrik; public-domain archive clips)'}
# Satz/Szene -> Archivsuche. Nur allgemeine, filmbare Szenen; Reihenfolge = Vorrang.
SZENEN = [
    (r'\b(?:sewing|seamstress\w*|tailor\w*|garments?|textiles?|clothing)\b', 'sewing'),
    (r'\b(?:trains?|railways?|railroads?|stations?|locomotives?|platforms?)\b', 'railroad'),
    (r'\b(?:factor(?:y|ies)|plants?|assembly|mills?|workshops?|machinery|workers)\b', 'factory workers'),
    (r'\b(?:ships?|harbou?rs?|ports?|docks?|shipyards?)\b', 'ship harbor'),
    # Rolls-Royce 29.10.: Geldgeschichten (Aktien, Tresor, Vorstand) fanden keinen einzigen Suchbegriff
    (r'\b(?:banks?|bankers?|vaults?|cash ?box(?:es)?|stock exchange|exchange hall|shares?|investors?)\b', 'bank'),
    (r'\b(?:boardrooms?|board meeting|directors?)\b', 'business meeting'),
    (r'\b(?:offices?|clerks?|typewriters?|secretar\w+)\b', 'office workers'),
    (r'\b(?:shops?|stores?|customers?|counters?|shoppers?)\b', 'store customers'),
    (r'\b(?:cars?|automobiles?|motorcars?)\b', 'automobile'),
    (r'\b(?:streets?|downtown|traffic|city)\b', 'city street'),
    (r'\b(?:construction|cranes?|building site)\b', 'construction'),
    (r'\b(?:farms?|fields?|harvest\w*|tractors?)\b', 'farm'),
]
JAHR_MAX = 1975  # Prelinger reicht bis 1987, gut bestueckt bis Mitte der 70er
MIN_NOTE = 7
KANDIDATEN = 6


def suchbegriff(*texte):
    t = ' '.join(str(x or '') for x in texte)
    return next((begriff for muster, begriff in SZENEN if re.search(muster, t, re.I)), None)


# Rolls-Royce 29.10.: Bildplan schrieb "Edwardian" statt einer Jahreszahl -> kein einziger Archivversuch
EPOCHEN = [(r'\bvictorian\b', 1885), (r'\bedwardian\b', 1905), (r'\bturn[- ]of[- ]the[- ]century\b', 1900),
           (r'\b(?:roaring )?twenties\b', 1925), (r'\b(?:great )?depression[- ]era\b|\bgreat depression\b', 1933),
           (r'\binter-?war\b', 1930), (r'\bwartime\b|\bworld war (?:ii|two|2)\b', 1943), (r'\bpost-?war\b', 1950)]


def jahr(epoche):
    """Jahr aus 'early 1930s', '1924', 'postwar 1950s', 'Edwardian'; None fuer modern/unklar."""
    t = str(epoche or '')
    m = re.search(r'\b(1[89]\d|20\d)(\d)s?\b', t)
    if m:
        return int(m.group(1) + m.group(2))
    return next((j for muster, j in EPOCHEN if re.search(muster, t, re.I)), None)


def story_jahr(*texte):
    """Fruehestes Jahr der Geschichte ("December 1906 ... January 1907" -> 1906) fuer Szenen ohne Epoche."""
    jahre = [int(a + b) for a, b in re.findall(r'\b(1[89]\d|20[0-2])(\d)\b', ' '.join(str(x or '') for x in texte))]
    return min(jahre) if jahre else None


def _json(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=KENNUNG), timeout=timeout) as r:
        return json.load(r)


def filme(begriff, um_jahr, anzahl=4):
    q = (f'collection:prelinger AND licenseurl:*publicdomain* AND ({begriff}) '
         f'AND year:[{um_jahr - 12} TO {um_jahr + 12}]')
    d = _json('https://archive.org/advancedsearch.php?' + urllib.parse.urlencode(
        {'q': q, 'fl[]': ['identifier', 'title', 'year'], 'rows': anzahl, 'sort[]': 'downloads desc',
         'output': 'json'}, doseq=True))
    return [x['identifier'] for x in d['response']['docs']]


def datei(kennung):
    """(Dateiname, Sekunden, Lizenz) der 640x480-Fassung (bzw. der kleinsten MP4)."""
    d = _json(f'https://archive.org/metadata/{kennung}')
    lizenz = d.get('metadata', {}).get('licenseurl', '')
    if 'publicdomain' not in str(lizenz):
        return None
    mp4 = [f for f in d.get('files', []) if f['name'].endswith('.mp4') and f.get('length')]
    if not mp4:
        return None
    f = next((f for f in mp4 if f['name'] == f'{kennung}.mp4'), min(mp4, key=lambda f: int(f.get('size', 0))))
    return f['name'], float(f['length']), lizenz


def url(kennung, name):
    return f'https://archive.org/download/{kennung}/{urllib.parse.quote(name)}'


def eingang(adresse):
    """ffmpeg-Eingabe; den User-Agent gibt es nur fuer Web-Adressen (lokale Commons-Kopie: "Option not found")."""
    return (['-user_agent', KENNUNG['User-Agent']] if str(adresse).startswith('http') else []) + ['-i', str(adresse)]


def standbild(adresse, sekunde):
    r = subprocess.run(['ffmpeg', '-loglevel', 'error', '-ss', f'{sekunde:.1f}', *eingang(adresse),
                        '-frames:v', '1', '-vf', 'scale=384:-2', '-f', 'mjpeg', '-'],
                       capture_output=True, timeout=60)
    return r.stdout if r.returncode == 0 and r.stdout else None


SCHEMA = {'type': 'OBJECT', 'properties': {'beste': {'type': 'INTEGER'}, 'note': {'type': 'INTEGER'},
                                           'gesehen': {'type': 'STRING'}}, 'required': ['beste', 'note', 'gesehen']}


def auswahl(bilder, satz, szene):
    """(Index, Note) des Standbilds, das den gesprochenen Satz am besten zeigt."""
    from skript import gemini, SEHEN
    import bildvision
    auftrag = ('You pick archive film footage for a short documentary. The narrator says: '
               + json.dumps(satz) + '. Planned scene: ' + json.dumps(str(szene)[:200])
               + f'. Images 0-{len(bilder) - 1} are stills from public-domain films. Pick the still whose visible '
               'subject and action best illustrate these words (people, place, objects, era). Score 1-10: 7+ only if '
               'a viewer would accept it as showing this moment; title cards, text, credits, cartoons, blurry or '
               'unrelated frames score 1-3. Describe what is visible in gesehen.')
    d, _ = bildvision.mit_ausweichweg(lambda: gemini(auftrag, SCHEMA, bilder=bilder, modelle=SEHEN, temperatur=.1),
                                      auftrag, SCHEMA, bilder[0])
    beste = d.get('beste')
    if not isinstance(beste, int) or not 0 <= beste < len(bilder):
        return None, 0
    return beste, int(d.get('note') or 0)


# Nintendo 30.10.2026: Nutzer - "nur die paar Begriffe (Fabrik, Buero) sind zu wenig". GEMESSEN: Prelinger findet per
# Freitext "gambling" 12, "Japan" 66 Filme; Wikimedia Commons hat kurze gemeinfreie Filme ("Playing Cards (1896)",
# "Le Tripot clandestin (1905)"). Darum zuerst die Suchwoerter der Bildplanung (2-4 Woerter je Einstellung), dann die
# festen Szenen; Quellen Prelinger und Commons. Die KI-Auswahl (MIN_NOTE) bleibt das Tor.
VERSUCHE = 4  # Filme je Einstellung (je Film 6 Standbilder + eine KI-Anfrage)
COMMONS_LIZENZ = re.compile(r'^(?:public domain|cc0|cc by \d)', re.I)  # ohne SA/NC/ND: gemaltes Video bleibt frei
COMMONS_MAX_S = 1800


def begriffe(satz, szene, suche=''):
    """Suchbegriffe in Vorrang-Reihenfolge: Bildplan-Suchwoerter, deren erste zwei, feste Szene, Einzelwoerter."""
    worte = re.findall(r"[A-Za-z][A-Za-z'-]+", str(suche or ''))[:4]
    # GEMESSEN 30.10.: "gambling card players" 0 Treffer, "gambling" allein 12 (Prelinger) bzw. 4 (Commons)
    liste = [' '.join(worte), ' '.join(worte[:2]), suchbegriff(satz, szene)] + [w for w in worte if len(w) >= 5]
    return [b for i, b in enumerate(liste) if b and b not in liste[:i]]


def commons(begriff, anzahl=4):
    """Kurze Videos von Wikimedia Commons mit freier Lizenz ohne Weitergabepflicht."""
    d = _json('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': f'{begriff} filetype:video',
         'gsrnamespace': 6, 'gsrlimit': 10, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size',
         'iiextmetadatafilter': 'LicenseShortName'}))
    treffer = []
    for p in sorted((d.get('query') or {}).get('pages', {}).values(), key=lambda p: p.get('index', 0)):
        ii = (p.get('imageinfo') or [{}])[0]
        lizenz = ((ii.get('extmetadata') or {}).get('LicenseShortName') or {}).get('value', '')
        if COMMONS_LIZENZ.match(lizenz) and 3 <= float(ii.get('duration') or 0) <= COMMONS_MAX_S and ii.get('url'):
            treffer.append({'kennung': p['title'], 'adresse': ii['url'], 'sekunden': float(ii['duration']),
                            'groesse': int(ii.get('size') or 0),
                            'lizenz': lizenz, 'seite': ii.get('descriptionurl', ''), 'quelle': 'Wikimedia Commons'})
    return treffer[:anzahl]


def prelinger(begriff, j):
    for kennung in filme(begriff, j):
        info = datei(kennung)
        if info:
            name, sekunden, lizenz = info
            yield {'kennung': kennung, 'adresse': url(kennung, name), 'sekunden': sekunden, 'lizenz': lizenz,
                   'seite': f'https://archive.org/details/{kennung}', 'quelle': 'Internet Archive (Prelinger)'}


def kandidaten(begriff, j):
    for quelle in (lambda: prelinger(begriff, j), lambda: commons(begriff)):
        try:
            yield from quelle()
        except Exception as e:  # eine Quelle offline -> die andere
            print('Archivsuche nicht erreichbar:', type(e).__name__)


COMMONS_HOLEN_MAX = 80_000_000


def holen(film):
    """Commons-Datei einmal herunterladen statt 7 Einzelabrufe (6 Standbilder + Schnitt).

    GEMESSEN 30.10.2026 (Business Adidas 41048229773): Standbilder klappten, der Schnitt desselben Commons-Films
    brach ab (CalledProcessError); lokal lief er durch - Ursache vermutlich Drosselung (429), nicht bewiesen."""
    if film.get('quelle') != 'Wikimedia Commons':
        return film
    import hashlib
    import tempfile
    pfad = urllib.parse.urlparse(film['adresse']).path  # /wikipedia/commons/6/67/Name.webm
    # Tullamaine-Film: Original 227 MB (4K) fuer 45 s. Commons bietet jede Datei auch als 480p-Fassung an.
    klein = ('https://upload.wikimedia.org' + pfad.replace('/commons/', '/commons/transcoded/', 1)
             + '/' + pfad.rsplit('/', 1)[1] + '.480p.vp9.webm')
    for adresse in (klein, film['adresse'] if 0 < film.get('groesse', 0) <= COMMONS_HOLEN_MAX else None):
        if not adresse:
            continue
        ziel = Path(tempfile.gettempdir()) / ('commons_' + hashlib.sha1(adresse.encode()).hexdigest()[:12] + '.webm')
        try:
            if not ziel.exists():
                with urllib.request.urlopen(urllib.request.Request(adresse, headers=KENNUNG), timeout=120) as r:
                    daten = r.read(COMMONS_HOLEN_MAX + 1)
                if len(daten) > COMMONS_HOLEN_MAX:
                    continue
                ziel.write_bytes(daten)
            return dict(film, adresse=str(ziel))
        except OSError as e:
            print('Commons-Datei nicht geladen:', type(e).__name__)
    return film


def finden(satz, szene, epoche, benutzt=(), suche=''):
    """{'kennung','adresse','sekunde','note','lizenz','seite','quelle'} oder None."""
    j = epoche if isinstance(epoche, int) else jahr(epoche)
    if not j or j > JAHR_MAX:
        return None
    versucht = set(benutzt)
    for begriff in begriffe(satz, szene, suche):
        for film in kandidaten(begriff, j):
            if len(versucht) - len(set(benutzt)) >= VERSUCHE:
                return None
            if film['kennung'] in versucht:
                continue
            versucht.add(film['kennung'])
            film = holen(film)
            stellen = [film['sekunden'] * (k + 1) / (KANDIDATEN + 1) for k in range(KANDIDATEN)]
            bilder, gueltig = [], []
            for s in stellen:
                b = standbild(film['adresse'], s)
                if b:
                    bilder.append(b)
                    gueltig.append(s)
            if len(bilder) < 2:
                continue
            index, note = auswahl(bilder, satz, szene)
            print(f"Archivclip {film['kennung'][:40]} ({begriff}, ~{j}): Note {note}")
            if index is not None and note >= MIN_NOTE:
                return dict(film, sekunde=gueltig[index], note=note)
    return None


def schneiden(fund, dauer, ziel):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', f"{max(0, fund['sekunde'] - 0.5):.1f}",
                    *eingang(fund['adresse']),
                    '-t', f'{dauer + 0.3:.2f}', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', str(ziel)],
                   check=True, timeout=180)
    return Path(ziel)


# ---- Einfaerben und Malen ---------------------------------------------------------------------------------
# GEMESSEN 29.10.2026 (farbprobe.yml): DDColor modelscope bei 512 und jedem Bild 4,7 s/Bild; bei 256 und jedem
# dritten Bild 0,38 s/Bild (~35 s je 3-s-Clip) mit fast gleich guten Farben. Das kleine Modell (0,2 s) liess den
# Himmel grau - darum das grosse. Farbe wandert langsam: dazwischen Helligkeit des Bildes + letzte Farbe (Lab).
DDCOLOR_MODELL, DDCOLOR_GROESSE, DDCOLOR_SCHRITT = 'ddcolor_modelscope', 256, 3
SW_SAETTIGUNG = 25  # mittlere HSV-Saettigung darunter = Schwarz-Weiss-Film (Farbfilme der 50er liegen weit drueber)
_ddcolor = None


def schwarzweiss(bilder):
    import cv2
    import numpy as np
    return float(np.mean([cv2.cvtColor(b, cv2.COLOR_BGR2HSV)[..., 1].mean() for b in bilder])) < SW_SAETTIGUNG


def _einfaerber():
    """DDColor-Pipeline oder None (CF_DDCOLOR = Ordner des geklonten Repos, video.yml nur fuer Business)."""
    global _ddcolor
    if _ddcolor is None:
        import os
        import sys
        ordner = os.environ.get('CF_DDCOLOR')
        if not ordner:
            return None
        sys.path.insert(0, ordner)
        from ddcolor import DDColor, ColorizationPipeline
        from huggingface_hub import PyTorchModelHubMixin

        class DDColorHF(DDColor, PyTorchModelHubMixin):
            def __init__(self, config=None, **kwargs):
                if isinstance(config, dict):
                    kwargs = {**config, **kwargs}
                super().__init__(**kwargs)
        _ddcolor = ColorizationPipeline(DDColorHF.from_pretrained(f'piddnad/{DDCOLOR_MODELL}'),
                                        input_size=DDCOLOR_GROESSE)
    return _ddcolor


def gemalt(f, satt=1.7):
    """"Gemalt+" (Nutzer 28.10.: "eingefaerbt und gemalt sieht viel besser aus"): Malfilter, Vibrance, warm."""
    import cv2
    import numpy as np
    f = cv2.stylization(f, sigma_s=45, sigma_r=0.35)
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
    s = hsv[..., 1] / 255
    hsv[..., 1] = np.clip(255 * (s + (1 - s) * s * (satt - 1) * 1.2 + s * (satt - 1) * .5), 0, 255)
    hsv[..., 2] = np.clip((hsv[..., 2] - 128) * 1.18 + 132, 0, 255)
    g = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    g[..., 2] *= 1.10
    g[..., 0] *= .88
    return np.clip(g, 0, 255).astype(np.uint8)


def farbe(roh, ziel, standbild_ziel):
    """(Video, erstes Bild) eingefaerbt (nur Schwarz-Weiss) und gemalt; None, None wenn es nicht geht."""
    import cv2
    cap = cv2.VideoCapture(str(roh))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    bilder = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        bilder.append(f)
    if len(bilder) < 2:
        return None, None
    einfaerber = None
    if schwarzweiss(bilder[::max(1, len(bilder) // 5)]):
        einfaerber = _einfaerber()
        if einfaerber is None:
            print('Archivclip schwarz-weiss, aber kein DDColor - gemaltes Bild statt Clip')
            return None, None
    h, w = bilder[0].shape[:2]
    prozess = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
                                '-s', f'{w}x{h}', '-r', f'{fps:.3f}', '-i', '-', '-an', '-c:v', 'libx264',
                                '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', str(ziel)],
                               stdin=subprocess.PIPE)
    ab = None
    for k, f in enumerate(bilder):
        if einfaerber is not None:
            if k % DDCOLOR_SCHRITT == 0 or ab is None:
                bunt = einfaerber.process(f)
                ab = cv2.cvtColor(bunt, cv2.COLOR_BGR2LAB)[..., 1:]
            else:
                lab = cv2.cvtColor(f, cv2.COLOR_BGR2LAB)
                lab[..., 1:] = ab
                bunt = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            bunt = f  # Farbfilm: nur malen
        bild = gemalt(bunt)
        if k == 0:
            cv2.imwrite(str(standbild_ziel), bild)
        prozess.stdin.write(bild.tobytes())
    prozess.stdin.close()
    if prozess.wait() != 0:
        return None, None
    return Path(ziel), Path(standbild_ziel)


# ---- Moderne Clips (Pixabay) ------------------------------------------------------------------------------
# Nutzer 29.10.2026: "aktuelle Videos, die nicht schwarz-weiss sind" - viele Firmengeschichten spielen nach 1975
# (SK Hynix 2001, Moderna, Anthropic). Ab 1995 Pixabay (frei kommerziell nutzbar, vorhandene KI-Auswahl in
# bauen.clip_fuer), nur gemalt. 1975-1995 bleibt gemalt: moderne Clips zeigten Smartphones/Flachbildschirme.
# Logos bleiben erlaubt (Nutzer: "bei Firmengeschichten gehoeren Logos dazu").
MODERN_AB = 1995
MODERN = re.compile(r'\b(?:modern|today|present[- ]day|contemporary|nowadays)\b', re.I)


def szenen_jahr(szene, geschichte=None):
    """Jahr der Szene; ohne eigene Angabe (und nicht 'modern') das Jahr der Geschichte."""
    j = jahr(szene)
    return j if j is not None or MODERN.search(str(szene or '')) else geschichte


def epoche_modern(szene, ohne_epoche=False, geschichte=None):
    """True: moderne Szene (Pixabay); False: keine Clips; None: historisch (Archiv)."""
    j = szenen_jahr(szene, geschichte)
    if j is not None:
        return True if j >= MODERN_AB else (None if j <= JAHR_MAX else False)
    return True if (MODERN.search(str(szene or '')) or ohne_epoche) else False


# Intel 30.10.2026 (1968-1985): kein einziger Clip - Chip-Saetze fanden keinen Archivbegriff (Fabrikfilme der 60er
# bekamen Note 2-3), und 1975-1995 bleibt Pixabay zu. Nahaufnahmen von Bauteilen zeigen keine Epoche (keine Mode,
# kein Smartphone) - die gehen in jeder Zeit zu Pixabay. Kartoffel-/Pokerchips sind keine Bauteile.
ZEITLOS = [(r'(?<!potato )(?<!poker )(?<!tortilla )(?<!corn )\b(?:micro)?chips?\b|\b(?:micro)?processors?\b|'
            r'\bsemiconductors?\b|\btransistors?\b', 'computer chip'),
           (r'\b(?:circuit|mother)boards?\b|\bcircuit boards?\b|\bsilicon wafers?\b|\bwafers?\b', 'circuit board'),
           # Nintendo 30.10.2026 (Hanafuda, Yakuza-Spielhallen): Archivfilme Note 2-6, kein Clip. Karten und Wuerfel
           # sehen seit 100 Jahren gleich aus; Kredit-/Visitenkarten sind nicht gemeint.
           (r'\b(?:playing|parlou?r|gambling|hanafuda|flower|poker) cards?\b|\bcard games?\b|\bdecks? of cards\b|'
            r'\bhanafuda\b|\bdice\b|\bgambl(?:ing|ers?|ed)\b', 'playing cards'),
           (r'\b(?:gold |silver |old )?coins?\b', 'coins')]


def zeitlos(*texte):
    t = ' '.join(str(x or '') for x in texte)
    return next((begriff for muster, begriff in ZEITLOS if re.search(muster, t, re.I)), None)


def zuschneiden(pfad, dauer, ziel):
    """Pixabay-Clips sind lang und gross: nur die Einstellungsdauer, hoechstens 720 px hoch."""
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(pfad), '-t', f'{dauer + 0.3:.2f}', '-an',
                    '-vf', "scale=-2:'min(720,ih)'", '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                    str(ziel)], check=True, timeout=180)
    return Path(ziel)


def epochen_hinweis(j):
    """Zusatz fuer die Clip-Auswahl, wenn Stock-Material eine historische Szene zeigen soll."""
    return (f' [Story set in {j}: choose only footage where nothing visible postdates {j} - no smartphones, screens, '
            'modern cars, modern clothing or modern buildings. Close-ups of hands, nature, fire, water or timeless '
            'objects are fine. If none qualifies, nummer=-1.]')


def fuer_einstellung(satz, szene, suche, dauer, basis, archiv=True, ohne_epoche=False, pixabay=None, benutzt=None,
                     geschichte=None):
    """(Video, Standbild, Quelle) fuer eine Einstellung oder (None, None, None) -> gemaltes Bild.

    pixabay(suchwoerter, zusatz) - zusatz haengt die Epochenregel an den Satz fuer die KI-Auswahl."""
    basis = Path(basis)
    modern = epoche_modern(szene, ohne_epoche, geschichte)
    j = None if modern else szenen_jahr(szene, geschichte)
    hinweis = epochen_hinweis(j) if j else ''

    def stock(begriff, zusatz=''):
        pfad, quelle = pixabay(begriff, zusatz)
        if not pfad:
            return None, None, None
        roh = zuschneiden(pfad, dauer, basis.with_name(basis.name + '_roh.mp4'))
        video, bild = farbe(roh, basis.with_suffix('.mp4'), basis.with_suffix('.jpg'))
        return (video, bild, dict(quelle, nennung='Stock footage, painted')) if video else (None, None, None)

    if modern and pixabay:
        return stock(suche or suchbegriff(satz, szene))
    bauteil = zeitlos(satz, szene, suche)
    if bauteil and pixabay:
        ergebnis = stock(bauteil, hinweis)
        if ergebnis[0]:
            return ergebnis
    if modern is None and archiv:
        fund = finden(satz, szene, j, benutzt or set(), suche) if begriffe(satz, szene, suche) else None
        if fund:
            roh = schneiden(fund, dauer, basis.with_name(basis.name + '_roh.mp4'))
            video, bild = farbe(roh, basis.with_suffix('.mp4'), basis.with_suffix('.jpg'))
            if video:
                if benutzt is not None:
                    benutzt.add(fund['kennung'])
                return video, bild, {'quelle': f"{fund['quelle']}, {fund['lizenz']}", 'seite': fund['seite'],
                                     'lizenz': fund['lizenz'], 'nennung': 'Archival footage, colorized and painted'}
    # 30.10.2026, Nutzer: "nicht nur Karten freimachen - wir brauchen was generell". Archive haben fuer die meisten
    # Saetze nichts (Nintendo/Intel: Note 0-6). Pixabay hat viel mehr; die KI-Auswahl bekommt die Epoche und lehnt
    # alles Moderne ab, der Schlusspruefer kontrolliert die Epoche ebenfalls. Ohne Jahr (unklar) bleibt es gemalt.
    if pixabay and hinweis and suche and not bauteil:
        return stock(suche, hinweis)
    return None, None, None
