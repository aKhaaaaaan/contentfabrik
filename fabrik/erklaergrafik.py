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
    # „Did it work? ... runs 2.7x" - der Vergleichspartner steht im naechsten Satz desselben Abschnitts
    if art not in ('balken', 'rechnung', 'schluessel', 'download') and phase and phase.strip() != text.strip() \
            and re.search(r'\d+(?:\.\d+)?\s?x\b|\bup from\b', text) and balken(phase):
        return 'balken'
    if art == 'kernsatz' and phase and phase.strip() != text.strip():
        geerbt = _layout(phase)
        if geerbt in ('frage', 'zitat', 'warnung'):  # 'vergleich' braucht beide Seiten im Teilsatz selbst
            return geerbt
    return art


def vergleich_seiten(text):
    """(gewaehlte Seite, verworfene Seite) eines gesprochenen Vergleichs, sonst None.

    GEMESSEN 18.10.2026 (Konnect, Lauf 39141604726): "It's still beta, so review matters." erbte den Vergleich
    seines Abschnitts, "Instead of placing every part by hand, you direct and review." passte nicht ins Muster
    "A instead of B" -> beide Grafiken "? NOT ?", identisch -> "Gleiches Motiv zu lange gehalten", alle Bauversuche."""
    satz = re.sub(r'\s+', ' ', str(text)).strip()
    m = re.match(r'(?:instead of|rather than)\s+(.+?),\s*(.+)', satz, re.I)
    if m:
        gewaehlt, verworfen = m[2], m[1]
    else:
        m = re.search(r'(.+?),?\s*(?:\bnot\b|\binstead of\b|\brather than\b|\bvs\.?)\s+(.+)', satz, re.I)
        if not m:
            return None
        gewaehlt, verworfen = m[1], m[2]
    links, rechts = phrasen(gewaehlt, 4)[-1:], phrasen(verworfen, 4)[-1:]
    return (links[0], rechts[0]) if links and rechts and links != rechts else None


# GEMESSEN 19.10.2026 (Gemini 4 Argon, Lauf 39235396942): 8 von 14 Einstellungen 2-3/10, alle Ablehnungen
# „zeigt nur Text"/„nur Textueberschriften": Saetze ohne eigenes Bildmuster fielen auf 'kernsatz' (gesprochene
# Woerter in Kaesten) oder 'zahlen' (Zahlenkacheln). Bestanden haben nur Grafiken mit einem GEGENSTAND (Rechnung
# 8-10, Warnzeichen 8). Darum zeigt jetzt jede Satzart ihren Gegenstand oder Vorgang: Code -> Editorfenster,
# Vergleich -> Balken mit den gesprochenen Werten, Zugang -> Schranke mit Wartenden, Agenten -> Arbeitsschleife.
# „source" allein nicht: „source-cited drafts" (OpenAccountants) ist kein Code
CODE = re.compile(r"\b(?:code|coding|codebase|lines? of code|compil\w*|rust|python|javascript|typescript|decoder|"
                  r"encoder|source code|repo|repository|refactor\w*|rewrites?|rewrote|rewritten|vectori[sz]\w*|bugs?|"
                  r"debug\w*|programm\w*)\b|\d+[kK]?-line", re.I)
ZUGANG = re.compile(r"\b(?:rolling out|rolls? out|access|available|availability|wait ?list|trusted|invite\w*|"
                    r"early access|limited to|only for|defenders|testers|beta users)\b", re.I)
AGENTEN = re.compile(r"\b(?:agents?|experiments?|rounds?|iterat\w+|trajector\w+|loops?)\b", re.I)
_ZAHL = r"\$?\d[\d,.]*\s?[kKmMbB]?\b"


def _wert(s):
    """'1M' -> 1e6, '64K' -> 64000, '$2' -> 2, '2.7x' -> 2.7, '32,000' -> 32000; sonst None."""
    m = re.match(r'\$?(\d[\d,]*(?:\.\d+)?)\s?([kKmMbB])?', str(s).strip())
    if not m:
        return None
    return float(m[1].replace(',', '')) * {'k': 1e3, 'm': 1e6, 'b': 1e9}.get((m[2] or '').lower(), 1)


def balken(text):
    """Gesprochener Vergleich zweier Werte als [(Beschriftung, Wert-Text, Wert)] - nur gesprochene Zahlen.
    'reaches 1M tokens, up from 64K' / 'runs 2.7x faster than the earlier Rust port' / '$2 input, $10 output'."""
    satz = re.sub(r'\s+', ' ', str(text))
    m = re.search(rf"({_ZAHL})\s*([A-Za-z]+)?[^.]*?\bup from\s+({_ZAHL})", satz)
    if m:
        einheit = (m[2] or '').upper()
        return [('BEFORE', f'{m[3].strip()} {einheit}'.strip(), _wert(m[3])),
                ('NOW', f'{m[1].strip()} {einheit}'.strip(), _wert(m[1]))]
    m = re.search(r"(\d+(?:\.\d+)?)\s?x\b(?:\s+faster)?[^.]*?\bthan (?:the |its |an? )?([A-Za-z0-9' -]{3,30}?)(?=[,.;]|$| with\b)",
                  satz, re.I)
    if m:
        return [(m[2].strip().upper()[:22], '1x', 1.0), ('NEW', f'{m[1]}x', float(m[1]))]
    m = re.search(rf"\bfrom ({_ZAHL})\s*([A-Za-z]+)? to ({_ZAHL})", satz)
    if m:
        return [('BEFORE', m[1].strip(), _wert(m[1])), ('AFTER', m[3].strip(), _wert(m[3]))]
    geld = re.findall(r"(\$\d[\d,.]*)(?:\s+per\s+[a-z]+)?\s+([a-z]+)(?:\s+tokens)?", satz, re.I)
    if len(geld) >= 2:
        return [(w.upper(), z, _wert(z)) for z, w in geld[:3]]
    return None


def _layout(text):
    """Bildaufbau aus dem Inhalt des Satzes. GEMESSEN 16.10.2026 (OpenAccountants, Lauf 38888929052): Es gab
    nur Datenbank-Symbol oder Balken mit erfundenen Werten; 5 von 9 Grafiken sahen gleich aus, der Pruefer
    lehnte "Zitat eines Guides" (4/10) und "keine Finanzberatung" (2/10) ab. Jetzt zeigt jede Grafik den
    Vorgang des Satzes: Frage -> Chat, Zitat -> Antwort mit Quellenkarte, Zahlen -> Zahlenkacheln usw."""
    t = text.lower()
    art = symbol(text)
    if art in ('schluessel', 'download'):
        return art
    # Preis-Rechnung bestand mit 10/10 - die bleibt; jeder andere gesprochene Vergleich wird Balken
    if balken(text) and not (art == 'rechnung' and '$' in text):
        return 'balken'
    # GEMESSEN 19.10. (Argon): „write hundreds of thousands of tokens in one trajectory" als LLM-Rechnung = 2/10.
    # Tokens ohne Kosten sind Textmenge, keine Rechnung.
    if art == 'rechnung' and not re.search(r'\b(?:bills?|billing|costs?|price|pricing|paid|charged?|per token)\b|\$\d',
                                           t):
        return 'ausgabe'
    if art == 'rechnung':
        return art
    # „Now the catch: access is limited": Warnzeichen 8/10, Schranke 3/10 - ein angekuendigter Haken bleibt Warnung
    if re.search(r'\b(?:catch|limitation|downside|caveat)\b', t):
        return 'warnung'
    if re.search(r"financial advice|outdated|\bwrong\b|\brisks?\b|warning|careful|\bverify\b|double-check", t):
        return 'warnung'
    if re.search(r'\bagents?\b', t) and re.search(r'\b(?:ran|run|runs|experiments?|rounds?|tried|tested)\b', t):
        return 'agenten'
    if CODE.search(text):
        return 'code'
    if ZUGANG.search(text):
        return 'zugang'
    if AGENTEN.search(text):
        return 'agenten'
    if zahlen(text):
        return 'zahlen'
    if text.strip().endswith('?') or re.search(r'\b(ask|asks|asking|question)\b', t):
        return 'frage'
    if re.search(r'\b(cite|cites|citing|citation|reviewer|answer|answers|replies|quote)\b', t):
        if not re.search(r'\bnot from\b|\binstead of\b|\brather than\b', t):
            return 'zitat'
        if vergleich_seiten(text):
            return 'vergleich'
    if re.search(r'\bnot from\b|\binstead of\b|\brather than\b|\bvs\.?\s|, not\b', t) and vergleich_seiten(text):
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
        seiten = vergleich_seiten(satz) or ('?', '?')  # nur bei ausdruecklich uebergebenem art='vergleich'
        for k, (wort, farbe) in enumerate(((seiten[0], gelb), (seiten[1], tuerkis))):
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
    elif art == 'balken':
        # Gesprochene Werte als Balken (Hoehe = Wert, bei sehr grossem Abstand Wurzel-Skala, damit der kleine
        # Balken sichtbar bleibt). Der Balken, den DIESER Satz nennt, ist hervorgehoben.
        werte = [w for w in (balken(satz) or balken(phase) or []) if w[2]]
        groesster = max(w[2] for w in werte)
        skala = (lambda v: (v / groesster) ** 0.5) if groesster / max(min(w[2] for w in werte), 1e-9) > 20 \
            else (lambda v: v / groesster)
        breite = 860 // len(werte)
        boden = 1120
        d.line((75, boden, 1005, boden), fill='#8dabbf', width=6)
        for k, (wort, zahl, wert) in enumerate(werte):
            x0 = 75 + k * breite + 40
            x1 = x0 + breite - 80
            hoch = max(40, int(560 * skala(wert)))
            genannt = zahl.split()[0].lower() in satz.lower() or any(
                w.lower() in satz.lower() for w in wort.split() if len(w) > 3)
            farbe = gelb if genannt else '#4b6a86'
            d.rounded_rectangle((x0, boden - hoch, x1, boden), 18, fill=farbe)
            n = passend(zahl, x1 - x0, 64)
            txt(x0 + (x1 - x0 - d.textlength(zahl, font=font(n))) / 2, boden - hoch - n - 24, zahl, n,
                gelb if genannt else hell)
            for j, z in enumerate(umbruch(wort, x1 - x0 + 40, 34)[:2]):
                txt(x0 - 20, boden + 24 + j * 44, z, 34, hell)
    elif art == 'code':
        # Code-Saetze haben je Vorgang ein eigenes Bild (GEMESSEN an Argon: sechs gleiche Editorfenster waeren
        # „gleiches Motiv zu lange"): Compiler -> parallele Spuren, Decoder -> Videobilder rein/raus,
        # Umbau/Port -> alt neben neu, sonst Editor mit gesprochener Zeilenzahl. Codezeilen sind Platzhalter.
        import hashlib
        zufall = hashlib.sha256(satz.encode()).digest()
        farben = ('#20d2be', '#ffae35', '#c792ea', '#8dabbf', '#dce4ec')

        def editor(x0, y0, x1, y1, titel, zeilen, versatz=0):
            d.rounded_rectangle((x0, y0, x1, y1), 22, fill='#0b1620', outline='#2b4258', width=4)
            d.rectangle((x0 + 2, y0 + 2, x1 - 2, y0 + 58), fill='#1b2d3e')
            for k, f in enumerate(('#ff5a5f', '#ffae35', '#16a34a')):
                d.ellipse((x0 + 22 + k * 36, y0 + 20, x0 + 44 + k * 36, y0 + 42), fill=f)
            if titel:
                txt(x0 + 140, y0 + 14, titel, passend(titel, x1 - x0 - 160, 30), hell)
            for z in range(zeilen):
                y = y0 + 80 + z * 40
                txt(x0 + 20, y, f'{z + 1:>2}', 22, '#4b6a86')
                x = x0 + 75 + (zufall[(z + versatz) % 32] % 3) * 30
                for j in range(1 + zufall[(z + 11 + versatz) % 32] % 3):
                    b = 50 + zufall[(z * 3 + j + versatz) % 32] % 150
                    if x + b > x1 - 25:
                        break
                    d.rounded_rectangle((x, y + 4, x + b, y + 24), 8, fill=farben[(zufall[(z + versatz) % 32] + j) % 5])
                    x += b + 20

        def leiste(y, s, farbe, haken=False):
            d.rounded_rectangle((75, y, 1005, y + 100), 22, fill='#13283d', outline=farbe, width=5)
            if haken:
                d.rounded_rectangle((100, y + 15, 170, y + 85), 12, fill=farbe)
                d.line((115, y + 50, 132, y + 68, 158, y + 30), fill=dunkel, width=10)
            txt(195 if haken else 110, y + 24, s, passend(s, 780 if haken else 860, 50), farbe)

        def pfeil(x, y0, y1):
            d.rectangle((x - 12, y0, x + 12, y1 - 30), fill=hell)
            d.polygon([(x - 40, y1 - 40), (x + 40, y1 - 40), (x, y1)], fill=hell)

        namen = [n for n in begriffe(text) if n.upper() != kopf and not re.match(r'[\d$]', n)]
        fenster = (namen[0] if namen else (phrasen(satz, 1) or ['SOURCE CODE'])[0]).upper()
        erledigt = bool(re.search(r'\b(worked|works|passed|succeed\w*|identical)\b', satz, re.I))
        wichtig = [p for p in phrasen(satz, 5) if re.search(
            r'COMPIL|VECTORI|REWR|SAFE|RUST|DECODER|WORKED|BUG|REFACTOR|OUTPUT|PORT|IDENTICAL', p)]
        menge = next((f'{zahl} {wort}' for zahl, wort in zahlen(satz) if re.search(r'LINE', wort)), None)
        if not menge:
            m = re.search(r'(\d[\d,.]*[kK]?)-line', satz)
            menge = f'{m[1]} LINES' if m else None
        if re.search(r'compil\w*|vectori[sz]\w*', satz, re.I):
            editor(75, 400, 1005, 640, fenster if namen else 'CODE', 4)
            pfeil(540, 650, 740)
            d.rounded_rectangle((300, 750, 780, 850), 24, fill=gelb)
            txt(540 - d.textlength('COMPILER', font=font(52)) / 2, 770, 'COMPILER', 52, dunkel)
            parallel = re.search(r'vectori[sz]\w*', satz, re.I)
            for k in range(4 if parallel else 1):
                x = 160 + k * 200 if parallel else 440
                pfeil(x + 70 if parallel else 540, 860, 950)
                d.rounded_rectangle((x, 955, x + 140 if parallel else 640, 1035), 18, fill=tuerkis)
            if wichtig:
                leiste(1070, wichtig[-1], tuerkis)
        elif re.search(r'\b(?:decoder|encoder|video|frames?)\b', satz, re.I) and not re.search(
                r'\b(?:port|rewr\w*|earlier|older|previous)\b', satz, re.I):
            for k in range(4):  # Videobilder hinein
                d.rounded_rectangle((95 + k * 70, 470 + k * 30, 335 + k * 70, 630 + k * 30), 14,
                                    fill='#22384d', outline=hell, width=4)
            d.polygon([(250, 560), (250, 640), (315, 600)], fill=hell)
            d.rectangle((470, 560, 560, 600), fill=hell)
            d.polygon([(560, 540), (560, 620), (610, 580)], fill=hell)
            editor(620, 430, 1005, 760, 'DECODER', 6)
            if re.search(r'\bagents?\b', satz, re.I):
                # GEMESSEN 19.10. (Argon, 6/10): „Argon agents did ... decoder" - Pruefer vermisste die Agenten
                for k in range(2):
                    x, y = 700 + k * 170, 690
                    d.rounded_rectangle((x - 55, y - 45, x + 55, y + 35), 20, fill=(tuerkis, gelb)[k],
                                        outline=dunkel, width=6)
                    d.ellipse((x - 30, y - 22, x - 10, y - 2), fill=dunkel)
                    d.ellipse((x + 10, y - 22, x + 30, y - 2), fill=dunkel)
                txt(660, 745, 'AGENTS', 34, hell)
            leiste(820, fenster if namen else 'DECODER', gelb)
            if wichtig and wichtig[-1] != fenster:
                leiste(950, wichtig[-1], tuerkis, erledigt)
        elif re.search(r'\b(?:port|rewr\w*|earlier|older|previous|migrat\w*)\b', satz, re.I):
            editor(75, 420, 505, 860, 'BEFORE', 9)
            editor(575, 420, 1005, 860, 'AFTER', 9, versatz=7)
            d.polygon([(500, 610), (500, 670), (580, 640)], fill=gelb)
            leisten = ([menge.upper()] if menge else []) + [p for p in (wichtig or phrasen(satz, 2))
                                                            if not menge or menge.split()[0] not in p]
            for k, p in enumerate(leisten[:2]):
                leiste(900 + k * 120, p, (gelb, tuerkis)[k] if menge else (tuerkis, gelb)[k],
                       erledigt and k == len(leisten[:2]) - 1)
        else:
            editor(75, 400, 1005, 1010, fenster, 12)
            y = 1040
            if menge:
                d.rounded_rectangle((75, y, 1005, y + 100), 22, fill='#13283d', outline=gelb, width=5)
                txt(110, y + 22, menge.upper(), passend(menge.upper(), 860, 54), gelb)
                y += 120
            if wichtig and y < 1180:
                leiste(y, wichtig[-1], tuerkis, erledigt)
    elif art == 'zugang':
        # Schranke mit Wartenden. Je nach Satz geschlossen (begrenzt), wenige durch (Rollout an eine Gruppe)
        # oder offen (spaeter breiter Zugang) - sonst drei gleiche Bilder hintereinander.
        def person(x, y, farbe, s=1.0):
            d.ellipse((x - 26 * s, y - 120 * s, x + 26 * s, y - 68 * s), fill=farbe)
            d.rounded_rectangle((x - 40 * s, y - 60 * s, x + 40 * s, y + 40 * s), int(22 * s), fill=farbe)
        offen = re.search(r'\b(?:wider|broader|everyone|all users|general availability|later|after)\b', satz, re.I)
        durch = re.search(r'\b(?:rolling out|rolls? out|to a set|trusted|selected|early access|testers)\b', satz, re.I)
        if offen:
            d.rectangle((520, 470, 560, 1080), fill='#2b4258')
            d.rounded_rectangle((560, 470, 600, 520), 10, fill=tuerkis)  # Schranke hochgeklappt
            d.rectangle((560, 470, 600, 700), fill=tuerkis)
            for k in range(9):
                person(640 + (k % 3) * 120, 700 + (k // 3) * 150, tuerkis, 0.8)
            d.rounded_rectangle((90, 560, 470, 900), 22, fill=hell)  # Pruefliste vor dem Oeffnen
            for k in range(4):
                d.rounded_rectangle((120, 600 + k * 70, 170, 650 + k * 70), 10, fill='#16a34a')
                d.line((130, 625 + k * 70, 142, 640 + k * 70, 162, 610 + k * 70), fill='white', width=6)
                d.rounded_rectangle((195, 615 + k * 70, 195 + (230, 190, 250, 170)[k], 635 + k * 70), 8, fill='#9fb0bf')
        else:
            d.rectangle((520, 470, 560, 1080), fill='#2b4258')
            d.rectangle((560, 820, 1000, 860), fill=gelb)  # geschlossene Schranke vor dem leeren Bereich
            d.rounded_rectangle((470, 640, 610, 760), 20, fill=gelb)
            d.arc((495, 570, 585, 680), 180, 360, fill=gelb, width=18)
            for k in range(8):
                person(130 + (k % 4) * 90, 760 + (k // 4) * 170, '#4b6a86', 0.8)
            if durch:
                for k, (x, y) in enumerate(((680, 760), (800, 820), (900, 740))):
                    person(x, y, tuerkis)
        gruppe = next((p for p in phrasen(satz, 5) if re.search(
            r'DEFENDER|TESTER|USER|DEVELOPER|CUSTOMER|PARTNER|TEAM|TRUSTED|SUBSCRIBER|TESTING', p)), None)
        rest = [p for p in phrasen(satz, 4) if p != gruppe]
        if gruppe:
            d.rounded_rectangle((620, 880, 1005, 1010) if not offen else (90, 920, 470, 1050), 22, fill='#13283d',
                                outline=tuerkis, width=5)
            for j, z in enumerate(umbruch(gruppe, 340, 38)[:2]):
                txt((645 if not offen else 115), (900 if not offen else 940) + j * 48, z, 38, tuerkis)
        if rest:
            d.rounded_rectangle((75, 1080, 1005, 1180), 22, fill='#2a1d12', outline=gelb, width=5)
            txt(110, 1102, rest[0], passend(rest[0], 860, 50), gelb)
    elif art == 'agenten':
        # Arbeitsschleife: drei Agenten-Karten im Kreis mit Pfeilen (Versuch -> Auswertung -> Verbesserung);
        # die gesprochenen Schritte stehen an den Karten.
        schritte = [p for p in phrasen(satz, 4) if not re.fullmatch(r'AGENTS?', p)][:3]
        orte = ((540, 500), (820, 870), (260, 870))
        for k, (x, y) in enumerate(orte):
            d.rounded_rectangle((x - 120, y - 85, x + 120, y + 30), 26, fill='#13283d',
                                outline=(tuerkis, gelb, '#c792ea')[k], width=6)
            d.rounded_rectangle((x - 50, y - 60, x + 50, y + 10), 18, fill=(tuerkis, gelb, '#c792ea')[k])
            d.ellipse((x - 30, y - 38, x - 10, y - 18), fill=dunkel)
            d.ellipse((x + 10, y - 38, x + 30, y - 18), fill=dunkel)
            ax, ay = orte[(k + 1) % 3]
            mx, my = (x + ax) / 2, (y + ay) / 2
            d.line((x + (ax - x) * 0.3, y + (ay - y) * 0.3, mx + (ax - mx) * 0.4, my + (ay - my) * 0.4),
                   fill=hell, width=10)
            d.ellipse((mx + (ax - mx) * 0.4 - 14, my + (ay - my) * 0.4 - 14,
                       mx + (ax - mx) * 0.4 + 14, my + (ay - my) * 0.4 + 14), fill=hell)
        for k, s in enumerate(schritte):
            x, y = orte[k]
            # Beschriftung UNTER der Karte (vorher in der Karte: lief ueber den Rand)
            zeilen = umbruch(s, 400, 34)[:2]
            for j, z in enumerate(zeilen):
                txt(x - d.textlength(z, font=font(34)) / 2, y + 50 + j * 42, z, 34, (tuerkis, gelb, '#c792ea')[k])
    elif art == 'ausgabe':
        # Lange KI-Ausgabe: ein Antwortfenster, dessen Text ueber den Rand hinauslaeuft (Bildlaufleiste fast leer),
        # daneben die gesprochene Menge. Zeigt "so viel Text in einem Durchgang" statt eines Rechnungszettels.
        d.rounded_rectangle((75, 400, 760, 1200), 26, fill='#0b1620', outline='#2b4258', width=4)
        txt(105, 420, 'AI OUTPUT', 30, '#8dabbf')
        for z in range(17):
            b = (600, 560, 620, 480, 590, 610, 540, 600, 570, 620, 500, 590, 610, 560, 600, 580, 620)[z]
            d.rounded_rectangle((105, 480 + z * 42, 105 + b, 500 + z * 42), 8, fill=('#dce4ec', '#8dabbf')[z % 4 == 3])
        d.rounded_rectangle((735, 430, 750, 1170), 7, fill='#1b2d3e')
        d.rounded_rectangle((735, 430, 750, 470), 7, fill=tuerkis)
        d.polygon([(380, 1215), (460, 1215), (420, 1265)], fill=gelb)  # laeuft weiter
        menge = next((p for p in phrasen(satz, 5) if re.search(r'TOKEN|WORD|PAGE|LINE', p)), None)
        rest = [p for p in phrasen(satz, 5) if p != menge and not re.match(r'GOOGLE SAYS|THAT LETS', p)]
        y = 470
        for k, p in enumerate(([menge] if menge else []) + rest[-1:]):
            zeilen = umbruch(p, 200, 34)[:4]
            hoehe = 40 + len(zeilen) * 44
            d.rounded_rectangle((790, y, 1005, y + hoehe), 20, fill='#13283d', outline=(gelb, tuerkis)[k], width=5)
            for j, z in enumerate(zeilen):
                txt(808, y + 20 + j * 44, z, 34, (gelb, tuerkis)[k])
            y += hoehe + 30
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
