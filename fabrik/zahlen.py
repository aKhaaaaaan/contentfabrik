"""Zahlenprobe ohne KI: Jede Zahl im gesprochenen Skript muss in den Quellen stehen.

GEMELDET (KI-Analyse 03.10.2026): Ein Faktencheck durch eine KI ist
unzuverlaessig - sie kann eine erfundene Jahreszahl durchwinken. Zahlen sind
die haeufigste und am leichtesten pruefbare Fehlerquelle (Gruendungsjahr,
Umsatz, Downloads). Darum prueft der Code: steht die Zahl in der Quelle?

Bewusst NICHT geprueft:
- Zahlen bis 10 (Countdown-Plaetze „Number 3", „two brothers") - zu viele
  Fehlalarme, kaum Schaden.
- gerundete Angaben („over 4,000 stores" bei 4,700 in der Quelle) gelten als
  belegt, wenn die gerundete Zahl hoechstens 25 % unter einer Quellzahl liegt
  und nur 1-2 gueltige Stellen hat - genau so rundet man beim Erzaehlen.
"""
import re

# 1,200 · 1.5 · 2023 · 40% · $3 - Tausendertrennung mit Komma wird entfernt
_ZAHL = re.compile(r'(?<![\w.])\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![\w.,])\d+(?:\.\d+)?')
_FEST = {60}  # „in 60 seconds" ist das Format, keine Behauptung
_MASS = {'thousand': 1e3, 'k': 1e3, 'million': 1e6, 'm': 1e6, 'billion': 1e9, 'bn': 1e9, 'b': 1e9,
         'trillion': 1e12}


_EINER = {w: i for i, w in enumerate('zero one two three four five six seven eight nine ten eleven twelve thirteen '
                                     'fourteen fifteen sixteen seventeen eighteen nineteen'.split())}
_ZEHNER = {w: 10 * i for i, w in enumerate('_ _ twenty thirty forty fifty sixty seventy eighty ninety'.split()) if i > 1}
_STUFE = {'thousand': 1e3, 'million': 1e6, 'billion': 1e9, 'trillion': 1e12}
_WORT = re.compile(r'\b(?:(?:a|' + '|'.join(list(_EINER) + list(_ZEHNER) + list(_STUFE) + ['hundred', 'oh', 'point'])
                   + r')\b[\s-]*(?:and\s+)?)+', re.I)


def _wort_wert(folge):
    """„one thousand three hundred thirty-eight" -> 1338, „nineteen seventy-seven" -> 1977,
    „one point two billion" -> 1.2e9. None, wenn es keine Zahl ist (z. B. nur „a")."""
    w = [x for x in re.split(r'[\s-]+', folge.lower()) if x and x != 'and']
    while w and w[-1] in ('a', 'point', 'oh'):
        w.pop()
    if not w or w == ['a']:
        return None
    # GEMESSEN: „a multi-billion empire" wurde zu 1.000.000.000 - ein blosses
    # Mengenwort ohne Zahl davor ist keine Zahlenangabe.
    if all(x in _STUFE for x in w):
        return None
    if not any(x in _STUFE or x == 'hundred' or x == 'point' for x in w):
        # Jahreszahl wie gesprochen: „nineteen seventy-seven", „twenty twenty-three", „nineteen oh five"
        gruppen, akt = [], None
        for x in w:
            if x == 'oh':  # „nineteen oh five" = 1905
                gruppen.append(akt); akt = None; continue
            v = _EINER.get(x, _ZEHNER.get(x))
            if v is None:
                return None
            if akt is not None and x in _EINER and akt % 10 == 0 and akt >= 20 and v < 10:
                akt += v  # „seventy seven" ohne Bindestrich
            else:
                if akt is not None:
                    gruppen.append(akt)
                akt = v
        gruppen.append(akt)
        if len(gruppen) == 2 and 10 <= gruppen[0] <= 99 and 0 <= gruppen[1] <= 99:
            return gruppen[0] * 100 + gruppen[1]
        return gruppen[0] if len(gruppen) == 1 else None
    gesamt, akt, nachkomma, stelle = 0.0, 0.0, None, 0.1
    for x in w:
        if x == 'a':
            akt = akt or 1
        elif x == 'point':
            nachkomma = 0.0
        elif x in _EINER and nachkomma is not None:
            nachkomma += _EINER[x] * stelle; stelle /= 10
        elif x in _EINER or x in _ZEHNER:
            akt += _EINER.get(x, _ZEHNER.get(x))
        elif x == 'hundred':
            akt = (akt or 1) * 100
        elif x in _STUFE:
            gesamt += ((akt or 1) + (nachkomma or 0)) * _STUFE[x]; akt, nachkomma, stelle = 0.0, None, 0.1
    return gesamt + akt + (nachkomma or 0)


def ziffern(text):
    """Zahlwoerter durch Ziffern ersetzen. GEMESSEN 04.10.2026: Mehrere Skripte
    schrieben fast alle Zahlen als Woerter (84 Zahlwoerter, 0 Ziffern; Jahre
    als „nineteen seventy-seven") - die Probe hatte sie gar nicht gesehen."""
    def ersetze(m):
        v = _wort_wert(m.group())
        if v is None:
            return m.group()
        return (f'{v:g}' if v != int(v) else str(int(v))) + (' ' if m.group().endswith((' ', '-')) else '')
    return _WORT.sub(ersetze, text)


def werte(text, beide=True):
    """Alle Zahlen eines Textes als float, Mengenwoerter („1.2 billion") eingerechnet.
    beide=True (Quellen): roh UND umgerechnet, damit jede Schreibweise trifft.
    beide=False (Skript): nur der gemeinte Wert - sonst wuerde die rohe „1.2"
    aus „1.2 billion" einzeln geprueft und faelschlich angemahnt."""
    aus = set()
    text = ziffern(text)
    for m in _ZAHL.finditer(text):
        roh = m.group().replace(',', '')
        try:
            w = float(roh)
        except ValueError:
            continue
        rest = text[m.end():m.end() + 10].lower()
        einheit = re.match(r'\s*(thousand|million|billion|trillion|bn|k|m|b)\b', rest)
        if einheit:
            aus.add(w * _MASS[einheit.group(1)])
        if beide or not einheit:
            aus.add(w)
    return aus


def _gerundet(w):
    """1-2 gueltige Stellen (4000, 1.5 Mio, 20) = typische Rundung beim Erzaehlen."""
    ziffern = re.sub(r'\D', '', f'{w:.10g}').strip('0')
    return len(ziffern) <= 2


def unbelegt(entwurf, quellen_texte):
    """Zahlen aus dem gesprochenen Text, die in keiner Quelle stehen (Liste fuer die Nachbesserung)."""
    belegt = set()
    for t in quellen_texte:
        belegt |= werte(t)
    fehlend = []
    for teil in entwurf.get('teile', []):
        satz = teil.get('text', '')
        for w in sorted(werte(satz, beide=False)):
            if w <= 10 or w in _FEST or w in belegt:
                continue
            if _gerundet(w) and any(w <= b <= w * 1.25 for b in belegt):
                continue
            # Jahreszahl als Teil eines Datums der Quelle („March 1946") ist schon in belegt.
            zahl = str(int(w)) if w == int(w) else f'{w:g}'
            fehlend.append(f'{zahl} („{satz.strip()[:80]}")')
    return fehlend
