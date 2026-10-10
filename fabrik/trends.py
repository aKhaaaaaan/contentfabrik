"""Trend- und Quellen-Baustein: Was ist gerade gefragt - und welche Fakten
sind aktuell? Alles kostenlos.

  youtube_ausreisser()  Videos der Nische, die weit ueber dem Durchschnitt
                        ihres Kanals liegen (YouTube Data API, YOUTUBE_API_KEY)
  google_trends()       Tagestrends je Land (offizieller RSS-Feed, ohne Schluessel)
  ki_quellen()          aktuelle Fakten fuer KI-Themen: GitHub, Hugging Face,
                        Hacker News (alle oeffentlich)

Jede Funktion faellt still auf [] zurueck, wenn die Quelle nicht antwortet -
dann entscheidet die KI ohne diese Hinweise, das Video entsteht trotzdem.
"""
import html, json, os, re, time, datetime, urllib.error, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from xml.etree import ElementTree

UNGEEIGNET = re.compile(r'uncensored|abliterated|nsfw|porn|nude|lewd|hentai|jailbreak', re.I)
# Wikimedia verlangt eine Kennung mit Kontaktweg
WIKI_KENNUNG = {'User-Agent': 'Contentfabrik/1.0 (private video tool; github.com/aKhaaaaaan)'}
KENNUNG = {'User-Agent': 'Contentfabrik/1.0 (privates Video-Tool)'}


def _hole(url, kopf=None, zeit=30):
    req = urllib.request.Request(url, headers={**KENNUNG, **(kopf or {})})
    with urllib.request.urlopen(req, timeout=zeit) as r:
        return r.read()


def _englisch(titel):
    # GEMESSEN 02.10.2026: Trotz relevanceLanguage=en kamen Titel in Hindi
    # und Bengali - die taugen nicht als Vorbild fuer einen englischen Kanal.
    buchst = [z for z in titel if z.isalpha()]
    return bool(buchst) and sum(z.isascii() for z in buchst) / len(buchst) > 0.9


def youtube_ausreisser(suchbegriffe, tage=30, je_begriff=15, top=10):
    """Ausreisser = Aufrufe des Videos / Durchschnitt je Video seines Kanals.
    Ein Video mit 2 Mio. Aufrufen auf einem Kanal mit 20.000 im Schnitt ist ein
    Treffer der IDEE; 2 Mio. auf einem Kanal mit 3 Mio. im Schnitt nicht."""
    schluessel = os.environ.get('YOUTUBE_API_KEY')
    if not schluessel or not suchbegriffe:
        return []
    seit = (datetime.datetime.utcnow() - datetime.timedelta(days=tage)).strftime('%Y-%m-%dT%H:%M:%SZ')
    basis = 'https://www.googleapis.com/youtube/v3/'
    videos = {}
    try:
        for q in suchbegriffe:
            d = json.loads(_hole(basis + 'search?' + urllib.parse.urlencode({
                'part': 'snippet', 'q': q, 'type': 'video', 'order': 'viewCount', 'videoDuration': 'short',
                'publishedAfter': seit, 'relevanceLanguage': 'en', 'regionCode': 'US', 'maxResults': je_begriff, 'key': schluessel})))
            for it in d.get('items', []):
                titel = html.unescape(it['snippet']['title'])
                if not _englisch(titel):
                    continue
                videos[it['id']['videoId']] = {'titel': titel, 'kanal': it['snippet']['channelId']}
        if not videos:
            return []
        stat = json.loads(_hole(basis + 'videos?' + urllib.parse.urlencode({
            'part': 'statistics', 'id': ','.join(list(videos)[:50]), 'key': schluessel})))
        for it in stat.get('items', []):
            videos[it['id']]['aufrufe'] = int(it['statistics'].get('viewCount', 0))
        kanaele = {v['kanal'] for v in videos.values()}
        kst = json.loads(_hole(basis + 'channels?' + urllib.parse.urlencode({
            'part': 'statistics', 'id': ','.join(list(kanaele)[:50]), 'key': schluessel})))
        schnitt = {}
        for it in kst.get('items', []):
            s = it['statistics']
            schnitt[it['id']] = int(s.get('viewCount', 0)) / max(1, int(s.get('videoCount', 1)))
        aus = []
        for vid, v in videos.items():
            if 'aufrufe' not in v:
                continue
            v['faktor'] = round(v['aufrufe'] / max(1, schnitt.get(v['kanal'], 1)), 1)
            aus.append({'titel': v['titel'], 'aufrufe': v['aufrufe'], 'faktor': v['faktor'], 'id': vid})
        aus.sort(key=lambda x: (x['faktor'], x['aufrufe']), reverse=True)
        return aus[:top]
    except Exception as e:
        print('YouTube-Trends nicht verfuegbar:', str(e).replace(schluessel, '***'))
        return []


def google_trends(land='US', top=20):
    try:
        wurzel = ElementTree.fromstring(_hole(f'https://trends.google.com/trending/rss?geo={land}'))
        ns = {'ht': 'https://trends.google.com/trending/rss'}
        aus = []
        for item in wurzel.iter('item'):
            t = item.findtext('title')
            v = item.findtext('ht:approx_traffic', namespaces=ns) or ''
            if t:
                aus.append(f'{t} ({v})' if v else t)
        return aus[:top]
    except Exception as e:
        print('Google Trends nicht verfuegbar:', e)
        return []


def beschreibung(q):
    """Primaerquelle lesen: Metadaten allein belegen keinen praktischen Nutzen."""
    q = dict(q)
    name = q.get('name', '')
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', name):
        return q
    url = (f'https://huggingface.co/{name}/raw/main/README.md' if q['quelle'] == 'Hugging Face'
           else f'https://raw.githubusercontent.com/{name}/HEAD/README.md' if q['quelle'] == 'GitHub' else '')
    if not url:
        return q
    try:
        roh = _hole(url, zeit=12).decode('utf-8', 'replace')[:160_000]
        # Code, Bild-Adressen und Benchmarktabellen sind keine Nutzenerklaerung.
        prose = re.sub(r'```.*?```', '', roh, flags=re.S)
        prose = re.sub(r'<(?:script|style)\b.*?</(?:script|style)>', '', prose, flags=re.I | re.S)
        prose = re.sub(r'<[^>]+>', ' ', prose)
        prose = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', prose)
        prose = '\n'.join(l for l in prose.splitlines() if not l.lstrip().startswith('|'))
        prose = re.sub(r'\n{3,}', '\n\n', prose).strip()
        if len(prose.split()) >= 80:
            q['beschreibung_url'] = url
            q['belegt'] = True
            q['text'] += '\nPRIMARY MODEL/PROJECT DESCRIPTION (not independently tested):\n' + prose[:6500]
    except Exception as e:
        print('Modellbeschreibung nicht verfuegbar:', name, type(e).__name__)
    return q


def schwerpunkt(kanal, heute=None):
    """Aktiver Themen-Schwerpunkt des Kanalprofils {'begriffe': [...], 'bis': 'JJJJ-MM-TT'} oder None."""
    sp = kanal.get('themen_schwerpunkt') or {}
    heute = heute or datetime.date.today().isoformat()
    return sp if sp.get('begriffe') and str(sp.get('bis', '')) >= heute else None


SPAM = re.compile(r'setup|crack|keygen|download|guide|companion|activat|license[- ]?key|free[- ]?full', re.I)
KI_BEZUG = re.compile(r'\bAI\b|\bLLM|GPT|machine learning|\bagent|ollama|openai|claude', re.I)
SCHWERPUNKT_THEMEN = ['personal-finance', 'accounting', 'budget', 'invoice', 'finance', 'expense-tracker',
                      'bookkeeping', 'fintech', 'investing', 'receipts', 'tax']


def schwerpunkt_quellen(begriffe, themen=SCHWERPUNKT_THEMEN, tage=21):
    """Bekannte, aktiv gepflegte Werkzeuge eines Themenfelds MIT KI-Bezug (GitHub-Themen).

    GEMESSEN 09.10.2026: neue Finanz-KI-Repos (30 Tage, >30 Sterne) gab es kaum - Treffer waren
    Aurelio (schon Video) und Spam wie „TaxAct-Windows-Setup-Companion"/„...-Crack". Etablierte
    Projekte (>800 Sterne, in 21 Tagen gepflegt) mit KI in der Beschreibung liefern echte Themen:
    TaxHacker (KI-Buchhalter), BeeCount, Invoice Ninja, Kimai."""
    aus, gesehen = [], set()
    kopf = {'Accept': 'application/vnd.github+json'}
    if os.environ.get('GITHUB_TOKEN'):
        kopf['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    gepflegt = (datetime.date.today() - datetime.timedelta(days=tage)).isoformat()
    for thema in themen:
        try:
            d = json.loads(_hole('https://api.github.com/search/repositories?' + urllib.parse.urlencode({
                'q': f'topic:{thema} stars:>300 pushed:>{gepflegt}', 'sort': 'stars', 'order': 'desc',
                'per_page': 10}), kopf))
        except Exception as e:
            print('Schwerpunkt-Suche nicht verfuegbar:', thema, e)
            continue
        for r in d.get('items', []):
            text = f"{r.get('description') or ''} {' '.join(r.get('topics') or [])}"
            if r['full_name'] in gesehen or SPAM.search(r['full_name']) or not KI_BEZUG.search(text):
                continue
            gesehen.add(r['full_name'])
            aus.append({'quelle': 'GitHub', 'name': r['full_name'], 'url': r['html_url'],
                        'zahl': r['stargazers_count'],
                        'text': f"{r.get('description') or ''} - {r['stargazers_count']} stars, license: "
                                f"{(r.get('license') or {}).get('spdx_id', 'unknown')}, actively maintained"})
    return aus


HN_VORRANG = 100  # ab so vielen Punkten ist ein Projekt auf HN „im Gespraech" und kommt nach vorn
HN_SUCHEN = (('', 'show_hn'), ('AI', 'story'), ('LLM', 'story'), ('open source AI', 'story'), ('AI agent', 'story'))
# GEMESSEN 10.10.2026 (Live-Abfrage): Die Volltextsuche lieferte auch „The lamps in my house" und
# F1-Softwarefehler - darum muss der TITEL selbst ein KI-Wort enthalten.
KI_WORT = re.compile(r'\b(?:AI|A\.I\.|LLMs?|GPT\w*|agents?|agentic|models?|ML|machine learning|neural|diffusion|'
                     r'chatbots?|Claude|Gemini|ChatGPT|Llama|Mistral|Qwen|DeepSeek|embedding\w*|transformer\w*|'
                     r'inference|RAG|copilot|speech-to-text|text-to-speech|TTS|OCR)\b', re.I)


def hn_geschichten(tage=7, mindest=50):
    """KI-Geschichten der letzten Tage von Hacker News (offizielle Algolia-API, kostenlos, ohne
    Schluessel), nach Punkten sortiert, ohne Dubletten. [] bei Ausfall."""
    ab = int(time.time()) - tage * 86400
    gesehen, aus = set(), []
    for suche, tags in HN_SUCHEN:
        try:
            d = json.loads(_hole('https://hn.algolia.com/api/v1/search?' + urllib.parse.urlencode({
                'query': suche, 'tags': tags, 'numericFilters': f'created_at_i>{ab},points>{mindest}',
                'hitsPerPage': 30}), zeit=15))
        except Exception as e:
            print('Hacker News nicht verfuegbar:', type(e).__name__)
            continue
        for h in d.get('hits', []):
            titel = re.sub(r'^(?:Show|Ask|Tell) HN:\s*', '', h.get('title') or '')
            if h.get('objectID') in gesehen or not KI_WORT.search(titel):
                continue
            gesehen.add(h.get('objectID'))
            aus.append({'titel': titel, 'url': h.get('url') or '', 'punkte': h.get('points') or 0,
                        'kommentare': h.get('num_comments') or 0, 'datum': (h.get('created_at') or '')[:10]})
    return sorted(aus, key=lambda h: -h['punkte'])


def github_repo(url):
    """'owner/repo' aus einer GitHub-Projektadresse, sonst None."""
    m = re.match(r'https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?(?:[#?].*)?$', url or '')
    return f'{m.group(1)}/{m.group(2)}' if m and m.group(1).lower() not in ('orgs', 'topics', 'sponsors') else None


def ki_quellen(tage=7, maximal=None, bevorzugt=None):
    """Aktuelle KI-Neuheiten mit Beschreibung - die EINZIGEN Fakten, die der
    Kanal „AI Tools Explained" verwenden darf (Konzept: Quellen-Methode).

    bevorzugt: Begriffe eines befristeten Schwerpunkts (Nutzerentscheidung 09.10.2026: eine Woche
    Finanz-/Spar-/Business-KI-Tools testen). Passende Quellen kommen nach vorn; eine Zusatzsuche
    ueber 30 Tage findet sie, weil sie unter den allgemeinen Sterne-Spitzen selten sind."""
    aus = []
    seit = (datetime.date.today() - datetime.timedelta(days=tage)).isoformat()
    if bevorzugt:
        aus += schwerpunkt_quellen(bevorzugt)
    try:  # GitHub: neue Repos zu KI, nach Sternen
        kopf = {'Accept': 'application/vnd.github+json'}
        if os.environ.get('GITHUB_TOKEN'):
            kopf['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
        d = json.loads(_hole('https://api.github.com/search/repositories?' + urllib.parse.urlencode({
            'q': f'topic:ai created:>{seit} stars:>100', 'sort': 'stars', 'order': 'desc', 'per_page': 10}), kopf))
        for r in d.get('items', []):
            aus.append({'quelle': 'GitHub', 'name': r['full_name'], 'url': r['html_url'], 'zahl': r['stargazers_count'],
                        'text': f"{r.get('description') or ''} - {r['stargazers_count']} stars, license: "
                                f"{(r.get('license') or {}).get('spdx_id', 'unknown')}, created {r['created_at'][:10]}"})
    except Exception as e:
        print('GitHub nicht verfuegbar:', e)
    try:  # Hugging Face: Modelle mit steigendem Interesse
        d = json.loads(_hole('https://huggingface.co/api/models?sort=trendingScore&limit=10'))
        for m in d:
            aus.append({'quelle': 'Hugging Face', 'name': m['id'], 'url': f"https://huggingface.co/{m['id']}", 'zahl': m.get('likes', 0),
                        # GEMESSEN: „null Downloads" wurde vorgelesen (neue Modelle zaehlen 30 Tage)
                        'text': f"task: {m.get('pipeline_tag', 'unknown')}, {m.get('likes', 0)} likes"
                                + (f", {m['downloads']} downloads" if m.get('downloads') else '')})
    except Exception as e:
        print('Hugging Face nicht verfuegbar:', e)
    # Hacker News: worueber Technik-Leute GERADE reden (Nutzerauftrag 10.10.2026). Ein dort
    # diskutiertes GitHub-Projekt wird eine normale GitHub-Quelle (README als Beleg) und kommt nach vorn.
    hn = hn_geschichten(tage)
    hn_repo = {}
    for h in hn:
        repo = github_repo(h['url'])
        if repo and repo.lower() not in hn_repo:
            hn_repo[repo.lower()] = h
    for q in aus:
        h = hn_repo.pop(q['name'].lower(), None) if q['quelle'] == 'GitHub' else None
        if h:
            q['hn'] = h['punkte']
            q['text'] += f" - discussed on Hacker News: {h['punkte']} points ({h['titel'][:120]})"
    for repo, h in list(hn_repo.items())[:4]:
        aus.append({'quelle': 'GitHub', 'name': repo, 'url': f'https://github.com/{repo}', 'zahl': h['punkte'],
                    'hn': h['punkte'],
                    'text': f"Hacker News: \"{h['titel'][:160]}\" - {h['punkte']} points, "
                            f"{h['kommentare']} comments, {h['datum']}"})
    for h in hn:
        if not github_repo(h['url']) and h['url']:
            aus.append({'quelle': 'Hacker News', 'name': h['titel'][:120], 'url': h['url'],
                        'text': f"{h['punkte']} points, {h['kommentare']} comments"})
    # Stabil: auf HN stark diskutierte Projekte zuerst, sonst Reihenfolge wie bisher
    aus.sort(key=lambda q: -(q.get('hn') or 0) if (q.get('hn') or 0) >= HN_VORRANG else 0)
    # GEMESSEN 02.10.2026: Unter den Hugging-Face-Trends war ein „Uncensored"-
    # Modell. Fuer einen werbefaehigen Kanal ungeeignet - nie als Fakt anbieten.
    # GEMESSEN: „AIHOT" (Beschreibung auf Chinesisch) landete auf Platz 1 - fuer
    # ein englisches Publikum unverstaendlich, die Karte zeigt fremde Schrift.
    geeignet = [q for q in aus if not UNGEEIGNET.search(q['name'] + ' ' + q['text'])
                and _englisch(q['name'] + ' ' + q['text'])]
    if bevorzugt:
        muster = re.compile('|'.join(re.escape(b) for b in bevorzugt), re.I)
        # stabil sortiert: Schwerpunkt-Treffer zuerst, sonst Reihenfolge wie bisher
        geeignet.sort(key=lambda q: not muster.search(q['name'] + ' ' + q['text']))
        doppelt = set()
        geeignet = [q for q in geeignet if not (q['url'] in doppelt or doppelt.add(q['url']))]
    if maximal is not None:
        belegt = []
        for q in geeignet[:6]:
            q = beschreibung(q)
            if q.get('belegt'):
                belegt.append(q)
            if len(belegt) >= maximal:
                break
        return belegt
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(beschreibung, geeignet))


def wikipedia(titel, grenze=7000):
    """Geschichte einer Firma aus der englischen Wikipedia (offizielle API,
    kostenlos). GEMESSEN 03.10.2026: Aus dem KI-Gedaechtnis geschriebene
    Firmengeschichten fielen zweimal durch die Pruefung (Nintendo, Wrigley:
    erfundene Zahl, Legenden, „overnight"). Jetzt: nur Fakten aus diesem Text.
    Fakten sind frei; in der Beschreibung steht trotzdem die Quelle."""
    try:
        adresse = 'https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'query', 'prop': 'extracts|info', 'explaintext': 1, 'redirects': 1, 'inprop': 'url',
            'titles': titel, 'format': 'json'})
        # GEMESSEN 05.10.2026: auf GitHub-Servern (geteilte IP-Adressen) blieb 429 auch nach
        # 5/15 s - laenger warten.
        for warte in (0, 10, 30, 60):  # 429 Too Many Requests
            try:
                import time as _t; _t.sleep(warte)
                d = json.loads(_hole(adresse, WIKI_KENNUNG))
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or warte == 60:
                    raise
        seite = next(iter(d['query']['pages'].values()))
        text = seite.get('extract') or ''
        if len(text) < 500:
            return None
        # Bevorzugt die Abschnitte zur Geschichte; sonst der Anfang des Artikels
        teile = re.split(r'\n(==+ [^=]+ ==+)\n', text)
        auswahl, nimm = [teile[0][:1500]], False
        for i in range(1, len(teile) - 1, 2):
            kopf = teile[i].strip('= ').lower()
            if teile[i].startswith('== '):
                nimm = any(w in kopf for w in ('history', 'origin', 'founding', 'early', 'background'))
            if nimm:
                auswahl.append(teile[i].strip('= ') + ': ' + teile[i + 1])
        text = '\n'.join(auswahl)[:grenze]
        return {'quelle': 'Wikipedia', 'name': seite['title'], 'url': seite.get('fullurl', ''), 'text': text}
    except Exception as e:
        print('Wikipedia nicht verfuegbar:', titel, str(e)[:120])
        return None


def _autor(roh):
    # GEMESSEN: Wikimedia liefert „Unknown authorUnknown author" (zwei Spans)
    t = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', roh)).strip()
    w = t.split()
    if len(w) % 2 == 0 and w[:len(w) // 2] == w[len(w) // 2:]:
        t = ' '.join(w[:len(w) // 2])
    return t[:80] or 'unknown'


def wiki_bilder(titel, n=40):
    """Frei lizenzierte Fotos zum Wikipedia-Artikel (Wikimedia Commons).
    GEMELDET (KI-Analyse Business-Video): Stock-Clips passten nur abstrakt
    (Gasflamme, Einkaufszentrum). Echte Fotos zeigen Gruender, Werk, Produkt.
    Nur gemeinfrei oder CC; nie „NonFree"; keine SVG (Flaggen, Logos, Icons).
    Urheber + Lizenz + Seite werden fuer die Namensnennung mitgefuehrt."""
    try:
        d = json.loads(_hole('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'query', 'generator': 'images', 'titles': titel, 'gimlimit': 50, 'redirects': 1,
            'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata', 'iiurlwidth': 360,
            'iiextmetadatafilter': 'LicenseShortName|Artist|ImageDescription|NonFree', 'format': 'json'}),
            WIKI_KENNUNG))
    except Exception as e:
        print('Wikipedia-Bilder nicht verfuegbar:', str(e)[:120])
        return []
    aus = []
    # GEMESSEN 03.10.2026: Ohne Lizenzangaben liefert die API [] statt {} (PHP-
    # Eigenheit) - 'list' object has no attribute 'get' brach den Lauf ab.
    query = d.get('query') if isinstance(d.get('query'), dict) else {}
    seiten = query.get('pages') if isinstance(query.get('pages'), dict) else {}
    for seite in seiten.values():
        ii = (seite.get('imageinfo') or [{}])[0]
        m = ii.get('extmetadata') if isinstance(ii.get('extmetadata'), dict) else {}
        m = {k: (w if isinstance(w, dict) else {}) for k, w in m.items()}
        lizenz = m.get('LicenseShortName', {}).get('value', '')
        if (not ii.get('thumburl') or seite['title'].lower().endswith(('.svg', '.gif'))
                or m.get('NonFree', {}).get('value') or ii.get('width', 0) < 600
                or not re.match(r'(CC|Public domain|PD)', lizenz, re.I)
                # NC verbietet Geld verdienen (Kanaele sollen monetarisiert werden),
                # ND verbietet Bearbeiten (wir zoomen und beschriften jedes Foto).
                # GEMESSEN 03.10.2026: Commons hat sie bei 8 Firmen nie geliefert -
                # die Sperre ist Absicherung, falls doch einmal eines auftaucht.
                or re.search(r'\b(NC|ND)\b', lizenz)):
            continue
        klein = ii['thumburl']
        aus.append({'titel': seite['title'], 'klein': klein,
                    # Standard-Muster der Wikimedia-Vorschauen: /360px- -> /1080px-
                    'gross': klein.replace('/360px-', '/1080px-') if ii.get('width', 0) > 1080 else ii['url'],
                    'lizenz': lizenz, 'seite': ii.get('descriptionurl', ''),
                    'autor': _autor(m.get('Artist', {}).get('value', '')),
                    'beschreibung': re.sub(r'<[^>]+>', '', m.get('ImageDescription', {}).get('value', ''))[:200]})
    return aus[:n]


if __name__ == '__main__':
    print('Google Trends:', google_trends()[:8])
    q = ki_quellen()
    print(f'KI-Quellen: {len(q)}'); [print(' -', x['quelle'], '|', x['name'], '|', x['text'][:90]) for x in q[:12]]
    print('YouTube-Ausreisser:', youtube_ausreisser(['business origin story']))


FIRMA = re.compile(r'\b(company|corporation|conglomerate|manufacturer|retailer|brand|chain|automaker|airline|'
                   r'bank|carmaker|startup|multinational|business|enterprise|franchise|label|studio)\b', re.I)


def firmen_im_trend(datum=None, n=300):
    """Firmen, die GESTERN viel gelesen wurden (Wikipedia-Aufrufe, offizielle API, kostenlos).
    GEMELDET 04.10.2026: „Die Themen muessen alle immer aktuell sein." Eine Firmen-
    geschichte bekommt so einen Anlass („gerade in den Schlagzeilen - wie fing es an?").
    Gefiltert ueber die Kurzbeschreibung des Artikels („American multinational
    technology company"). Gibt [(titel, aufrufe, beschreibung)] absteigend zurueck."""
    import datetime
    tag = datum or (datetime.datetime.utcnow() - datetime.timedelta(days=1))
    try:
        top = json.loads(_hole('https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/'
                               f'{tag:%Y/%m/%d}', WIKI_KENNUNG))['items'][0]['articles'][:n]
    except Exception as e:
        print('Wikipedia-Bestenliste nicht verfuegbar:', str(e)[:100])
        return []
    aufrufe = {a['article'].replace('_', ' '): a['views'] for a in top if ':' not in a['article']}
    titel, aus = list(aufrufe), []
    import time as _t
    # GEMESSEN 04.10.2026 (GitHub-Lauf): 20 schnelle Anfragen -> Wikipedia antwortete danach
    # auch beim eigentlichen Artikel mit 429 Too Many Requests. Jetzt 300 statt 1.000 Titel
    # (6 Anfragen) und eine kurze Pause dazwischen.
    for i in range(0, len(titel), 50):  # 50 Titel je Anfrage (API-Grenze)
        _t.sleep(0.5)
        try:
            d = json.loads(_hole('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({
                'action': 'query', 'prop': 'description', 'titles': '|'.join(titel[i:i + 50]), 'format': 'json',
                'redirects': 1}), WIKI_KENNUNG))
        except Exception:
            continue
        for s in (d.get('query', {}).get('pages') or {}).values():
            b = s.get('description', '')
            if (FIRMA.search(b) and not re.search(r'\b(film|album|song|series|episode|band)\b', b, re.I)
                    and not re.match(r'(List of|Proposed|Timeline of|History of)', s['title'])):
                aus.append((s['title'], aufrufe.get(s['title'], 0), b))
    return sorted(aus, key=lambda x: -x[1])
