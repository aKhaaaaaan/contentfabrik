"""Trend-Check: Welches Thema ist HEUTE gefragt? (Nutzerauftrag 09.10.2026)

„Die Themen muessen aktuell aus Google Trends kommen oder von dem, was auf YouTube viral ging."
Vorher gewann jeden Tag das aelteste Telegram-Thema, egal ob es gerade jemanden interessierte.
Jetzt bekommt jeder Kandidat - Warteschlange UND (Business) die gestern meistgelesenen Firmen -
Punkte aus drei offiziellen, kostenlosen Signalen:

  YouTube    Ausreisser der letzten 30 Tage zum Suchbegriff (Aufrufe / Kanaldurchschnitt).
             Ein Ausreisser zeigt, dass die IDEE zieht, nicht nur ein grosser Kanal.
  Wikipedia  AUFWIND statt Groesse: Aufrufe der letzten zwei Tage gegen den Median der vier
             Wochen davor. Netflix hat immer viele Aufrufe; zaehlt nur, wenn es gerade steigt.
  Google     Steht der Begriff heute in den US-Tagestrends (inkl. Schlagzeilen dazu)?

Eigene Themen bekommen einen kleinen Bonus (Nutzerwunsch zaehlt), schlagen aber kein echtes
Trendthema. Ohne Signal bleibt ein Thema liegen, bis es gefragt ist. Faellt JEDE Quelle aus
(kein Schluessel, Netz weg), gilt die alte Reihenfolge - nie still die Nutzerliste ignorieren.
Ergebnis je Kanal und Tag in verlauf/trendcheck/ (spart YouTube-Kontingent bei Wiederanlauf).
"""
import datetime
import json
import math
import re
import statistics
import urllib.parse
from pathlib import Path
from xml.etree import ElementTree

ORDNER = Path('verlauf/trendcheck')
BONUS_EIGEN = 1.0
SCHWELLE = 1.5  # darunter kein echtes Trendsignal
FREIE_KANDIDATEN = 5


def punkte(yt_faktor=None, wiki_aufwind=None, google=False, eigen=False):
    """Reine Rechenregel (testbar). Jedes Signal hoechstens 5 Punkte, damit keins allein alles kippt.
    YouTube logarithmisch: 3x Kanalschnitt ~1,6, 10x ~3,3, 30x ~4,9 Punkte."""
    p = 0.0
    if yt_faktor:
        p += min(5.0, max(0.0, math.log2(yt_faktor) * 1.0))
    if wiki_aufwind:
        p += min(5.0, max(0.0, (wiki_aufwind - 1.0) * 2.5))  # +40 % ~1 Punkt, verdoppelt 2,5
    if google:
        p += 4.0
    if eigen:
        p += BONUS_EIGEN
    return round(p, 2)


def wiki_aufwind(titel, heute=None):
    """Aufrufe der letzten 2 Tage / Median der 28 Tage davor; None ohne Daten."""
    import trends
    heute = heute or datetime.date.today()
    ende, anfang = heute - datetime.timedelta(days=1), heute - datetime.timedelta(days=31)
    try:
        d = json.loads(trends._hole(
            'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/'
            f'{urllib.parse.quote(titel.replace(" ", "_"), safe="")}/daily/{anfang:%Y%m%d}/{ende:%Y%m%d}',
            trends.WIKI_KENNUNG))
        werte = [x['views'] for x in d.get('items', [])]
    except Exception:
        return None
    if len(werte) < 10:
        return None
    basis = statistics.median(werte[:-2]) or 1
    return round(sum(werte[-2:]) / 2 / basis, 2)


def google_heute(land='US'):
    """[(Trendbegriff, [Schlagzeilen])] aus dem offiziellen RSS-Feed; [] bei Ausfall."""
    import trends
    try:
        wurzel = ElementTree.fromstring(trends._hole(f'https://trends.google.com/trending/rss?geo={land}'))
    except Exception as e:
        print('Google Trends nicht verfuegbar:', str(e)[:80])
        return []
    ns = {'ht': 'https://trends.google.com/trending/rss'}
    return [(item.findtext('title') or '', [n.findtext('ht:news_item_title', namespaces=ns) or ''
                                            for n in item.findall('ht:news_item', ns)])
            for item in wurzel.iter('item')]


def _kern(begriff):
    """Woerter, die im Titel/Trend vorkommen muessen (ohne Fuellwoerter)."""
    leer = {'the', 'and', 'for', 'with', 'what', 'how', 'why', 'from', 'that', 'this', 'free', 'really'}
    return [w for w in re.findall(r'[a-z0-9]+', begriff.lower()) if len(w) > 2 and w not in leer]


def google_treffer(begriff, heute_liste):
    kern = _kern(begriff)
    if not kern:
        return None
    for titel, news in heute_liste:
        text = ' '.join([titel] + news).lower()
        if all(re.search(r'\b' + re.escape(w) + r'\b', text) for w in kern):
            return titel
    return None


def yt_faktor(begriff):
    """Groesster Ausreisser-Faktor eines Videos, dessen Titel den Begriff wirklich enthaelt."""
    import trends
    kern = _kern(begriff)
    treffer = [v for v in trends.youtube_ausreisser([begriff], tage=30, je_begriff=15, top=15)
               if kern and all(w in v['titel'].lower() for w in kern)]
    return max((v['faktor'] for v in treffer), default=None), treffer[:2]


def kandidaten(kanal, themen, mit_trendfirmen=True):
    aus = [{'thema': x['thema'], 'begriff': x.get('trend_suche') or x.get('wikipedia') or x['thema'],
            'wikipedia': x.get('wikipedia'), 'eigen': True}
           for x in themen.laden() if x['kanal'] == kanal and x.get('status', 'bereit') == 'bereit']
    if mit_trendfirmen and kanal == 'business-origin-stories':
        import trends
        bekannt = {a.get('wikipedia') for a in aus}
        for titel, aufrufe, _ in trends.firmen_im_trend()[:FREIE_KANDIDATEN * 2]:
            if titel not in bekannt and len([a for a in aus if not a['eigen']]) < FREIE_KANDIDATEN:
                aus.append({'thema': '', 'begriff': titel, 'wikipedia': titel, 'eigen': False})
    return aus


def bewerten(liste, google_liste, heute=None):
    for k in liste:
        k['youtube'], k['beispiele'] = yt_faktor(k['begriff'])
        k['wiki'] = wiki_aufwind(k['wikipedia'], heute) if k.get('wikipedia') else None
        k['google'] = google_treffer(k['begriff'], google_liste)
        k['punkte'] = punkte(k['youtube'], k['wiki'], bool(k['google']), k['eigen'])
    return sorted(liste, key=lambda k: -k['punkte'])


def entscheiden(bewertet):
    """(thema, grund). '' = freie Wahl (Business: Trendfirmen, AI: Trend-Repos).
    None = keine einzige Quelle hat geantwortet -> Aufrufer nimmt die alte Reihenfolge."""
    if not any(k.get('youtube') or k.get('wiki') or k.get('google') for k in bewertet):
        return None, 'kein Trendsignal abrufbar'
    beste = bewertet[0]
    if beste['punkte'] - (BONUS_EIGEN if beste['eigen'] else 0) < SCHWELLE:
        return '', 'kein Kandidat mit echtem Trendsignal - freie Trendwahl'
    return beste['thema'], beschreibung(beste)


def beschreibung(k):
    teile = []
    if k.get('youtube'):
        teile.append(f"YouTube-Ausreisser {k['youtube']}x Kanalschnitt")
    if k.get('wiki'):
        teile.append(f"Wikipedia {round((k['wiki'] - 1) * 100):+d} % gegenueber Vormonat")
    if k.get('google'):
        teile.append(f"heute in Google Trends ({k['google']})")
    return f"{k['thema'] or k['begriff']}: {k['punkte']} Punkte - " + ', '.join(teile or ['ohne Signal'])


def waehlen(kanal, heute=None, themen=None):
    """Thema fuer den heutigen Lauf: (thema, bericht). Ein Ergebnis je Kanal und Tag.
    bericht ist None, wenn es nichts abzuwaegen gab (alte Reihenfolge, kein Netzabruf)."""
    if themen is None:
        import themen
    heute = heute or datetime.date.today()
    pfad = ORDNER / f'{kanal}-{heute.isoformat()}.json'
    try:
        alt = json.loads(pfad.read_text(encoding='utf-8'))
        offen = {x['thema'] for x in themen.laden() if x['kanal'] == kanal}
        if not alt['thema'] or alt['thema'] in offen:  # bereits erledigt -> neu waehlen
            return alt['thema'], alt
    except (OSError, ValueError, KeyError):
        pass
    try:
        liste = kandidaten(kanal, themen)
    except Exception as e:  # nie den Tageslauf am Trend-Check scheitern lassen
        print('Trend-Check fehlgeschlagen:', type(e).__name__, str(e)[:120])
        liste = []
    if not liste:
        return themen.nehmen(kanal), None
    try:
        bewertet = bewerten(liste, google_heute(), heute)
        thema, grund = entscheiden(bewertet)
    except Exception as e:  # nie den Tageslauf am Trend-Check scheitern lassen
        print('Trend-Check fehlgeschlagen:', type(e).__name__, str(e)[:120])
        thema, grund, bewertet = None, 'Trend-Check fehlgeschlagen', []
    if thema is None:
        thema = themen.nehmen(kanal)
        grund += ' - alte Reihenfolge der Warteschlange'
    bericht = {'datum': heute.isoformat(), 'thema': thema, 'grund': grund,
               'kandidaten': [{k: x.get(k) for k in ('thema', 'begriff', 'eigen', 'punkte', 'youtube', 'wiki',
                                                     'google', 'beispiele')} for x in bewertet]}
    ORDNER.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(bericht, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('Trend-Check:', grund)
    for x in bewertet[:6]:
        print('  ', beschreibung(x))
    return thema, bericht


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    waehlen(sys.argv[1])
