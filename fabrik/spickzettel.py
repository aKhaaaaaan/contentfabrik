"""Spickzettel zum Abfotografieren im Schlussbild (Werkzeug-Kanaele).

Nutzer 30.10.2026 ("Ja mach das"), Vorbild TikTok @brandnat: eine "Screenshot this"-Tafel mit den 3 Werkzeugen
-> 14.175 Speicherungen bei 128.600 Aufrufen (11 %); unsere Videos werden fast nie gespeichert. Das Schlussbild
spricht ohnehin "like, share and SAVE" - dort steht jetzt die Kurzfassung des Videos.

Fakten: Die Zeilen fasst die KI NUR aus dem gesprochenen Text zusammen; jede Zahl und fast jedes Inhaltswort muss
im Sprechtext stehen, sonst faellt die Zeile weg. Unter zwei Zeilen bleibt das bisherige Schlussbild.
"""
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCHRIFT = Path(__file__).resolve().parents[1] / 'schriften/Montserrat-ExtraBold.ttf'
ZEICHEN = 34  # je Zeile; bei 1080 px und 50 pt passt das ohne Umbruch
SCHEMA = {'type': 'OBJECT', 'properties': {'zeilen': {'type': 'ARRAY', 'items': {'type': 'STRING'}}},
          'required': ['zeilen']}


def erzaehlung(skript):
    import texte
    return ' '.join(str(t.get('text', '')) for t in skript.get('teile') or [] if not texte.AUFRUF.search(str(t.get('text', ''))))


def _woerter(text):
    return {w.rstrip('s') for w in re.findall(r'[a-z0-9]+', str(text).lower()) if len(w) >= 4}


def belegt(zeile, gesprochen):
    """Jede Zahl woertlich im Sprechtext, mindestens 80 % der Inhaltswoerter ebenso."""
    zahlen = re.findall(r'\d[\d,.]*', zeile)
    if any(z.rstrip('.,') not in gesprochen for z in zahlen):
        return False
    w = _woerter(zeile)
    return bool(w) and len(w & _woerter(gesprochen)) >= 0.8 * len(w)


def quelle(skript):
    """github.com/owner/repo bzw. huggingface.co/... aus der ersten Projektquelle - das wollen Leute abfotografieren."""
    for t in skript.get('teile') or []:
        m = re.match(r'https?://(?:www\.)?((?:github\.com|huggingface\.co)/[^/\s?#]+/[^/\s?#]+)', str(t.get('quelle_url') or ''))
        if m:
            return m.group(1)[:44]
    return ''


def auftrag(gesprochen, werkzeug):
    import prompts
    return (prompts.DATEN + 'TASK: Write a cheat sheet a viewer screenshots at the end of this short video about '
            f'{werkzeug or "the topic"}. 3 lines, each at most {ZEICHEN} characters: what it does, how to start or '
            'the key step, and the main cost, limit or catch. Each line is a practical takeaway the viewer can act '
            'on - never a joke, metaphor or the story example. Use ONLY facts and wording from the narration below - '
            'no new facts, numbers, names or claims. Plain text, no emojis, no hashtags.\nNARRATION: '
            + json.dumps(gesprochen, ensure_ascii=False))


def zeilen(skript, ablage=None, ki=None):
    """Belegte Zeilen (0-3). ablage: JSON-Datei, damit Korrekturrunden nicht erneut fragen."""
    gesprochen = erzaehlung(skript)
    werkzeug = next((str(t.get('werkzeug')) for t in skript.get('teile') or [] if t.get('werkzeug')), '') \
        or str(skript.get('thema') or '')
    schluessel = __import__('hashlib').sha256(gesprochen.encode()).hexdigest()[:16]
    if ablage and Path(ablage).exists():
        try:
            alt = json.loads(Path(ablage).read_text(encoding='utf-8'))
            if alt.get('schluessel') == schluessel:
                return alt['zeilen']
        except (OSError, ValueError, KeyError):
            pass
    if ki is None:
        from skript import gemini, MODELLE

        def ki(prompt):
            return gemini(prompt, SCHEMA, temperatur=0.2, modelle=MODELLE)[0]
    antwort = ki(auftrag(gesprochen, werkzeug))
    roh = [re.sub(r'\s+', ' ', str(z)).strip(' -•*') for z in (antwort or {}).get('zeilen') or []]
    gut = [z for z in roh if 0 < len(z) <= ZEICHEN and belegt(z, gesprochen)][:3]
    print(f'Spickzettel: {len(gut)} von {len(roh)} Zeilen belegt', [z for z in roh if z not in gut])
    if ablage:
        Path(ablage).write_text(json.dumps({'schluessel': schluessel, 'zeilen': gut}, ensure_ascii=False),
                                encoding='utf-8')
    return gut


def bild(ziel, figur, kopf, punkte, adresse='', zusatz=''):
    """1080x1920: Tafel "SCREENSHOT THIS" oben, Kanalfigur unten; Kommentarfrage klein in Kanalfarbe."""
    im = Image.new('RGB', (1080, 1920), '#10202d')
    with Image.open(figur) as f:
        im.paste(f.convert('RGB').resize((1080, 1080)), (0, 840))
    d = ImageDraw.Draw(im)

    def font(n):
        return ImageFont.truetype(str(SCHRIFT), n)

    def passend(text, n, breite=880):
        while d.textlength(text, font=font(n)) > breite and n > 26:
            n -= 2
        return n

    unten = 470 + len(punkte) * 92 + (70 if adresse else 0) + (70 if zusatz else 0)
    d.rounded_rectangle((60, 230, 1020, unten), 40, fill='white')
    d.text((100, 262), 'SCREENSHOT THIS', font=font(40), fill='#0f8f82')
    titel = str(kopf).upper()[:30]
    d.text((100, 320), titel, font=font(passend(titel, 64)), fill='#10202d')
    y = 420
    for p in punkte:
        d.ellipse((104, y + 18, 124, y + 38), fill='#20d2be')
        d.text((146, y), p, font=font(passend(p, 50, 830)), fill='#10202d')
        y += 92
    if adresse:
        d.text((100, y + 8), adresse, font=font(passend(adresse, 40)), fill='#3a5a70')
        y += 70
    if zusatz:
        d.text((100, y + 8), zusatz, font=font(passend(zusatz, 40)), fill='#0f8f82')
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    im.save(ziel, 'JPEG', quality=93)
    return Path(ziel)
