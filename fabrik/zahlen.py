"""Zahlenprobe ohne KI: Jede Zahl im gesprochenen Skript muss in den Quellen stehen.

GEMELDET (KI-Analyse 03.10.2026): Ein Faktencheck durch eine KI ist
unzuverlaessig - sie kann eine erfundene Jahreszahl durchwinken. Zahlen sind
die haeufigste und am leichtesten pruefbare Fehlerquelle (Gruendungsjahr,
Umsatz, Downloads). Darum prueft der Code: steht die Zahl in der Quelle?

Bewusst NICHT geprueft:
- Zahlen bis 10 (Countdown-Plaetze „Number 3", „two brothers") - zu viele
  Fehlalarme, kaum Schaden.
- Zahlen in Worten („nineteen forty-six") - die Skripte schreiben Ziffern.
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


def werte(text, beide=True):
    """Alle Zahlen eines Textes als float, Mengenwoerter („1.2 billion") eingerechnet.
    beide=True (Quellen): roh UND umgerechnet, damit jede Schreibweise trifft.
    beide=False (Skript): nur der gemeinte Wert - sonst wuerde die rohe „1.2"
    aus „1.2 billion" einzeln geprueft und faelschlich angemahnt."""
    aus = set()
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
