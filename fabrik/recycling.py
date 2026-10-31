"""Gewinner nach 30 Tagen neu erzaehlen - mit neuem Hook und neuem Titel.

Nutzer 31.10.2026 („Deine Vorschlaege umsetzen"): ein Video, das auf TikTok deutlich ueber dem Kanalschnitt lief,
hat ein bewiesenes Thema. Nach ALTER_TAGE kommen viele neue Zuschauer; die Geschichte wird mit anderem ersten Satz
und anderem Einstiegsmoment neu gebaut. GEMESSEN 31.10.2026 (erfolg/*.json, TikTok-Median): Business 568 Aufrufe,
Spitze 974 (1,7x); KI 122, Spitze 573 (4,7x).

Weg: einmal pro Woche (TAG) ein Eintrag in die Themen-Warteschlange. Er laeuft dann wie ein Nutzerthema
(Vorrang, feste Wahl, Auftrag an den Autor ueber idee_original) - lauf.py und skript.py bleiben unveraendert.
Das Thema traegt den Zusatz ZUSATZ, sonst traegt lauf.py es als „schon geliefert" sofort wieder aus.
"""
import datetime
import json
import re
import statistics
from pathlib import Path

ALTER_TAGE = 30
FAKTOR = 1.3        # Aufrufe gegenueber dem TikTok-Median; Business streut eng (Spitze 1,7x, 788 = 1,4x)
MIN_AUFRUFE = 300   # unter dieser Zahl ist auch das 1,5-fache Zufall
TAG = 6             # Sonntag; Mittwoch ist der Tierlist-Tag des KI-Kanals
ZUSATZ = ' (remake)'
ERFOLG = Path('erfolg')


def _norm(t):
    return re.sub(r'\W+', ' ', str(t or '')).strip().lower()


def _datum(text):
    try:
        return datetime.date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def gewinner(kanal, heute, erfolg=ERFOLG):
    """Bester noch nicht neu erzaehlter Gewinner: dict(thema, titel, hook, aufrufe, faktor, tage) oder None."""
    import kanalstandard
    import themen
    try:
        tiktok = list((json.loads((Path(erfolg) / f'{kanal}.json').read_text(encoding='utf-8')).get('tiktok')
                       or {}).values())
        geliefert = json.loads(themen.GELIEFERT.read_text(encoding='utf-8'))
        profil = kanalstandard.alle().get(kanal) or {}
        name = profil.get('name') or kanal
    except (OSError, ValueError, AttributeError, TypeError):
        return None
    # Firmenkanaele vergleichen die Firma wie themen.wiederholung_gesperrt: Tesla lief am 17.10. als
    # „Tesla: How Funding ..." und am 25.10. als Langvideo „Tesla" - das ist schon neu erzaehlt.
    gleich = themen._gleiche_firma if profil.get('quelle') == 'wikipedia' else (lambda a, b: _norm(a) == _norm(b))
    geliefert = [e for e in geliefert if isinstance(e, dict) and e.get('kanal') == name]
    median = statistics.median([v.get('aufrufe') or 0 for v in tiktok] or [0]) or 1
    besten = []
    for v in tiktok:
        aufrufe, am = v.get('aufrufe') or 0, _datum(v.get('veroeffentlicht'))
        if not v.get('oeffentlich') or not am or (heute - am).days < ALTER_TAGE \
                or aufrufe < max(MIN_AUFRUFE, FAKTOR * median):
            continue
        # TikTok-Titel = Telegram-Titel ohne Satzzeichen; dort steht das Thema
        quelle = next((e for e in geliefert if _norm(e.get('titel')) == _norm(v.get('titel'))), None)
        if not quelle or not quelle.get('thema'):
            continue
        thema = str(quelle['thema']).removesuffix(ZUSATZ)
        # Schon neu erzaehlt: dasselbe Thema spaeter noch einmal geliefert (auch als Remake)
        if any(gleich(str(e.get('thema')).removesuffix(ZUSATZ), thema)
               and (_datum(e.get('datum_utc')) or am) > am + datetime.timedelta(days=1) for e in geliefert):
            continue
        besten.append({'thema': thema, 'titel': v.get('titel') or '', 'hook': v.get('hook') or '',
                       'aufrufe': aufrufe, 'faktor': round(aufrufe / median, 1), 'tage': (heute - am).days})
    return max(besten, key=lambda g: g['aufrufe'], default=None)


def auftrag(g):
    """Auftrag an den Autor (landet als idee_original im Skriptauftrag)."""
    return (f'Remake of our past winner "{g["titel"]}" ({g["aufrufe"]} TikTok views, {g["faktor"]}x our channel '
            f'median, {g["tage"]} days ago). Retell the same story for new viewers with a NEW first sentence, a '
            'different opening moment and a new title. Do not reuse the old opening'
            + (f': "{g["hook"]}"' if g['hook'] else '') + '.')


def einreihen(kanal, heute=None, erfolg=ERFOLG):
    """Am TAG einmal je Woche den Gewinner einreihen. Gibt das neue Thema zurueck oder None."""
    import themen
    heute = heute or datetime.date.today()
    if heute.weekday() != TAG:
        return None
    liste = themen.laden()
    kennung = f'recycling-{kanal}-{heute.isocalendar()[0]}-{heute.isocalendar()[1]}'
    if any(x.get('id') == kennung or (x.get('kanal') == kanal and str(x.get('thema')).endswith(ZUSATZ))
           for x in liste):
        return None
    g = gewinner(kanal, heute, erfolg)
    if not g:
        return None
    thema = g['thema'] + ZUSATZ
    liste.insert(0, {'kanal': kanal, 'thema': thema, 'eingang': heute.isoformat(), 'id': kennung,
                  'trend_suche': g['thema'], 'idee_original': auftrag(g)})
    themen.speichern(liste)
    print(f'Gewinner neu erzaehlen: {thema} ({g["aufrufe"]} TikTok-Aufrufe, {g["faktor"]}x Median)')
    return thema
