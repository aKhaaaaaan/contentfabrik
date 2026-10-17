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
    ('warnung', r'\b(catch|risk|warning|not financial advice|careful|limitation)\b'),
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


FUELL = {'the', 'a', 'an', 'its', 'it', 'your', 'their', 'our', 'this', 'that', 'these', 'those', 'can', 'will',
         'would', 'may', 'might', 'should', 'must', 'is', 'are', 'was', 'be', 'then', 'first', 'so', 'also', 'just',
         'something', 'any', 'each', 'every', 'some', 'ones'}
TRENNER = (r'[,;:.?!](?=\s|$)|\b(?:and|or|with|only|but|so|from|to|for|like|including|across|via|into|on|without|not'
           r'|can|will|would|may|might|should|must)\b')
JAHR = r'(?:19|20)\d\d'


def phrasen(text, n=4):
    """Kurze Sachbegriffe des Satzes, in Satzreihenfolge: je Satzglied die letzten (bis zu) 3 Woerter ohne
    Fuellwoerter ("... cite the fetched Guide, naming a reviewer ... with a published review record" ->
    FETCHED GUIDE, NAMING A REVIEWER, PUBLISHED REVIEW RECORD). Nur gesprochene Woerter, nichts erfunden."""
    aus = []
    for teil in re.split(TRENNER, text, flags=re.I):
        w = re.findall(r"[A-Za-z0-9$+'-]+(?:[.,]\d+)*", teil or '')[-4:]
        while w and w[0].lower() in FUELL:
            w.pop(0)
        while w and w[-1].lower() in FUELL:
            w.pop()
        p = ' '.join(w).upper()
        if len(p) > 2 and p not in aus:
            aus.append(p)
    return aus[:n]


def zahlen(text):
    """Gesprochene Mengen mit Bezugswort ("1,903 Guides" -> 1,903 GUIDES); Jahreszahlen zaehlen nicht."""
    aus = []
    for m in re.finditer(r"(\$?\d[\d,.]*\d|\$?\d)(-plus|\+)?\s+([A-Za-z][A-Za-z'-]*)(?:\s+([A-Za-z][A-Za-z'-]*))?", text):
        if re.fullmatch(JAHR, m[1]):
            continue
        woerter = [x for x in (m[3], m[4]) if x and x.lower() not in FUELL | {'and', 'or', 'across', 'in', 'of'}]
        if m[4] and m[4].lower() in FUELL | {'and', 'or', 'across', 'in', 'of'}:
            woerter = woerter[:1]
        aus.append((m[1] + ('+' if m[2] else ''), ' '.join(woerter or [m[3]]).upper()))
    return aus[:3]


def layout(text, phase=''):
    """Teilsatz ohne eigenen Vorgang erbt den Aufbau seines gesprochenen Abschnitts.

    GEMESSEN 16.10.2026 (Groq, Schlusspruefer-Auftrag): "Florida's combined sales tax rate for 2026." setzt die
    Frage "Then ask something it would guess, like Manatee County," fort - als Schlagzeilenkarte 5/10."""
    art = _layout(text)
    if art == 'kernsatz' and phase and phase.strip() != text.strip():
        geerbt = _layout(phase)
        if geerbt in ('frage', 'zitat', 'vergleich', 'warnung'):
            return geerbt
    return art


def _layout(text):
    """Bildaufbau aus dem Inhalt des Satzes. GEMESSEN 16.10.2026 (OpenAccountants, Lauf 38888929052): Es gab
    nur Datenbank-Symbol oder Balken mit erfundenen Werten; 5 von 9 Grafiken sahen gleich aus, der Pruefer
    lehnte "Zitat eines Guides" (4/10) und "keine Finanzberatung" (2/10) ab. Jetzt zeigt jede Grafik den
    Vorgang des Satzes: Frage -> Chat, Zitat -> Antwort mit Quellenkarte, Zahlen -> Zahlenkacheln usw."""
    t = text.lower()
    art = symbol(text)
    if art in ('schluessel', 'rechnung', 'download'):
        return art
    if re.search(r"financial advice|outdated|\bwrong\b|\brisks?\b|warning|careful|\bverify\b|double-check", t):
        return 'warnung'
    if zahlen(text):
        return 'zahlen'
    if text.strip().endswith('?') or re.search(r'\b(ask|asks|asking|question)\b', t):
        return 'frage'
    if re.search(r'\b(cite|cites|citing|citation|reviewer|answer|answers|replies|quote)\b', t):
        return 'zitat' if not re.search(r'\bnot from\b|\binstead of\b|\brather than\b', t) else 'vergleich'
    if re.search(r'\bnot from\b|\binstead of\b|\brather than\b|\bvs\.?\s|, not\b', t):
        return 'vergleich'
    if re.search(r'\b(connect|connector|connects|plug|plugin|integrat\w*|mcp)\b|\badd\b.*\bto\b', t):
        return 'verbinden'
    if art in ('daten', 'warnung'):
        return art
    return 'kernsatz'


def titelzeile(titel):
    """'openaccountants/openaccountants' -> OPENACCOUNTANTS (war abgeschnitten: OPENACCOUNTANTS/OPENACCOUNTA)."""
    teile = [x for x in str(titel or '').split('/') if x.strip()]
    return (teile[-1] if teile else 'HOW IT WORKS').strip().upper()


def figur_frage(ziel, figur, text, titel='', zusatz=''):
    """Einstieg: gemalte Kanalfigur mit Sprechblase, darin der gesprochene Satz.

    GEMESSEN 16.10.2026 (KI-Lauf 38888929052): Das gemalte Einstiegsbild scheiterte fuenfmal (2x Cloudflare
    "flagged", 3x Nahaufnahme/falsche Pose); als Ersatz kam die Grafik der naechsten Einstellung doppelt
    (Pruefer 6/10). Die Figur allein bekam 2/10 ("keine Beziehung zur Frage"). Figur + woertliche Frage
    zeigt beides - ohne Cloudflare und ohne Gemini-Bildpruefung."""
    im = Image.new('RGB', (1080, 1920), '#10202d')
    with Image.open(figur) as f:
        f = f.convert('RGB').resize((1080, 1080))
        im.paste(f, (0, 640))
    d = ImageDraw.Draw(im)
    def font(n):
        return ImageFont.truetype(str(SCHRIFT), n)
    satz = re.sub(r'\s+', ' ', str(text)).strip()
    n = 58
    def zeilen_fuer(n):
        zeilen, z = [], ''
        for w in satz.split():
            if z and d.textlength(z + ' ' + w, font=font(n)) > 860:
                zeilen.append(z)
                z = w
            else:
                z = (z + ' ' + w).strip()
        return zeilen + ([z] if z else [])
    zeilen = zeilen_fuer(n)
    while len(zeilen) * (n + 16) > 250 and n > 30:
        n -= 4
        zeilen = zeilen_fuer(n)
    # Zusatz (17.10.2026, Kommentarfrage beim Aufruf): nur sichtbar, kleiner, in Kanalfarbe unter dem Satz.
    nz = 44
    while zusatz and d.textlength(zusatz, font=font(nz)) > 860 and nz > 26:
        nz -= 2
    extra = (nz + 40) if zusatz else 0
    unten = 330 + 50 + len(zeilen) * (n + 16) + extra
    d.rounded_rectangle((60, 330, 1020, unten), 40, fill='white')
    d.polygon([(480, unten - 2), (600, unten - 2), (560, unten + 70)], fill='white')
    for k, z in enumerate(zeilen):
        d.text((100, 355 + k * (n + 16)), z, font=font(n), fill='#10202d')
    if zusatz:
        d.text((100, 355 + len(zeilen) * (n + 16) + 24), zusatz, font=font(nz), fill='#0f8f82')
    if titel:
        kopf = titelzeile(titel)
        d.text((75, 250), kopf, font=font(36), fill='#20d2be')
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    im.save(ziel, 'JPEG', quality=93)
    return Path(ziel)


def grafik(ziel, text, motiv='', titel='', phase='', art=None):
    im = Image.new('RGB', (1080, 1920), '#10202d')
    d = ImageDraw.Draw(im)
    def font(n):
        return ImageFont.truetype(str(SCHRIFT), n)
    def txt(x, y, s, n=40, farbe='#edf6ff'):
        d.text((x, y), s, font=font(n), fill=farbe)
    def passend(s, breite, n):
        while n > 22 and d.textlength(s, font=font(n)) > breite:
            n -= 2
        return n
    def umbruch(s, breite, n):
        zeilen, z = [], ''
        for w in s.split():
            if z and d.textlength(z + ' ' + w, font=font(n)) > breite:
                zeilen.append(z)
                z = w
            else:
                z = (z + ' ' + w).strip()
        return zeilen + ([z] if z else [])
    def blase(x0, y0, x1, s, n, fuell, farbe):
        zeilen = umbruch(s, x1 - x0 - 60, n)[:4]
        y1 = y0 + 44 + len(zeilen) * (n + 14)
        d.rounded_rectangle((x0, y0, x1, y1), 34, fill=fuell)
        for k, z in enumerate(zeilen):
            txt(x0 + 30, y0 + 22 + k * (n + 14), z, n, farbe)
        return y1
    gelb, tuerkis, hell, dunkel, rot = '#ffae35', '#20d2be', '#dce4ec', '#10202d', '#ff5a5f'
    kopf = titelzeile(titel)
    txt(75, 315, kopf, passend(kopf, 930, 40), tuerkis)
    art = art or layout(text, phase)
    satz = re.sub(r'\s+', ' ', str(text)).strip()
    cx, cy = 540, 760
    beschriften = art in ('schluessel', 'rechnung', 'download', 'daten')
    if not beschriften:
        pass
    elif art in ('schluessel', 'download', 'daten', 'rechnung'):
        for k, zeile in enumerate(textwrap.wrap(str(motiv or text).upper(), 24)[:2]):
            txt(75, 380 + k * 52, zeile, 44)
    if art == 'schluessel':
        d.ellipse((cx - 230, cy - 90, cx - 50, cy + 90), outline=gelb, width=28)
        d.rectangle((cx - 60, cy - 18, cx + 230, cy + 18), fill=gelb)
        for x in (cx + 120, cx + 190):
            d.rectangle((x, cy + 18, x + 30, cy + 80), fill=gelb)
    elif art == 'rechnung':
        # Eichung 15.10.2026: Rechnung nur mit $-Zeichen galt als Metapher (3/10). Abrechnungslogik
        # zeigen - Posten statt erfundener Betraege.
        d.rounded_rectangle((cx - 300, cy - 230, cx + 300, cy + 230), 20, fill=hell)
        txt(cx - 250, cy - 200, 'LLM BILL', 44, dunkel)
        for k, posten in enumerate(('INPUT TOKENS  x  PRICE', 'OUTPUT TOKENS  x  PRICE')):
            txt(cx - 250, cy - 90 + k * 90, posten, 34, dunkel)
        d.rectangle((cx - 250, cy + 95, cx + 250, cy + 103), fill=dunkel)
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
        txt(cx - 70, cy + 188, 'APP', 40, dunkel)
    elif art == 'warnung':
        handlung = re.search(r'\b(check|verify|review|confirm|double-check|compare)\b\s+(.+)', satz, re.I)
        if handlung:
            # Warnung MIT Handlung ("may be outdated or wrong, so check each review record"): Groq 16.10.2026
            # gab der reinen Textkarte 4/10 ("nur Text-Overlay"). Jetzt sieht man den Vorgang: Dokumentkarte
            # mit den gesprochenen Zweifeln als Stempel, darunter die abgehakte Pruefung.
            zweifel = [w.upper() + '?' for w in re.findall(
                r'\b(outdated|wrong|incomplete|inaccurate|stale|old|risky|biased|unverified)\b', satz, re.I)][:2]
            subjekt = (phrasen(satz.split(',')[0], 1) or [kopf])[0].split(' MAY ')[0].split(' CAN ')[0]
            d.rounded_rectangle((150, 400, 930, 840), 22, fill=hell)
            txt(195, 430, subjekt[:22], passend(subjekt[:22], 520, 44), dunkel)
            for k, b in enumerate((620, 560, 640, 480)):
                d.rounded_rectangle((195, 510 + k * 70, 195 + b, 540 + k * 70), 10, fill='#9fb0bf')
            for k, w in enumerate(zweifel or ['?']):
                x0, y0 = 560 - k * 300, 600 + k * 120
                breite = d.textlength(w, font=font(52)) + 60
                d.rounded_rectangle((x0, y0, x0 + breite, y0 + 95), 14, outline=rot, width=8)
                txt(x0 + 30, y0 + 16, w, 52, rot)
            pruefung = handlung[0].strip(' .').upper()
            d.rounded_rectangle((75, 900, 1005, 1100), 24, fill='#13283d', outline=tuerkis, width=6)
            d.rounded_rectangle((110, 950, 200, 1040), 14, fill=tuerkis)
            d.line((128, 995, 150, 1020, 185, 965), fill=dunkel, width=12)
            zeilen = umbruch(pruefung, 760, passend(pruefung, 1520, 46))
            for k, z in enumerate(zeilen[:2]):
                txt(230, 945 + k * 60, z, 46 if len(zeilen) > 1 else passend(z, 760, 52), tuerkis)
            art = 'warnung_erledigt'
    if art == 'warnung':
        # Warnsatz woertlich unter dem Warnzeichen - der Pruefer verlangte "Haftungsausschluss/Warnhinweis".
        d.polygon([(cx, 400), (cx + 170, 690), (cx - 170, 690)], fill=gelb)
        d.rectangle((cx - 14, 490, cx + 14, 620), fill=dunkel)
        d.ellipse((cx - 17, 640, cx + 17, 674), fill=dunkel)
        d.rounded_rectangle((75, 740, 1005, 1250), 26, fill='#2a1d12', outline=gelb, width=5)
        n = 56
        zeilen = umbruch(satz.upper(), 860, n)
        while len(zeilen) * (n + 18) > 440 and n > 30:
            n -= 4
            zeilen = umbruch(satz.upper(), 860, n)
        for k, z in enumerate(zeilen):
            txt(110, 780 + k * (n + 18), z, n, gelb)
    elif art == 'zahlen':
        # Gesprochene Zahlen mit Bezugswort als grosse Kacheln - keine erfundenen Werte.
        werte = zahlen(text)
        hoehe = min(300, (850 - 30 * (len(werte) - 1)) // len(werte))
        for k, (zahl, wort) in enumerate(werte):
            y = 400 + k * (hoehe + 30)
            farbe = (gelb, tuerkis, hell)[k % 3]
            d.rounded_rectangle((75, y, 1005, y + hoehe), 26, fill='#13283d', outline=farbe, width=5)
            nz = passend(zahl, 860, min(140, hoehe - 110))
            txt(115, y + 18, zahl, nz, farbe)
            txt(115, y + 36 + nz, wort, passend(wort, 860, 46), hell)
        rest = [p for p in phrasen(text) if not any(z in p for z, _ in werte)]
        if rest and len(werte) == 1:
            y = 400 + hoehe + 40
            d.rounded_rectangle((75, y, 1005, y + 150), 26, fill='#13283d', outline=tuerkis, width=5)
            txt(115, y + 45, rest[-1], passend(rest[-1], 860, 50), tuerkis)
    elif art == 'frage':
        # Chatfenster: die gesprochene Frage als Nutzer-Nachricht, die KI ist unsicher ("guessing").
        d.rounded_rectangle((75, 400, 1005, 1250), 30, fill='#0b1620', outline='#2b4258', width=4)
        txt(115, 425, 'AI CHAT', 32, '#8dabbf')
        frage = satz if satz.endswith('?') else re.split(r'\b(?:like|ask|asks|asking)\b', satz, flags=re.I)[-1]
        ist_frage = satz.endswith('?') or re.search(r'\b(?:like|ask|asks|asking)\b', satz, re.I)
        frage = re.sub(r'^(?:whether|if)\s+', '', frage.strip(' ,.'), flags=re.I)
        frage = frage + ('?' if ist_frage and not frage.endswith('?') else '' if ist_frage else '.')
        # GEMESSEN 17.10.2026 (Talorys, Lauf 39017190861): "Talorys asks whether the old one is now a past
        # fact" und der Satz davor zeigten dieselbe Grafik mit der festen Antwort "I am guessing" - erfunden
        # und hier falsch (das Tool fragt nach, es raet nicht). Fragt das Werkzeug, steht die Frage links als
        # KI-Nachricht; die Rate-Antwort nur, wenn der Satz vom Raten spricht.
        fragt = re.search(r'\b(\w+)\s+(?:asks|asked|will ask)\b', satz, re.I)
        ki_fragt = bool(fragt) and (fragt[1].lower() in ('it', 'ai', 'assistant', 'agent', 'bot', 'model', 'app')
                                    or fragt[1].lower() in str(titel).lower())
        if ki_fragt:
            y = blase(105, 500, 860, frage[:1].upper() + frage[1:], 42, '#22384d', hell)
            y = blase(560, y + 50, 975, '...', 42, tuerkis, dunkel)
        else:
            y = blase(300, 500, 975, frage[:1].upper() + frage[1:], 42, tuerkis, dunkel)
            if re.search(r'\bguess\w*|\bhallucinat\w*|\bmakes? (?:it|things) up\b|\bunsure\b', phase or satz, re.I):
                y = blase(105, y + 50, 760, 'Hmm... probably? I am guessing.', 40, '#22384d', hell)
            for k in range(3):
                d.ellipse((140 + k * 50, y + 40, 170 + k * 50, y + 70), fill='#8dabbf')
    elif art == 'zitat':
        # Antwort mit sichtbarer Quellenkarte: Vorgang "Antwort zitiert Quelle/Pruefer".
        d.rounded_rectangle((75, 400, 1005, 1250), 30, fill='#0b1620', outline='#2b4258', width=4)
        txt(115, 425, 'AI ANSWER', 32, '#8dabbf')
        d.rounded_rectangle((105, 490, 975, 640), 30, fill='#22384d')
        for k, b in enumerate((780, 640)):
            d.rounded_rectangle((140, 525 + k * 55, 140 + b, 555 + k * 55), 12, fill='#5d7790')
        d.rounded_rectangle((105, 680, 975, 1220), 24, fill=hell)
        txt(140, 705, 'CITED SOURCE', 34, '#c2410c')
        # Das Ausloeserwort allein ("ANSWER") ist keine Quelle - nur Begriffe mit Inhalt auflisten.
        for k, p in enumerate([p for p in phrasen(text, 5) if p not in ('ANSWER', 'ANSWERS', 'REPLIES')][:4]):
            y = 775 + k * 108
            d.ellipse((140, y + 6, 190, y + 56), fill='#16a34a')
            d.line((152, y + 32, 162, y + 44, 180, y + 18), fill='white', width=7)
            txt(215, y + 8, p, passend(p, 730, 40), dunkel)
    elif art == 'vergleich':
        m = re.search(r'(.+?),?\s*(?:\bnot\b|\binstead of\b|\brather than\b|\bvs\.?)\s+(.+)', satz, re.I)
        links = (phrasen(m[1], 4) if m else [])[-1:] or ['?']
        rechts = (phrasen(m[2], 4) if m else [])[-1:] or ['?']
        for k, (wort, farbe) in enumerate(((links[0], gelb), (rechts[0], tuerkis))):
            y = 420 + k * 470
            d.rounded_rectangle((75, y, 1005, y + 340), 28, fill='#13283d', outline=farbe, width=6)
            n = 64
            zeilen = umbruch(wort, 860, n)
            for j, z in enumerate(zeilen[:3]):
                txt(115, y + 170 - len(zeilen[:3]) * 42 + j * 84, z, n, farbe)
        d.rounded_rectangle((cx - 110, 775, cx + 110, 875), 24, fill=rot)
        txt(cx - d.textlength('NOT', font=font(60)) / 2, 790, 'NOT', 60, 'white')
    elif art == 'verbinden':
        # Der Vorgang "hinzufuegen": Einstellungsfenster des ersten genannten Programms, neue Zeile mit
        # Werkzeug + ADD und Mauszeiger; die weiteren genannten Programme darunter. Groq 16.10.2026: die
        # Stern-Grafik (nur Namen + Linien) bekam 5/10 - "die Handlung des Hinzufuegens fehlt".
        namen = [n for n in begriffe(text) if n.upper() != kopf][:4]
        was = next((re.sub(r'^(?:(?:ADD|INSTALL|CONNECT|PLUG IN)\s+)?(?:THE|A|AN)\s+', '', p) for p in phrasen(text, 5)
                    if re.search(r'CONNECTOR|PLUGIN|SERVER|EXTENSION|INTEGRATION|MCP', p)), 'CONNECTOR')
        d.rounded_rectangle((75, 400, 1005, 1010), 26, fill='#0b1620', outline='#2b4258', width=4)
        d.rectangle((77, 402, 1003, 480), fill='#1b2d3e')
        fenster = ((namen[0] if namen else 'AI APP') + '  ·  SETTINGS').upper()
        txt(115, 420, fenster, passend(fenster, 820, 36), hell)
        txt(115, 510, 'CONNECTORS', 34, '#8dabbf')
        for k in range(2):
            d.rounded_rectangle((105, 575 + k * 105, 975, 655 + k * 105), 18, fill='#1b2d3e')
            d.rounded_rectangle((135, 600 + k * 105, 135 + (420, 330)[k], 630 + k * 105), 10, fill='#3c556c')
        d.rounded_rectangle((105, 800, 975, 960), 22, fill='#13283d', outline=tuerkis, width=6)
        zeile = '+ ' + kopf
        txt(140, 815, zeile, passend(zeile, 560, 46), tuerkis)
        txt(140, 885, was, passend(was, 560, 34), hell)
        d.rounded_rectangle((740, 835, 945, 925), 20, fill=tuerkis)
        txt(780, 855, 'ADD', 46, dunkel)
        d.polygon([(880, 900), (880, 1000), (905, 975), (925, 1020), (945, 1010), (925, 965), (960, 962)],
                  fill='white', outline=dunkel)
        if len(namen) > 1:
            txt(75, 1050, 'ALSO IN:', 34, '#8dabbf')
            x = 75
            for name in namen[1:]:
                breite = d.textlength(name, font=font(40)) + 60
                if x + breite > 1005:
                    break
                d.rounded_rectangle((x, 1110, x + breite, 1180), 16, fill='#13283d', outline=gelb, width=4)
                txt(x + 30, 1122, name, 40, gelb)
                x += breite + 24
    elif art == 'kernsatz':
        # Kernaussage als grosse Schlagzeilen - frueher Balken mit erfundenen Werten (Pruefer: "generisch").
        y = 420
        for k, p in enumerate(phrasen(text, 4) or [satz.upper()[:40]]):
            n = passend(p, 860, 74)
            d.rounded_rectangle((75, y, 1005, y + n + 70), 24, fill=('#13283d', '#2a1d12')[k % 2],
                                outline=(tuerkis, gelb)[k % 2], width=5)
            txt(115, y + 32, p, n, (tuerkis, gelb)[k % 2])
            y += n + 110
            if y > 1150:
                break
    # Beschriftungen nebeneinander und umbrechend: alles bis y ~1250, dem sichtbaren Pruefausschnitt.
    x, y = 75, 1030
    for name in (begriffe(text, motiv)[:4] if beschriften else []):
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
