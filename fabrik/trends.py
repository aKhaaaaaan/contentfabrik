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
import html, json, os, re, time, datetime, urllib.request, urllib.parse
from xml.etree import ElementTree

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


def ki_quellen(tage=7):
    """Aktuelle KI-Neuheiten mit Beschreibung - die EINZIGEN Fakten, die der
    Kanal „AI Tools Explained" verwenden darf (Konzept: Quellen-Methode)."""
    aus = []
    seit = (datetime.date.today() - datetime.timedelta(days=tage)).isoformat()
    try:  # GitHub: neue Repos zu KI, nach Sternen
        kopf = {'Accept': 'application/vnd.github+json'}
        if os.environ.get('GITHUB_TOKEN'):
            kopf['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
        d = json.loads(_hole('https://api.github.com/search/repositories?' + urllib.parse.urlencode({
            'q': f'topic:ai created:>{seit} stars:>100', 'sort': 'stars', 'order': 'desc', 'per_page': 10}), kopf))
        for r in d.get('items', []):
            aus.append({'quelle': 'GitHub', 'name': r['full_name'], 'url': r['html_url'],
                        'text': f"{r.get('description') or ''} - {r['stargazers_count']} stars, license: "
                                f"{(r.get('license') or {}).get('spdx_id', 'unknown')}, created {r['created_at'][:10]}"})
    except Exception as e:
        print('GitHub nicht verfuegbar:', e)
    try:  # Hugging Face: Modelle mit steigendem Interesse
        d = json.loads(_hole('https://huggingface.co/api/models?sort=trendingScore&limit=10'))
        for m in d:
            aus.append({'quelle': 'Hugging Face', 'name': m['id'], 'url': f"https://huggingface.co/{m['id']}",
                        'text': f"task: {m.get('pipeline_tag', 'unknown')}, {m.get('likes', 0)} likes, "
                                f"{m.get('downloads', 0)} downloads"})
    except Exception as e:
        print('Hugging Face nicht verfuegbar:', e)
    try:  # Hacker News: worueber Technik-Leute gerade reden
        ab = int(time.time()) - tage * 86400
        d = json.loads(_hole('https://hn.algolia.com/api/v1/search?' + urllib.parse.urlencode({
            'query': 'AI tool', 'tags': 'story', 'numericFilters': f'created_at_i>{ab},points>100', 'hitsPerPage': 10})))
        for h in d.get('hits', []):
            aus.append({'quelle': 'Hacker News', 'name': h.get('title', ''), 'url': h.get('url') or '',
                        'text': f"{h.get('points', 0)} points, {h.get('num_comments', 0)} comments"})
    except Exception as e:
        print('Hacker News nicht verfuegbar:', e)
    return aus


if __name__ == '__main__':
    print('Google Trends:', google_trends()[:8])
    q = ki_quellen()
    print(f'KI-Quellen: {len(q)}'); [print(' -', x['quelle'], '|', x['name'], '|', x['text'][:90]) for x in q[:12]]
    print('YouTube-Ausreisser:', youtube_ausreisser(['business origin story']))
