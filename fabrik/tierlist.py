"""Tierlist-Format fuer den KI-Kanal (Nutzer 31.10.2026, Pilot 1x/Woche).

Vorbild: TikTok @howto.print "What is the BEST side hustle of 2026?" - eine Rangliste F bis S, die sich Stufe fuer
Stufe fuellt; S kommt zuletzt, Zuschauer bleiben bis zum Ende und widersprechen in den Kommentaren.
Das Skript beginnt jeden Rangabschnitt mit "<Stufe> tier: <Name>." (prompts.skript). Diese Grafik zeigt die Tafel
mit allen bisher genannten Eintraegen; der aktuelle Rang ist hervorgehoben. Wichtiges liegt in Grafik-y 300-1270:
nur diesen Ausschnitt sieht der Bildpruefer (Dauerregel 4)."""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCHRIFT = Path(__file__).resolve().parents[1] / 'schriften/Montserrat-ExtraBold.ttf'
STUFEN = ['S', 'A', 'B', 'C', 'F']
FARBEN = {'S': '#e8453c', 'A': '#f39a2b', 'B': '#f4cf3a', 'C': '#3fbf5f', 'F': '#d94fd0'}
RANG = re.compile(r'^\s*([SABCF])[- ]tier\b[\s:,.!-]*', re.I)
THEMA = re.compile(r'\btier ?list\b|\branked (?:from )?F to S\b', re.I)


def stufe(text):
    """'S'...'F', wenn der Abschnitt mit "<Stufe> tier" beginnt, sonst None."""
    m = RANG.match(text or '')
    return m.group(1).upper() if m else None


def name(text):
    """Eintrag hinter "<Stufe> tier:" bis zum ersten Satzende (hoechstens 28 Zeichen)."""
    rest = RANG.sub('', text or '', count=1)
    return re.split(r'(?<=[^\s.])[.!?;](?:\s|$)|,\s', rest, maxsplit=1)[0].strip()[:28]


def stand(teile, bis):
    """[(Stufe, Name)] aller Rangabschnitte bis einschliesslich Abschnitt bis."""
    return [(stufe(t.get('text')), name(t.get('text'))) for t in teile[:bis + 1] if stufe(t.get('text'))]


def bild(ziel, eintraege, aktuell, titel=''):
    """1080x1920-Tafel S..F mit den genannten Eintraegen; aktueller Rang gross oben und umrandet."""
    im = Image.new('RGB', (1080, 1920), '#121418')
    d = ImageDraw.Draw(im)

    def font(n):
        return ImageFont.truetype(str(SCHRIFT), n)

    def passend(text, n, breite):
        while d.textlength(text, font=font(n)) > breite and n > 24:
            n -= 2
        return n

    if titel:
        t = str(titel).upper()[:34]
        d.text((540, 150), t, font=font(passend(t, 56, 960)), fill='white', anchor='mm')
    kopf = f'{aktuell} TIER'
    d.text((540, 250), kopf, font=font(72), fill=FARBEN.get(aktuell, 'white'), anchor='mm')
    zeile, oben, links, rechts = 180, 340, 60, 1020
    for k, s in enumerate(STUFEN):
        y = oben + k * zeile
        d.rectangle((links, y, links + 170, y + zeile - 12), fill=FARBEN[s])
        d.text((links + 85, y + (zeile - 12) // 2), s, font=font(96), fill='#121418', anchor='mm')
        d.rectangle((links + 182, y, rechts, y + zeile - 12), fill='#23272e')
        namen = [n for st, n in eintraege if st == s]
        text = ' · '.join(namen)
        if text:
            d.text((links + 210, y + (zeile - 12) // 2), text, anchor='lm',
                   font=font(passend(text, 54 if s == aktuell else 46, rechts - links - 240)),
                   fill='white' if s == aktuell else '#b8bec8')
        if s == aktuell:
            d.rectangle((links - 8, y - 8, rechts + 8, y + zeile - 4), outline='white', width=8)
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    im.save(ziel, 'JPEG', quality=92)
    return Path(ziel)
