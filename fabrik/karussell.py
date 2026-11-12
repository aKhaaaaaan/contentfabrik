"""TikTok-Bilderkarussell aus dem zuletzt gelieferten Short (Nutzer 07.11./12.11.2026: beide Kanaele, alle zwei Tage,
Bilder von Codex, erste zwei vorher zeigen).

Die Bilder malt Codex auf dem PC des Nutzers (privater Helfer, Abo-Login bleibt lokal). Dieses Modul ist der
oeffentliche Teil:
- folien_pruefen: Folientext darf nur aus dem bereits faktengeprueften Sprechtext stammen (keine neuen Zahlen,
  keine neuen Behauptungen) - "Nie Fakten erfinden".
- rendern: Text legen WIR auf das Bild (gemalte KI-Schrift lehnen Pruefer und Nutzer seit Wochen ab).
- senden: als Telegram-Album; TikTok-Fotobeitraege per API brauchen eine verifizierte Domain (PULL_FROM_URL),
  bis dahin postet der Nutzer das Album selbst.

Aufruf (GitHub, karussell.yml): python fabrik/karussell.py senden <ordner>
"""
import json
import os
import re
import sys
import uuid
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHRIFT = ROOT / 'schriften' / 'Anton-Regular.ttf'
KLEIN = ROOT / 'schriften' / 'Montserrat-ExtraBold.ttf'
BREITE, HOEHE = 1080, 1350  # 4:5 - TikTok-Fotobeitraege zeigen Hochformat 4:5 ohne Beschnitt durch die Bedienleiste
MIN_FOLIEN, MAX_FOLIEN = 4, 7
MAX_ZEICHEN = 110
FUELL = set('a an the of to and or in on at for is was were be by with as it its this that his her their our '
            'your you we he she they so but if then than from into one'.split())
SCHLUSS = 'Full story in our video'


def _woerter(text):
    return re.findall(r"[a-z0-9]+(?:['’][a-z]+)?", text.lower().replace('’', "'"))


def _zahlen(text):
    return {z.replace(',', '') for z in re.findall(r'\d[\d,.]*\d|\d', text)}


def folien_pruefen(folien, skripttext):
    """Liste der Probleme (leer = ok). Jede Folie: Zahlen nur aus dem Skript, >= 75 % der Inhaltswoerter aus dem
    Skript, kurz genug zum Lesen. Die letzte Folie darf der feste Verweis aufs Video sein."""
    fehler = []
    if not MIN_FOLIEN <= len(folien) <= MAX_FOLIEN:
        fehler.append(f'{len(folien)} Folien, erlaubt {MIN_FOLIEN}-{MAX_FOLIEN}')
    skript_woerter = set(_woerter(skripttext))
    skript_zahlen = _zahlen(skripttext)
    for i, f in enumerate(folien, 1):
        text = (f.get('text') or '').strip()
        if not text:
            fehler.append(f'Folie {i}: leer')
            continue
        if text == SCHLUSS:
            continue
        if len(text) > MAX_ZEICHEN:
            fehler.append(f'Folie {i}: {len(text)} Zeichen (max {MAX_ZEICHEN})')
        neu = _zahlen(text) - skript_zahlen
        if neu:
            fehler.append(f'Folie {i}: Zahl nicht im Skript: {", ".join(sorted(neu))}')
        inhalt = [w for w in _woerter(text) if w not in FUELL]
        fremd = [w for w in inhalt if w not in skript_woerter]
        if inhalt and len(fremd) / len(inhalt) > 0.25:
            fehler.append(f'Folie {i}: Woerter nicht im Skript: {", ".join(fremd)}')
    return fehler


def _umbrechen(text, font, breite):
    zeilen, zeile = [], ''
    for wort in text.split():
        probe = f'{zeile} {wort}'.strip()
        if font.getlength(probe) <= breite or not zeile:
            zeile = probe
        else:
            zeilen.append(zeile)
            zeile = wort
    return zeilen + ([zeile] if zeile else [])


def rendern(bild, text, ziel, nummer, gesamt, kanal=''):
    """Bild auf 4:5 zuschneiden, unten abdunkeln, Text gross darauf (wie die Untertitel: Anton, weiss, Kontur)."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(bild).convert('RGB')
    skala = max(BREITE / im.width, HOEHE / im.height)
    im = im.resize((round(im.width * skala), round(im.height * skala)), Image.LANCZOS)
    links, oben = (im.width - BREITE) // 2, max(0, (im.height - HOEHE) // 3)
    im = im.crop((links, oben, links + BREITE, oben + HOEHE))
    verlauf = Image.new('L', (1, HOEHE))
    for y in range(HOEHE):
        verlauf.putpixel((0, y), int(215 * max(0, (y - HOEHE * 0.45) / (HOEHE * 0.55)) ** 1.3))
    im.paste(Image.new('RGB', im.size, (0, 0, 0)), mask=verlauf.resize(im.size))
    d = ImageDraw.Draw(im)
    groesse = 92 if nummer == 1 else 74
    while True:
        font = ImageFont.truetype(str(SCHRIFT), groesse)
        zeilen = _umbrechen(text.upper(), font, BREITE - 140)
        if len(zeilen) <= 4 or groesse <= 52:
            break
        groesse -= 6
    zeilenhoehe = int(groesse * 1.12)
    y = HOEHE - 120 - zeilenhoehe * len(zeilen)
    for z in zeilen:
        x = (BREITE - font.getlength(z)) / 2
        d.text((x, y), z, font=font, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
        y += zeilenhoehe
    klein = ImageFont.truetype(str(KLEIN), 30)
    d.text((BREITE - 70, HOEHE - 62), f'{nummer}/{gesamt}', font=klein, fill=(255, 255, 255), anchor='rs',
           stroke_width=2, stroke_fill=(0, 0, 0))
    if kanal:
        d.text((70, HOEHE - 62), kanal, font=klein, fill=(255, 210, 90), anchor='ls', stroke_width=2,
               stroke_fill=(0, 0, 0))
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    im.save(ziel, 'JPEG', quality=90)
    return ziel


def bauen(ordner, skripttext=None):
    """ordner/karussell.json {kanal, titel, folien:[{text, bild}]} -> fertige Folien ordner/folie<i>.jpg."""
    ordner = Path(ordner)
    plan = json.loads((ordner / 'karussell.json').read_text(encoding='utf-8'))
    if skripttext is None:
        skripttext = plan.get('skript', '')
    fehler = folien_pruefen(plan['folien'], skripttext)
    if fehler:
        raise ValueError('Karussell gesperrt: ' + '; '.join(fehler))
    fertig = []
    for i, f in enumerate(plan['folien'], 1):
        fertig.append(rendern(ordner / f['bild'], f['text'], ordner / f'folie{i}.jpg', i, len(plan['folien']),
                              plan.get('kanalname', '')))
    return plan, fertig


HASHTAGS = {'Business Origin Stories': '#businesshistory #entrepreneur #founderstory #history',
            'AI Tools Explained': '#ai #aitools #tech #techtips'}


def beschreibung(plan):
    """Kopiertext fuer TikTok (Nutzer 12.11.: "wie poste ich die genau?"): Folie 1 als Hook - kein neuer Fakt -,
    Verweis aufs Video, Kanal-Hashtags + ein Themen-Hashtag."""
    if plan.get('hashtags'):  # 12.11.: dieselben Tags wie das Video, inkl. gemessener Trend-Hashtags
        tags = ' '.join('#' + str(t).lstrip('#') for t in plan['hashtags'])
        return f"{plan['folien'][0]['text']} Full story in our video.\n\n{tags}".strip()
    thema = re.sub(r'[^A-Za-z0-9]', '', (plan.get('thema') or '').split(':')[0])[:30].lower()
    tags = ' '.join(t for t in [HASHTAGS.get(plan.get('kanalname', ''), ''), f'#{thema}' if thema else ''] if t)
    return f"{plan['folien'][0]['text']} Full story in our video.\n\n{tags}".strip()


def senden(plan, dateien):
    token, chat = os.environ['TELEGRAM_BOT_TOKEN'], os.environ['TELEGRAM_CHAT_ID']
    grenze = uuid.uuid4().hex
    medien = [{'type': 'photo', 'media': f'attach://f{i}'} for i in range(len(dateien))]
    medien[0]['caption'] = (f"🖼 Karussell-Entwurf {plan.get('kanalname', '')}: {plan.get('titel', '')}\n"
                            'In TikTok als Fotobeitrag posten (Text liegt schon auf den Bildern).')[:1000]
    teile = [f'--{grenze}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
             for k, v in {'chat_id': chat, 'media': json.dumps(medien, ensure_ascii=False)}.items()]
    for i, pfad in enumerate(dateien):
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="f{i}"; filename="f{i}.jpg"\r\n'
                     'Content-Type: image/jpeg\r\n\r\n'.encode() + Path(pfad).read_bytes() + b'\r\n')
    teile.append(f'--{grenze}--\r\n'.encode())
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMediaGroup', data=b''.join(teile),
                                 headers={'Content-Type': f'multipart/form-data; boundary={grenze}'})
    antwort = json.load(urllib.request.urlopen(req, timeout=120))
    if not antwort.get('ok'):
        raise RuntimeError(f"Telegram: {antwort.get('description')}")
    text = plan.get('beschreibung') or beschreibung(plan)
    if text:
        req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',
                                     data=json.dumps({'chat_id': chat, 'text': text[:4000]}).encode(),
                                     headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=60)
    return antwort


def main(argv):
    if len(argv) != 3 or argv[1] not in ('bauen', 'senden'):
        sys.exit('Aufruf: karussell.py bauen|senden <ordner>')
    plan, dateien = bauen(argv[2])
    print(f'{len(dateien)} Folien gebaut: {plan.get("titel", "")}')
    if argv[1] == 'senden':
        senden(plan, dateien)
        print('Telegram-Album gesendet')


if __name__ == '__main__':
    main(sys.argv)
