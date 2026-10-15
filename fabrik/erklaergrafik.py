"""Erklaergrafik fuer Werkzeug-Saetze ohne passenden echten Screenshot.

Nutzerentscheidung 15.10.2026: Bilder muessen wortgenau zum Satz passen. Lauf 38711622156
(FinceptTerminal): Saetze ueber API-Schluessel, Token-Kosten, Datenquellen oder Download hatten
kein README-Bild; gemalte Laptop-Szenen fielen beim Pruefer mit 2-4/10 durch. Die handgebauten
Bigarrow-Grafiken (Symbol + konkrete Begriffe) bestanden 18/18. Diese Grafik baut das automatisch:
ein Symbol fuer die Handlung des Satzes plus die gesprochenen Namen als Beschriftung.
Klar als Erklaergrafik gekennzeichnet - kein vorgetaeuschter Screenshot oder Messwert.
"""
from pathlib import Path
import re
import textwrap
from PIL import Image, ImageDraw, ImageFont

SCHRIFT = Path(__file__).resolve().parents[1] / 'schriften/Montserrat-ExtraBold.ttf'
# Reihenfolge = Vorrang. Woerter sind englisch, weil die Videos englisch gesprochen werden.
SYMBOLE = [
    ('schluessel', r'\b(api[ -]?keys?|keys?|token key|credentials?|login)\b'),
    ('rechnung', r'\b(bills?|billing|cost|costs|price|pricing|paid|charged?|per token|tokens?|\$\d)'),
    ('download', r'\b(download|install|release|setup|brew|pip|npm|clone)\b'),
    ('daten', r'\b(data|connectors?|sources?|api|feeds?|database|imports?)\b'),
    ('warnung', r'\b(catch|risk|warning|not financial advice|careful|limit|limitation|but)\b'),
]
STOPP = {'The', 'A', 'An', 'It', 'Its', 'Yes', 'No', 'And', 'But', 'Can', 'For', 'Catch', 'Data', 'The repo'}


def symbol(text):
    """Symbol der zuerst genannten Handlung; Warnung nur, wenn sonst nichts passt."""
    t = text.lower()
    treffer = [(m.start(), name) for name, muster in SYMBOLE for m in [re.search(muster, t)] if m]
    sachlich = [x for x in treffer if x[1] != 'warnung']
    return min(sachlich or treffer)[1] if treffer else 'diagramm'


def begriffe(text, motiv=''):
    """Gesprochene Eigennamen/Produkte als Beschriftung (OpenAI, Yahoo Finance, 100+); sonst Motiv."""
    woerter = re.findall(r"[A-Za-z0-9$+.'-]+[,.;:?!]?", text)
    namen, folge = [], []
    def schliessen():
        if folge:
            namen.append(' '.join(folge)); folge.clear()
    for k, roh in enumerate(woerter):
        w = roh.rstrip(",.;:?!'")
        zahl = re.fullmatch(r'(\d[\d,.]*)-plus', w)
        if zahl:
            schliessen(); namen.append(zahl[1] + '+')
        elif k > 0 and w[:1].isupper() and w not in STOPP:
            folge.append(w)
        elif re.fullmatch(r'\d[\d,.]*\+|\$\d[\d,.]*', w):
            schliessen(); namen.append(w)
        else:
            schliessen()
        if roh[-1:] in ',.;:?!':
            schliessen()
    schliessen()
    namen = [n for n in dict.fromkeys(namen) if n not in ('AI', 'I')]
    # Eichung 15.10.2026: Rechnung nur mit "LLM" bekam 4/10 ("pro Token" fehlte). Bei weniger als zwei
    # Namen steht die Kernaussage des Satzes zusaetzlich als Beschriftung.
    if len(namen) < 2 and motiv and str(motiv).upper() not in [n.upper() for n in namen]:
        namen.append(str(motiv).upper()[:24])
    return namen[:4]


def grafik(ziel, text, motiv='', titel=''):
    im = Image.new('RGB', (1080, 1920), '#10202d')
    d = ImageDraw.Draw(im)
    def font(n):
        return ImageFont.truetype(str(SCHRIFT), n)
    def txt(x, y, s, n=40, farbe='#edf6ff'):
        d.text((x, y), s, font=font(n), fill=farbe)
    gelb, tuerkis, hell = '#ffae35', '#20d2be', '#dce4ec'
    art = symbol(text)
    txt(75, 315, (titel or 'HOW IT WORKS').upper()[:28], 40, tuerkis)
    for k, zeile in enumerate(textwrap.wrap(str(motiv or text).upper(), 24)[:2]):
        txt(75, 380 + k * 52, zeile, 44)
    cx, cy = 540, 760
    if art == 'schluessel':
        d.ellipse((cx - 230, cy - 90, cx - 50, cy + 90), outline=gelb, width=28)
        d.rectangle((cx - 60, cy - 18, cx + 230, cy + 18), fill=gelb)
        for x in (cx + 120, cx + 190):
            d.rectangle((x, cy + 18, x + 30, cy + 80), fill=gelb)
    elif art == 'rechnung':
        # Eichung 15.10.2026: Rechnung nur mit $-Zeichen galt als Metapher (3/10). Abrechnungslogik
        # zeigen - Posten statt erfundener Betraege.
        d.rounded_rectangle((cx - 300, cy - 230, cx + 300, cy + 230), 20, fill=hell)
        txt(cx - 250, cy - 200, 'LLM BILL', 44, '#10202d')
        for k, posten in enumerate(('INPUT TOKENS  x  PRICE', 'OUTPUT TOKENS  x  PRICE')):
            txt(cx - 250, cy - 90 + k * 90, posten, 34, '#10202d')
        d.rectangle((cx - 250, cy + 95, cx + 250, cy + 103), fill='#10202d')
        txt(cx - 250, cy + 125, '= PAY PER TOKEN', 40, '#c2410c')
    elif art == 'download':
        d.polygon([(cx - 60, cy - 220), (cx + 60, cy - 220), (cx + 60, cy - 40), (cx + 150, cy - 40),
                   (cx, cy + 110), (cx - 150, cy - 40), (cx - 60, cy - 40)], fill=gelb)
        d.rounded_rectangle((cx - 230, cy + 140, cx + 230, cy + 220), 16, fill=hell)
    elif art == 'daten':
        for k, x in enumerate((cx - 260, cx, cx + 260)):
            y = cy - 150 + (k % 2) * 40
            d.ellipse((x - 90, y - 35, x + 90, y + 35), fill=hell)
            d.rectangle((x - 90, y, x + 90, y + 130), fill=hell)
            d.ellipse((x - 90, y + 95, x + 90, y + 165), fill='#b8c6d2')
            d.line((x, y + 170, cx, cy + 190), fill=gelb, width=12)
        d.rounded_rectangle((cx - 120, cy + 170, cx + 120, cy + 250), 18, fill=tuerkis)
        txt(cx - 70, cy + 188, 'APP', 40, '#10202d')
    elif art == 'warnung':
        d.polygon([(cx, cy - 230), (cx + 230, cy + 170), (cx - 230, cy + 170)], fill=gelb)
        d.rectangle((cx - 18, cy - 110, cx + 18, cy + 60), fill='#10202d')
        d.ellipse((cx - 22, cy + 85, cx + 22, cy + 129), fill='#10202d')
    else:
        for k, h in enumerate((140, 260, 200, 330)):
            d.rectangle((cx - 230 + k * 120, cy + 200 - h, cx - 150 + k * 120, cy + 200), fill=(tuerkis, gelb)[k % 2])
        d.line((cx - 260, cy + 205, cx + 260, cy + 205), fill=hell, width=8)
    # Beschriftungen nebeneinander und umbrechend: alles bis y ~1250, dem sichtbaren Pruefausschnitt.
    x, y = 75, 1030
    for name in begriffe(text, motiv)[:4]:
        breite = d.textlength(name, font=font(40)) + 60
        if x + breite > 1005:
            x, y = 75, y + 95
        if y > 1160:
            break
        d.rounded_rectangle((x, y, x + breite, y + 70), 16, fill='#13283d', outline=gelb, width=4)
        txt(x + 30, y + 12, name, 40, gelb)
        x += breite + 24
    txt(75, 1500, 'EXPLAINER GRAPHIC', 25, '#8dabbf')
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    im.save(ziel, 'JPEG', quality=93)
    return Path(ziel)
