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
  HackerNews Wird es diese Woche auf Hacker News diskutiert (Punkte; Nutzerauftrag 10.10.2026)?
             Dort tauchen neue KI-Tools oft frueher auf als auf YouTube.

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
YT_FIRMEN = 3  # je Kandidat eine weitere YouTube-Suche (100 Einheiten des Tageskontingents)


# GEMESSEN 23.10.2026: Der Bericht von 10:36 UTC kannte nur die Geld-Titelvorlage; nach deren Lieferung nahm das
# Zusatzvideo um 15:53 eine zufaellige GitHub-Neuheit (nvidia/openshell), ohne neu nach Trends zu suchen.
NEU_NACH_S = 3 * 3600


def punkte(yt_faktor=None, wiki_aufwind=None, google=False, eigen=False, hn=None):
    """Reine Rechenregel (testbar). Jedes Signal hoechstens 5 Punkte, damit keins allein alles kippt.
    YouTube logarithmisch: 3x Kanalschnitt ~1,6, 10x ~3,3, 30x ~4,9 Punkte."""
    p = 0.0
    if yt_faktor:
        p += min(5.0, max(0.0, math.log2(yt_faktor) * 1.0))
    if wiki_aufwind:
        p += min(5.0, max(0.0, (wiki_aufwind - 1.0) * 2.5))  # +40 % ~1 Punkt, verdoppelt 2,5
    if google:
        p += 4.0
    if hn:
        p += min(4.0, max(0.0, math.log2(hn / 25)))  # 100 Punkte = 2, 400 Punkte = 4
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


# GEMESSEN 30.10.2026 (TikTok Business, 28 Videos): alle Firmen unter ~1.000 Wikipedia-Aufrufen/Tag liefen schwach
# (Moderna 260/Tag -> 243 Aufrufe, Squibb 344 -> 244, GE Vernova 779 -> 270, Verizon 917 -> 244); alle Videos mit
# 700+ Aufrufen hatten bekannte Marken (Hugo Boss 1.021 bis Netflix 7.633/Tag). Gilt nur fuer Trendfirmen,
# nie fuer eigene Themen des Nutzers.
BEKANNT_MIN = 1000


def bekanntheit(titel, heute=None):
    """Median der taeglichen Wikipedia-Aufrufe (60 Tage) = wie bekannt die Firma ist; None ohne Daten."""
    import trends
    heute = heute or datetime.date.today()
    ende, anfang = heute - datetime.timedelta(days=1), heute - datetime.timedelta(days=61)
    try:
        d = json.loads(trends._hole(
            'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/'
            f'{urllib.parse.quote(titel.replace(" ", "_"), safe="")}/daily/{anfang:%Y%m%d}/{ende:%Y%m%d}',
            trends.WIKI_KENNUNG))
        werte = [x['views'] for x in d.get('items', [])]
    except Exception:
        return None
    return round(statistics.median(werte)) if len(werte) >= 10 else None


def zu_unbekannt(k):
    return not k.get('eigen') and type(k.get('bekannt')) is int and k['bekannt'] < BEKANNT_MIN


GOOGLE_NEWS = 'Google News: '


def google_heute(land='US', news=False):
    """[(Trendbegriff, [Schlagzeilen])] aus dem offiziellen RSS-Feed; [] bei Ausfall.
    news=True haengt die heutigen Google-News-Wirtschaftsschlagzeilen an (Firmenkanaele).
    GEMESSEN 22.10.2026: Die Google-Tagestrends enthielten an keinem Tag eine Firma (Sportler, Serien,
    „playstation plus") - die Business-Stufe „Google" griff nie, obwohl Meta/Tesla in jeder Schlagzeile standen."""
    import trends
    try:
        wurzel = ElementTree.fromstring(trends._hole(f'https://trends.google.com/trending/rss?geo={land}'))
        ns = {'ht': 'https://trends.google.com/trending/rss'}
        aus = [(item.findtext('title') or '', [n.findtext('ht:news_item_title', namespaces=ns) or ''
                                               for n in item.findall('ht:news_item', ns)])
               for item in wurzel.iter('item')]
    except Exception as e:
        print('Google Trends nicht verfuegbar:', str(e)[:80])
        aus = []
    if news:
        aus += [(GOOGLE_NEWS + z, []) for z in trends.wirtschafts_schlagzeilen() if z]
    return aus


def _kern(begriff):
    """Woerter, die im Titel/Trend vorkommen muessen (ohne Fuellwoerter)."""
    leer = {'the', 'and', 'for', 'with', 'what', 'how', 'why', 'from', 'that', 'this', 'free', 'really'}
    return [w for w in re.findall(r'[a-z0-9]+', begriff.lower()) if len(w) > 2 and w not in leer]


def google_treffer(begriff, heute_liste):
    kern = _kern(begriff)
    if not kern:
        return None
    for titel, news in heute_liste:
        # GEMESSEN 22.10.2026 (Lauf 39810452976): das Praefix selbst traf 'Google' -> Thema ohne Anlass
        text = ' '.join([titel.removeprefix(GOOGLE_NEWS)] + news).lower()
        if all(re.search(r'\b' + re.escape(w) + r'\b', text) for w in kern):
            return titel
    return None


def hn_treffer(begriff, hn_liste):
    """Hoechste HN-Punktzahl einer Geschichte, deren Titel alle Kernwoerter enthaelt; sonst None."""
    kern = _kern(begriff)
    if not kern:
        return None
    return max((h['punkte'] for h in hn_liste
                if all(re.search(r'\b' + re.escape(w) + r'\b', h['titel'].lower()) for w in kern)), default=None)


def yt_faktor(begriff, zusatz=''):
    """Groesster Ausreisser-Faktor eines Videos, dessen Titel den Begriff wirklich enthaelt.
    GEMESSEN 09.10.2026 (Live-Vorschau): „Netflix" allein fand Serientrailer (79,5x) - das misst
    Interesse an Netflix-Serien, nicht an der Firmengeschichte. Darum mit Kanal-Zusatz suchen."""
    import trends
    kern = _kern(begriff)
    treffer = [v for v in trends.youtube_ausreisser([f'{begriff} {zusatz}'.strip()], tage=30, je_begriff=15, top=15)
               if kern and all(w in v['titel'].lower() for w in kern)]
    return max((v['faktor'] for v in treffer), default=None), treffer[:2]


def kandidaten(kanal, themen, mit_trendfirmen=True, google_liste=(), heute=None):
    aus = [{'thema': x['thema'], 'begriff': x.get('trend_suche') or x.get('wikipedia') or x['thema'],
            'wikipedia': x.get('wikipedia'), 'eigen': True}
           for x in themen.laden() if x['kanal'] == kanal and x.get('status', 'bereit') == 'bereit'
           and not themen.gespraech_grund(x['thema'])]
    if mit_trendfirmen and _profil(kanal).get('quelle') == 'wikipedia':
        import trends
        bekannt = {a.get('wikipedia') for a in aus}
        # Nutzer 27.10.2026: Firmengeschichten, die gerade auf YouTube laufen (Loctite), zuerst - die Bewertung
        # misst danach wie bei jeder Trendfirma den YouTube-Ausreisser („<Firma> story").
        yt = trendquellen(kanal).get('firmen_suche') or []
        for titel, _, _ in (trends.firmen_aus_youtube(yt) if yt else [])[:YT_FIRMEN]:
            if titel not in bekannt:
                bekannt.add(titel)
                aus.append({'thema': titel, 'begriff': titel, 'wikipedia': titel, 'eigen': False, 'trendfirma': True})
        for titel, aufrufe, _ in trends.firmen_im_trend()[:FREIE_KANDIDATEN * 2]:
            if titel not in bekannt and len([a for a in aus if not a['eigen']]) < FREIE_KANDIDATEN:
                # 21.10.2026 Nutzer: Trend im Fokus, fuer jeden Kanal. Vorher thema '' (nur Vorschlag an den Autor;
                # Claude nahm meist eine "klassische Marke" wie Boeing/Ford statt der Trendfirma).
                aus.append({'thema': titel, 'begriff': titel, 'wikipedia': titel, 'eigen': False, 'trendfirma': True})
    einstellung = trendquellen(kanal)
    if mit_trendfirmen and (einstellung.get('suche') or einstellung.get('google_news')):
        import trends
        aus += zuschauer_themen(einstellung, trends.gezeigte_themen(kanal), google_liste, heute)
    return aus


def _profil(kanal):
    """Kanalprofil kanaele/<kanal>.json ({} ohne Datei) - Trendquellen haengen am Profil, nicht am Namen."""
    try:
        import kanalstandard
        return kanalstandard.laden(Path('kanaele') / f'{kanal}.json')
    except (OSError, ValueError):
        return {}


TRENDQUELLEN = Path('trendquellen')


def trendquellen(kanal):
    """Zuschauer-Trendquellen aus trendquellen/<kanal>.json ({} ohne Datei = keine Zuschauer-Themen).
    Eigene Datei statt Kanalprofil: kanaele/<kanal>.json steckt im Cache-Schluessel (entwurf_cache.profil_key) -
    jede Aenderung an Suchbegriffen haette gepruefte Entwuerfe entwertet."""
    try:
        return json.loads((TRENDQUELLEN / f'{kanal}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


ZUSATZ = {'business-origin-stories': 'story'}  # Suchwinkel des Kanals, nicht Pflichtwort im Titel

# GEMELDET 19.10.2026 (Nutzer): „Bei KI muessen wir immer aktuell bleiben ... Die Pipeline muss immer solche
# Themen vom YouTube Trends oder Google Trends entnehmen." Vorher bewertete der Trend-Check beim KI-Kanal nur
# Telegram-Themen; bei leerer Liste kamen GitHub-/Hugging-Face-Neuheiten (19.10.: datalab-to/indra, 18.10.:
# mixelpixx/konnect) - Entwickler-Trends, nach denen auf YouTube kaum jemand sucht. GEMESSEN 19.10. (YouTube-
# Suche, 30 Tage): Claude-/ChatGPT-Videos mit 0,4-7 Mio. Aufrufen („Claude Code for free", „make money with AI").
# Jetzt: Zuschauer-Themen aus YouTube-Ausreissern der letzten 7 Tage und Google-Tagestrends, nur zu bekannten
# KI-Produkten (dazu gibt es Quellen und Suchinteresse) und nur mit belegbarer Recherche.
# Nutzer 19.10.2026: „hochskalierbar - ein neuer Account mit anderem Thema soll sich direkt anpassen". Darum stehen
# Suchbegriffe und Namen je Kanal in trendquellen/<kanal>.json, nicht im Code:
#   {"suche": [YouTube-Suchbegriffe], "namen": [Produkte/Firmen/Personen der Nische], "tage": 7, "dauer": "medium"}
# GEMESSEN 19.10.2026: Bei allen Laengen fuehrten Meme-Shorts („Badtameez Chatgpt Pt-7 #couplegoals"). 4-20-Min.-
# Videos tragen die Themen, nach denen Zuschauer suchen („Claude Just Dropped MOTION", neue Modelle).
TREND_STANDARD = {'tage': 7, 'dauer': 'medium', 'pruefen': 3, 'min_aufrufe': 5000, 'format_jeden': 2}
# Nutzer 19.10.2026: neben Neuheiten auch „richtig nutzen"/„Geld verdienen"-Themen. Jeden format_jeden-ten Tag
# bekommt ein echtes Format-Ausreisser-Thema (ab FORMAT_FAKTOR x Kanalschnitt) Vorrang vor Neuheiten.
FORMAT_FAKTOR = 2.0
BONUS_FORMAT = 10.0  # Formattag: Vorrang sicher, auch vor einer 60x-Neuheit
# GEMESSEN 21.10.2026: „ChatGPT | The Notice : A short film by Reema Kagti" (248x) wurde Thema "ChatGPT: ChatGPT".
KEIN_WERKZEUG = re.compile(r'\b(?:short film|trailer|music video|official video|lyrics|full movie)\b', re.I)
# GEMESSEN 27.10.2026 (Lauf 40490036813): „I Built My Own TV Operating System With Claude Code" - ein fremdes
# Bastelprojekt. Keine Quelle traegt es (Recherche fand Fuchsia/Android TV), eigene Erfahrung duerfen wir nicht
# erfinden: Story 4/10, der KI-Tag verging. Wie schon „I Made My Own VST Plugins" (19.10.).
# Danach stand „I Removed Every Ad From My Google TV using Claude" bereit - darum jede Ich-Tat in der Vergangenheit.
ERLEBNIS = re.compile(r"\bI(?:'ve|\s+have)?\s+(?i:(?:just\s+)?(?:built|made|wrote|ran|[a-z]+ed))\b|(?i:\bmy\s+own\b)")
# GEMESSEN 19.10.2026: „OpenAI alerta PF apos identificar ameacas contra Lula no ChatGPT" bestand trends._englisch
# (fast nur ASCII-Buchstaben). Ein englischer Titel enthaelt fast immer eines dieser Woerter.
ENGLISCH = re.compile(r"\b(?:the|a|an|to|is|in|of|for|and|with|my|your|you|how|this|it|i|just|vs|what|why|can|new|"
                      r"made|using|tested|master)\b", re.I)
# GEMESSEN 19.10.: „ChatGPT baut Dir Wasserzeichen in Deine Texte" (nur „in") und „... (In Telugu)" kamen durch
FREMDSPRACHE = re.compile(r"\b(?:hindi|telugu|tamil|urdu|bangla|bengali|marathi|kannada|malayalam|espa[nñ]ol|"
                          r"portugu[eê]s|deutsch|arabic)\b", re.I)


def englisch(titel):
    return len(set(w.lower() for w in ENGLISCH.findall(titel or ''))) >= 2 and not FREMDSPRACHE.search(titel or '')


def format_vorlage(e, tag, gezeigt=()):
    """Formattag ohne echten Format-Ausreisser: bewaehrtes Titelmuster (format_vorlagen) fuer ein Produkt mit
    offizieller Anleitung (anleitungen). Reihum nach Datum, schon gezeigte Themen ueberspringen."""
    import trends
    vorlagen, produkte = e.get('format_vorlagen') or [], sorted(e.get('anleitungen') or {})
    # Muster UND Produkt wechseln jedes Mal (nicht dreimal hintereinander „Geld verdienen")
    paare = list(dict.fromkeys((vorlagen[i % len(vorlagen)], produkte[i % len(produkte)])
                               for i in range(len(vorlagen) * len(produkte)))) if vorlagen and produkte else []
    for n in range(len(paare)):
        v, p = paare[(tag.toordinal() // max(1, int(e['format_jeden'])) + n) % len(paare)]
        thema = f'{p}: ' + v.format(produkt=p)
        if thema.lower() not in gezeigt:
            return {'thema': thema, 'produkt': p, 'google': None, 'youtube': None, 'beispiele': [],
                    'format': trends.format_art(v.format(produkt=p)) or 'anleitung', 'vorlage': True}
    return None


def name_im_text(text, namen):
    """Erster Nischen-Name im Text (Schreibweise wie in trendquellen) oder None; laengere Namen zuerst
    („Claude Code" vor „Claude")."""
    for p in sorted(namen, key=len, reverse=True):
        if re.search(r'(?<![\w-])' + re.escape(p) + r'(?![\w])', text or '', re.I):
            return p
    return None


def _zuschauer_thema(produkt, titel):
    """Produkt vorn: die Recherche (trends.themen_begriffe) nimmt die ersten Namen des Themas."""
    titel = re.sub(r'\s+', ' ', re.sub(r'#\S+', ' ', titel)).split(' | ')[0].strip(' -|:')
    return f'{produkt}: {titel}'


def zuschauer_themen_der_tage(kanal, tage, heute=None):
    """Gewaehlte Zuschauer-Trendthemen der letzten Tage (nur gespeicherte Berichte, kein Netzabruf).
    Der Vorrat schreibt nachts; ein solches Thema steht in keiner Warteschlange und waere sonst ungueltig."""
    heute = heute or datetime.date.today()
    aus = set()
    for n in range(tage):
        try:
            b = json.loads((ORDNER / f'{kanal}-{heute - datetime.timedelta(days=n)}.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if (b.get('zuschauer') or b.get('trend')) and b.get('thema'):
            aus.add(b['thema'])
        # Nachtvorrat schreibt auch die naechsten Trendthemen (Zusatzvideos) - die bleiben ebenso gueltig.
        aus |= {k['thema'] for k in b.get('kandidaten') or [] if k.get('thema') and stufe(k) <= 1}
    return aus


def zuschauer_themen(einstellung, gezeigt=(), google_liste=(), heute=None):
    """Kandidaten aus dem, was Zuschauer gerade schauen/suchen - je Name das staerkste Signal.
    einstellung = trendquellen/<kanal>.json; pruefen = hoechstens so viele recherchieren (je bis 8 Seitenabrufe)."""
    import trends
    e = {**TREND_STANDARD, **einstellung}
    namen = e.get('namen') or []
    roh = []
    # Nutzer 23.10.2026: „KI-Kanal kann solche Themen [Geld sparen/verdienen] von YouTube-Trends nehmen oder Google".
    # Die Google-Tagestrends nennen fast nie ein KI-Produkt - darum zusaetzlich die Google-News-Rubrik des Kanals.
    if e.get('google_news'):
        google_liste = list(google_liste) + [(GOOGLE_NEWS + z, []) for z in trends.news_schlagzeilen(e['google_news'])
                                             if z]
    for titel, news in google_liste:
        kopf = news[0] if news else titel.removeprefix(GOOGLE_NEWS)
        p = name_im_text(' '.join([titel.removeprefix(GOOGLE_NEWS)] + news[:1]), namen)
        if p:
            art = trends.format_art(kopf)
            roh.append({'thema': _zuschauer_thema(p, trends.ohne_betraege(kopf) if art in ('geld', 'sparen') else kopf),
                        'produkt': p, 'google': titel, 'youtube': None, 'beispiele': [], 'format': art})
    for v in trends.youtube_ausreisser(e.get('suche') or [], tage=e['tage'], je_begriff=15, top=40,
                                       dauer=e['dauer']):
        p = name_im_text(v['titel'], namen)
        # GEMESSEN 19.10.: Spam („ChatGPT Premium gratis freischalten", 1.794 Aufrufe = 15.6x) lag vorn
        if p and englisch(v['titel']) and not trends.SPAM_VIDEO.search(v['titel']) \
                and not KEIN_WERKZEUG.search(v['titel']) and not ERLEBNIS.search(v['titel']) \
                and (v.get('aufrufe') or 0) >= e['min_aufrufe']:
            art = trends.format_art(v['titel'])
            # Betraege im Titel sind fremde Behauptungen (Einkommen, Preise) - der Beleg kommt aus der Quelle
            titel = trends.ohne_betraege(v['titel']) if art in ('geld', 'sparen') else v['titel']
            roh.append({'thema': _zuschauer_thema(p, titel), 'produkt': p, 'google': None,
                        'youtube': v['faktor'], 'beispiele': [v], 'format': art})
    tag = heute or datetime.date.today()
    formattag = tag.toordinal() % max(1, int(e['format_jeden'])) == 0
    for k in roh:
        # Google-Schlagzeile = heutiges Suchinteresse, zaehlt wie ein YouTube-Ausreisser
        k['vorrang'] = bool(formattag and k.get('format')
                            and ((k['youtube'] or 0) >= FORMAT_FAKTOR or k.get('google')))
    if formattag and not any(k['vorrang'] for k in roh):
        ersatz = format_vorlage(e, tag, gezeigt)
        if ersatz:
            roh.append(dict(ersatz, vorrang=True))
    roh.sort(key=lambda k: (not k['vorrang'], -punkte(k['youtube'], google=bool(k['google']))))
    aus, produkte, geprueft = [], set(), 0
    for k in roh:
        schluessel = (k['produkt'], bool(k.get('format')))
        if schluessel in produkte or k['thema'].lower() in gezeigt or geprueft >= e['pruefen']:
            continue
        geprueft += 1
        # Ohne lesbare Quelle schreibt skript.py nichts (nur_quellen) - so ein Thema wuerde den Tag kosten.
        if not trends.thema_recherche(k['thema'], tage=30, maximal=1):
            print('Zuschauer-Thema ohne Quelle verworfen:', k['thema'][:80])
            continue
        produkte.add(schluessel)
        aus.append({'thema': k['thema'], 'begriff': k['thema'], 'wikipedia': None, 'eigen': False,
                    'zuschauer': True, 'youtube': k['youtube'], 'beispiele': k['beispiele'],
                    'google': k['google'], 'format': k.get('format') or '', 'vorrang': k.get('vorrang', False),
                    'vorlage': k.get('vorlage', False)})
    # GEMESSEN 19.10. (Live-Probe fuer 20.10.): kein Neuheiten-Trend mit Quelle (Argon schon gesendet, VST/Motion
    # ohne Beleg) -> der Lauf haette wieder eine zufaellige GitHub-Neuheit genommen. Dann lieber die Titelvorlage.
    if not aus and not any(k.get('vorlage') for k in roh):
        ohne_quelle = set(gezeigt)
        for _ in range(3):  # Anleitungsseite gerade nicht lesbar -> naechste Vorlage
            ersatz = format_vorlage(e, tag, ohne_quelle)
            if not ersatz:
                break
            if trends.thema_recherche(ersatz['thema'], tage=30, maximal=1):
                aus.append({'thema': ersatz['thema'], 'begriff': ersatz['thema'], 'wikipedia': None, 'eigen': False,
                            'zuschauer': True, 'youtube': None, 'beispiele': [], 'google': None,
                            'format': ersatz['format'], 'vorrang': True, 'vorlage': True})
                break
            ohne_quelle.add(ersatz['thema'].lower())
    return aus


def bewerten(liste, google_liste, heute=None, kanal='', hn_liste=()):
    # Eigene Telegram-Themen des Nutzers schlaegt kein Format-Vorrang (nur dessen Trendsignal)
    eigene = any(k.get('eigen') for k in liste)
    for k in liste:
        if k.get('zuschauer'):  # Signale stammen schon aus der Suche - kein zweiter YouTube-Abruf
            k['punkte'] = round(punkte(k['youtube'], google=bool(k['google']))
                                + (BONUS_FORMAT if k.get('vorrang') and not eigene else 0), 2)
            continue
        k['youtube'], k['beispiele'] = yt_faktor(k['begriff'], ZUSATZ.get(kanal, ''))
        k['wiki'] = wiki_aufwind(k['wikipedia'], heute) if k.get('wikipedia') else None
        if k.get('wikipedia') and not k.get('eigen') and _profil(kanal).get('quelle') == 'wikipedia':
            k['bekannt'] = bekanntheit(k['wikipedia'], heute)
        k['google'] = google_treffer(k['begriff'], google_liste)
        k['hn'] = hn_treffer(k['begriff'], hn_liste)
        k['punkte'] = punkte(k['youtube'], k['wiki'], bool(k['google']), k['eigen'], k['hn'])
    # Nutzerentscheidung 21.10.2026: „Bei Trend erst YouTube-Trends, wenn da nichts ist, dann Google Trends."
    # Vorher zaehlte die Punktsumme - ein Google-Treffer (4 Punkte) schlug einen 10x-YouTube-Ausreisser (3,3).
    for k in liste:
        k['stufe'] = stufe(k)
    return sorted(liste, key=lambda k: (k['stufe'], -k['punkte']))


def stufe(k):
    """0 = echter YouTube-Trend, 1 = nur Google (Tagestrends, bei Firmenkanaelen auch Google News), 2 = Rest (Wikipedia, Hacker News, Titelvorlage)."""
    if punkte(k.get('youtube')) >= SCHWELLE:
        return 0
    return 1 if k.get('google') else 2


def entscheiden(bewertet):
    """(thema, grund). '' = freie Wahl (Business: Trendfirmen, AI: Trend-Repos).
    None = keine einzige Quelle hat geantwortet -> Aufrufer nimmt die alte Reihenfolge."""
    if not any(k.get('youtube') or k.get('wiki') or k.get('google') or k.get('hn') or k.get('vorlage')
               for k in bewertet):
        return None, 'kein Trendsignal abrufbar'
    # 21.10.2026 Nutzer: „immer der Trend aus YouTube oder Google im Fokus" (alle Kanaele) - ohne solches
    # Signal nur eigene Telegram-Themen oder die bewaehrte Titelvorlage; sonst freie Wahl.
    for beste in bewertet:
        if _akzeptiert(beste):
            return beste['thema'], beschreibung(beste)
    return '', 'kein Kandidat mit echtem Trendsignal - freie Trendwahl'


def _akzeptiert(k):
    if not k.get('thema') or k['punkte'] - (BONUS_EIGEN if k['eigen'] else 0) < SCHWELLE:
        return False
    if not (k['eigen'] or k.get('vorlage') or stufe(k) <= 1):
        return False
    if not k['eigen'] and _wiederholung(k.get('_kanal', ''), k['thema']):
        return False
    return not zu_unbekannt(k)


# Nutzer 30.10.2026: "Claude auch die Themenauswahl - ohne viel Token, drei Tage Vorrat". Die Regeln liefern die
# geprueften Kandidaten (Trendsignal, Bekanntheit, keine Wiederholung); Claude ordnet sie EINMAL fuer drei Tage nach
# Geschichte (BMW-Toepfe 728 TikTok-Aufrufe, Walmart-Start 254 - beide Trend, die Formel sah keinen Unterschied).
PLAN = Path('verlauf/themenplan')
PLAN_TAGE = 3
KURZLISTE = 8
PLAN_SCHEMA = {'type': 'OBJECT', 'properties': {'reihenfolge': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
                                                'begruendung': {'type': 'STRING'}},
               'required': ['reihenfolge', 'begruendung']}


def _publikum(kanal, n=4):
    """Kurz: staerkste und schwaechste TikTok-Themen des Kanals (echte Aufrufe) als Massstab fuer Claude."""
    try:
        tt = list((json.loads((Path('erfolg') / f'{kanal}.json').read_text(encoding='utf-8')).get('tiktok') or {}).values())
    except (OSError, ValueError, AttributeError):
        return ''
    tt = sorted((v for v in tt if isinstance(v.get('aufrufe'), int) and v.get('titel')), key=lambda v: -v['aufrufe'])
    if len(tt) < 2 * n:
        return ''
    def zeile(vs):
        return '; '.join(f"{v['titel'][:60]} ({v['aufrufe']})" for v in vs)
    return f'OUR REAL TIKTOK RESULTS - strongest: {zeile(tt[:n])}. Weakest: {zeile(tt[-n:])}.\n'


def plan_auftrag(kanal, kurz):
    import prompts
    liste = '\n'.join(f"- {k['thema']} ({beschreibung(k)[:140]}"
                      + (f"; Wikipedia {k['bekannt']} views/day" if type(k.get('bekannt')) is int else '')
                      + ('; the owner asked for it' if k.get('eigen') else '') + ')' for k in kurz)
    return (prompts.DATEN + f'TASK: You are the editor of the short-video channel "{_profil(kanal).get("name", kanal)}". '
            f'Order up to {PLAN_TAGE} topics from this checked list for the next {PLAN_TAGE} days, best first. Pick '
            'topics that make viewers stop scrolling: a world-famous name with a surprising, little-known story people '
            'repeat to friends. Avoid topics whose only story is current corporate news. Use ONLY exact topic names '
            'from the list.\n' + _publikum(kanal) + 'CANDIDATES:\n' + liste)


def redaktion(kanal, bewertet, heute, ki=None):
    """(thema, grund) aus dem Drei-Tage-Plan oder None (dann entscheidet die Formel wie bisher).
    Claude wird hoechstens alle PLAN_TAGE gefragt und nie, wenn es weniger als zwei Kandidaten gibt."""
    kurz = [k for k in bewertet if _akzeptiert(k)][:KURZLISTE]
    nach_thema = {k['thema']: k for k in kurz}
    pfad = PLAN / f'{kanal}.json'
    try:
        plan = json.loads(pfad.read_text(encoding='utf-8'))
        if not 0 <= (heute - datetime.date.fromisoformat(plan['erstellt'])).days < PLAN_TAGE:
            plan = None
    except (OSError, ValueError, KeyError, TypeError):
        plan = None
    offen = [t for t in (plan or {}).get('reihenfolge', []) if t in nach_thema]
    if plan and not offen:
        return None  # Plan aufgebraucht/nicht mehr im Trend: bis zum Ablauf die Formel, keine neue Anfrage
    if not offen:
        if len(kurz) < 2:
            return None
        if ki is None:
            import claude_ki
            if not claude_ki.verfuegbar():
                return None
            ki = lambda auftrag: claude_ki.schreiben(auftrag, PLAN_SCHEMA, zeit=120)[0]
        try:
            antwort = ki(plan_auftrag(kanal, kurz)) or {}
        except Exception as e:  # nie den Tageslauf an der Redaktion scheitern lassen
            print('Claude-Themenplan nicht moeglich:', type(e).__name__, str(e)[:120])
            return None
        reihenfolge = list(dict.fromkeys(t for t in antwort.get('reihenfolge') or [] if t in nach_thema))[:PLAN_TAGE]
        if not reihenfolge:
            print('Claude-Themenplan ohne gueltiges Thema - Formel entscheidet')
            return None
        plan = {'erstellt': heute.isoformat(), 'reihenfolge': reihenfolge,
                'begruendung': str(antwort.get('begruendung', ''))[:400]}
        PLAN.mkdir(parents=True, exist_ok=True)
        pfad.write_text(json.dumps(plan, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print('Claude-Themenplan:', reihenfolge, '-', plan['begruendung'][:200])
        offen = reihenfolge
    k = nach_thema[offen[0]]
    return k['thema'], f"Claude-Redaktion (Plan vom {plan['erstellt']}): {beschreibung(k)}"


def _wiederholung(kanal, thema):
    try:
        import themen
        return bool(kanal and themen.wiederholung_gesperrt(kanal, thema))
    except Exception:
        return False


def trend_themen(kanal, heute=None):
    """Noch nicht (60 Tage) gelieferte YouTube-/Google-Trendthemen des Tages, YouTube zuerst - fuer
    Zusatzvideos und den Nachtvorrat (Nutzer 21.10.2026: „Harness Engineering 101 interessiert niemanden")."""
    heute = heute or datetime.date.today()
    try:
        b = json.loads((ORDNER / f'{kanal}-{heute.isoformat()}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    aus = []
    for k in sorted(b.get('kandidaten') or [], key=lambda k: (stufe(k), -(k.get('punkte') or 0))):
        t = k.get('thema') or ''
        if t and stufe(k) <= 1 and t not in aus and _taugt(k) and not zu_unbekannt(k) and not _wiederholung(kanal, t):
            aus.append(t)
    return aus


def _taugt(k):
    """Kein leeres Thema ("ChatGPT: ChatGPT" aus einem Kurzfilm-Titel) - gilt auch fuer schon gespeicherte Berichte."""
    produkt, _, rest = (k.get('thema') or '').partition(': ')
    if rest and rest.strip().lower() == produkt.strip().lower():
        return False
    return not any(KEIN_WERKZEUG.search(b.get('titel') or '') or ERLEBNIS.search(b.get('titel') or '')
                   for b in k.get('beispiele') or [])


def beschreibung(k):
    teile = []
    if k.get('youtube'):
        teile.append(f"YouTube-Ausreisser {k['youtube']}x Kanalschnitt")
    if k.get('wiki'):
        teile.append(f"Wikipedia {round((k['wiki'] - 1) * 100):+d} % gegenueber Vormonat")
    if k.get('google'):
        teile.append(f"heute in Google News ({k['google'][len(GOOGLE_NEWS):]})"
                     if k['google'].startswith(GOOGLE_NEWS) else f"heute in Google Trends ({k['google']})")
    if k.get('hn'):
        teile.append(f"Hacker News {k['hn']} Punkte")
    if k.get('format'):  # Telegram zeigt, warum heute ein Anleitungs-/Geld-Thema statt einer Neuheit
        teile.append({'geld': 'Format Geld verdienen', 'sparen': 'Format Geld sparen',
                      'anleitung': 'Format richtig nutzen'}[k['format']]
                     + (' (Formattag)' if k.get('vorrang') else '')
                     + (', bewaehrte Titelvorlage + offizielle Anleitung' if k.get('vorlage') else ''))
    return f"{k['thema'] or k['begriff']}: {k['punkte']} Punkte - " + ', '.join(teile or ['ohne Signal'])


def bericht_veraltet(kanal, heute=None, jetzt=None):
    """True, wenn der Tagesbericht fehlt oder aelter als NEU_NACH_S ist (Zusatzvideo am Nachmittag)."""
    heute = heute or datetime.date.today()
    jetzt = jetzt or datetime.datetime.now(datetime.timezone.utc)
    try:
        b = json.loads((ORDNER / f'{kanal}-{heute.isoformat()}.json').read_text(encoding='utf-8'))
        return (jetzt - datetime.datetime.fromisoformat(b['berechnet'])).total_seconds() > NEU_NACH_S
    except (OSError, ValueError, KeyError, TypeError):
        return True


def heute_gescheitert(kanal, thema, heute=None, ordner=Path('verlauf/messungen')):
    """Gesperrte Laeufe von heute mit diesem Trendthema (messungen: trendcheck = '<Thema>: <Punkte> ...')."""
    if heute is None:
        from zoneinfo import ZoneInfo
        heute = datetime.datetime.now(ZoneInfo('Europe/Berlin')).date()
    try:
        laeufe = json.loads((Path(ordner) / f'{kanal}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 0
    # genau "<Thema>: <Zahl> Punkte" - Themen mit Doppelpunkt ("Claude: ...") duerfen nicht als "Claude" zaehlen
    muster = re.compile(re.escape(thema) + r': \d+(?:\.\d+)? Punkte')
    return sum(1 for e in laeufe if e.get('datum') == heute.isoformat() and e.get('status') == 'gesperrt'
               and muster.match(str(e.get('trendcheck') or '')))


def waehlen(kanal, heute=None, themen=None, neu=False):
    """Thema fuer den heutigen Lauf: (thema, bericht). Ein Ergebnis je Kanal und Tag.
    bericht ist None, wenn es nichts abzuwaegen gab (alte Reihenfolge, kein Netzabruf).
    neu=True rechnet den Tagesbericht trotzdem neu (Zusatzvideo, Trend des Morgens schon geliefert)."""
    if themen is None:
        import themen
    heute = heute or datetime.date.today()
    pfad = ORDNER / f'{kanal}-{heute.isoformat()}.json'
    try:
        if neu:
            raise KeyError('Neuberechnung angefordert')
        alt = json.loads(pfad.read_text(encoding='utf-8'))
        offen = {x['thema'] for x in themen.laden() if x['kanal'] == kanal}
        # 22.10.2026: Berichte von Firmenkanaelen ohne Google-News-Abgleich (vor 3e2a714) neu berechnen -
        # sonst bliebe es den ganzen Tag bei der freien Wahl (Walmart), obwohl Meta in den Schlagzeilen steht.
        if _profil(kanal).get('quelle') == 'wikipedia' and not alt.get('google_news'):
            raise KeyError('ohne Google News berechnet')
        # 27.10.2026: Bericht des Morgens hatte ein Bastelprojekt gewaehlt - neue Filter gelten auch fuer ihn.
        gewaehlt = next((x for x in alt.get('kandidaten') or [] if x.get('thema') == alt['thema']), None)
        if gewaehlt and not _taugt(gewaehlt):
            raise KeyError('gewaehltes Thema taugt nicht')
        if not themen.gespraech_grund(alt['thema']) and (not alt['thema'] or alt['thema'] in offen
                                                         or alt.get('zuschauer') or alt.get('trend')):
            # Bereits erledigte Ideen und alte Fehlklassifikationen neu waehlen.
            return alt['thema'], alt
    except (OSError, ValueError, KeyError):
        pass
    google_liste = None
    firmen = _profil(kanal).get('quelle') == 'wikipedia'
    try:
        google_liste = google_heute(news=firmen)
        liste = kandidaten(kanal, themen, google_liste=google_liste, heute=heute)
    except Exception as e:  # nie den Tageslauf am Trend-Check scheitern lassen
        print('Trend-Check fehlgeschlagen:', type(e).__name__, str(e)[:120])
        liste = []
    if not liste:
        return themen.nehmen(kanal), None
    try:
        import trends
        bewertet = bewerten(liste, google_heute(news=firmen) if google_liste is None else google_liste, heute, kanal,
                            trends.hn_geschichten())
        for x in bewertet:
            x['_kanal'] = kanal
        thema, grund = entscheiden(bewertet)
        if thema:
            thema, grund = redaktion(kanal, bewertet, heute) or (thema, grund)
    except Exception as e:  # nie den Tageslauf am Trend-Check scheitern lassen
        print('Trend-Check fehlgeschlagen:', type(e).__name__, str(e)[:120])
        thema, grund, bewertet = None, 'Trend-Check fehlgeschlagen', []
    if thema is None:
        thema = themen.nehmen(kanal)
        grund += ' - alte Reihenfolge der Warteschlange'
    bericht = {'datum': heute.isoformat(), 'thema': thema, 'grund': grund, 'google_news': firmen,
               'berechnet': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
               'zuschauer': any(x.get('zuschauer') and x['thema'] == thema for x in bewertet),
               'trend': any(x.get('thema') == thema and thema and x.get('stufe', 2) <= 1 for x in bewertet),
               'kandidaten': [{k: x.get(k) for k in ('thema', 'begriff', 'eigen', 'punkte', 'youtube', 'wiki',
                                                     'google', 'hn', 'beispiele', 'stufe', 'bekannt')} for x in bewertet]}
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
