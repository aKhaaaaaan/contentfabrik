"""Erfolgs-Gedaechtnis: Welche UNSERER Videos liefen wirklich - und mit welchen Einstellungen?

GEMELDET: „Das Tool muss sich merken, welche Videos viral gegangen sind, und
daraus Stimmen, Qualitaet und andere Einstellungen fuer zukuenftige Videos
uebernehmen - also staendig lernen."

Stufe 1 (abrufen): einmal taeglich die echten Zahlen der hochgeladenen Videos
ueber die offiziellen Schnittstellen (YouTube Data API + YouTube Analytics):
Aufrufe, Likes, Kommentare, durchschnittlich gesehener Anteil. Zuordnung zu
unseren Videos ueber den Titel (der Nutzer uebernimmt ihn aus Telegram).
Stufe 2 (waehlen): Einstellungen, die bei UNSEREN Videos besser liefen, werden
haeufiger gewaehlt - 2 von 10 Mal wird bewusst Neues probiert, damit das Tool
nicht an einem Zufallstreffer haengen bleibt. Gezaehlt wird erst ab 48 h.
TikTok liefert Zahlen nur an gepruefte Apps - bis dahin lernt das Tool aus YouTube.

Daten: erfolg/<kanal>.json (im Projekt, nach jedem Lauf gesichert).
"""
import datetime, json, os, random, re, statistics, urllib.parse, urllib.request
from pathlib import Path

ORDNER = Path('erfolg')
GEHEIM = Path(os.environ.get('CF_GEHEIM', Path.home() / 'Downloads' / 'contentfabrik-geheim'))
MIN_DATEN = 3        # so viele Videos je Einstellung, bevor sie verglichen wird
NEUGIER = 0.2        # Anteil bewusst neuer Versuche


def _zugang(kanal_id):
    if os.environ.get('YT_CLIENT'):
        c = json.loads(os.environ['YT_CLIENT'])
        token = json.loads(os.environ['YT_TOKENS']).get(kanal_id)
    else:  # lokal am PC
        c = json.loads(sorted(GEHEIM.glob('client_secret*.json'))[0].read_text(encoding='utf-8'))['installed']
        p = GEHEIM / f'token-{kanal_id}.json'
        token = json.loads(p.read_text(encoding='utf-8'))['refresh_token'] if p.exists() else None
    if not token:
        return None
    d = json.load(urllib.request.urlopen(urllib.request.Request(c['token_uri'], data=urllib.parse.urlencode({
        'client_id': c['client_id'], 'client_secret': c['client_secret'], 'refresh_token': token,
        'grant_type': 'refresh_token'}).encode()), timeout=30))
    return d['access_token']


def _hole(url, token):
    return json.load(urllib.request.urlopen(urllib.request.Request(
        url, headers={'Authorization': 'Bearer ' + token}), timeout=30))


def _norm(titel):
    return re.sub(r'[^a-z0-9]', '', re.sub(r'#\w+', '', (titel or '').lower()))


def laden(kanal):
    p = ORDNER / f'{kanal}.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'videos': {}}


def abrufen(kanal):
    """Zahlen der letzten 50 Uploads holen und unseren Videos zuordnen."""
    einst = json.loads(Path(f'kanaele/{kanal}.json').read_text(encoding='utf-8'))
    kanal_id = einst.get('youtube_kanal_id')
    token = _zugang(kanal_id) if kanal_id else None
    if not token:
        print(f'{kanal}: noch kein YouTube-Zugang - uebersprungen')
        return
    API = 'https://www.googleapis.com/youtube/v3/'
    uploads = _hole(API + 'channels?part=contentDetails&mine=true', token)['items'][0]['contentDetails'][
        'relatedPlaylists']['uploads']
    ids = [i['contentDetails']['videoId'] for i in _hole(
        API + f'playlistItems?part=contentDetails&maxResults=50&playlistId={uploads}', token).get('items', [])]
    if not ids:
        print(f'{kanal}: keine Uploads')
        return
    videos = _hole(API + 'videos?part=snippet,statistics,status&id=' + ','.join(ids), token)['items']
    # Anteil gesehen (Zuschauerbindung) - der wichtigste Wert fuer den Algorithmus
    heute = datetime.date.today()
    # RECHERCHE 03.10.2026 (vidIQ, Metricool, YouTube-API-Doku): Fuer Shorts
    # zaehlen Engaged Views, gesehener Anteil, Teilen (~8x so viel wie Likes)
    # und Abos aus dem Video. „Angesehen vs. weggewischt" gibt es nur in Studio.
    bindung = {}
    ANALYTICS = 'https://youtubeanalytics.googleapis.com/v2/reports?'
    zeitraum = {'ids': 'channel==MINE', 'startDate': (heute - datetime.timedelta(days=90)).isoformat(),
                'endDate': heute.isoformat()}
    for metriken in ('views,engagedViews,averageViewDuration,averageViewPercentage,shares,subscribersGained',
                     'views,averageViewDuration,averageViewPercentage'):  # Rueckfall ohne neue Felder
        try:
            a = _hole(ANALYTICS + urllib.parse.urlencode({**zeitraum, 'metrics': metriken, 'dimensions': 'video',
                                                          'filters': 'video==' + ','.join(ids), 'maxResults': 200}), token)
            namen = [k['name'] for k in a.get('columnHeaders', [])]
            for zeile in a.get('rows', []):
                w = dict(zip(namen, zeile))
                bindung[w['video']] = {'dauer_s': w.get('averageViewDuration'),
                                       'anteil_prozent': w.get('averageViewPercentage'),
                                       'engaged': w.get('engagedViews'), 'teilungen': w.get('shares'),
                                       'abos': w.get('subscribersGained')}
            break
        except Exception as e:
            print('Analytics nicht verfuegbar:', str(e)[:150])
    verlauf = json.loads(Path(f'verlauf/{kanal}.json').read_text(encoding='utf-8')) \
        if Path(f'verlauf/{kanal}.json').exists() else []
    unsere = {_norm(' '.join(v['titel']).replace('*', '')): v for v in verlauf if v.get('status') == 'gesendet'}
    daten = laden(kanal)
    for v in videos:
        eintrag = unsere.get(_norm(v['snippet']['title']))
        if not eintrag:
            continue  # nicht von uns (oder Titel geaendert)
        s = v.get('statistics', {})
        daten['videos'][v['id']] = {
            'titel': v['snippet']['title'], 'veroeffentlicht': v['snippet']['publishedAt'][:10],
            'oeffentlich': v['status']['privacyStatus'] == 'public',
            'aufrufe': int(s.get('viewCount', 0)), 'likes': int(s.get('likeCount', 0)),
            'kommentare': int(s.get('commentCount', 0)), **bindung.get(v['id'], {}),
            'einstellungen': eintrag.get('einstellungen', {}), 'hook': eintrag.get('hook', ''),
            'gliederung': eintrag.get('gliederung', []),
        }
    # Zuschauer-Kurve je Video (ab 2 Tagen, einmalig): WO springen die Leute ab?
    neue_lehren = []
    for vid, v in daten['videos'].items():
        if 'kurve' in v or v['veroeffentlicht'] > (heute - datetime.timedelta(days=2)).isoformat():
            continue
        try:
            k = _hole(ANALYTICS + urllib.parse.urlencode({**zeitraum, 'metrics': 'audienceWatchRatio',
                                                          'dimensions': 'elapsedVideoTimeRatio',
                                                          'filters': f'video=={vid}'}), token)
            v['kurve'] = [[round(r[0], 2), round(r[1], 3)] for r in k.get('rows', [])]
        except Exception as e:
            print('Kurve nicht verfuegbar:', vid, str(e)[:120])
            continue
        lehre = absprung(v, unsere)
        if lehre:
            v['absprung'] = lehre
            neue_lehren.append({'zeit': lehre['sekunde'], 'art': 'zuschauer', 'text': lehre['text']})
    if neue_lehren:  # echtes Zuschauerverhalten -> Lern-Gedaechtnis
        try:
            import lernen
            lernen.aktualisieren(kanal, {'probleme': neue_lehren, 'kategorien': {}})
        except Exception as e:
            print('Lernen aus Zuschauerdaten nicht moeglich:', str(e)[:150])
    daten['stand'] = heute.isoformat()
    ORDNER.mkdir(exist_ok=True)
    (ORDNER / f'{kanal}.json').write_text(json.dumps(daten, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"{kanal}: {len(daten['videos'])} eigene Videos mit Zahlen")


def absprung(v, unsere):
    """Wo faellt die Kurve unter 50 % - und welcher Skript-Abschnitt lief da?"""
    eintrag = unsere.get(_norm(v['titel'])) or {}
    abschnitte, gliederung = eintrag.get('abschnitte_s') or [], eintrag.get('gliederung') or []
    kurve = v.get('kurve') or []
    stelle = next((r for r, w in kurve if w < 0.5), None)
    if stelle is None or not abschnitte:
        return None
    sekunde = stelle * sum(abschnitte)
    summe, teil = 0, len(abschnitte) - 1
    for i, d in enumerate(abschnitte):
        summe += d
        if sekunde <= summe:
            teil = i
            break
    name = 'the hook' if teil == 0 else 'the ending' if teil == len(abschnitte) - 1 else f'part {teil + 1}'
    text = (f'Real viewers dropped below 50% at second {sekunde:.0f}, during {name}: '
            f'"{gliederung[teil] if teil < len(gliederung) else ""}..." - make that kind of part stronger or cut it.')
    return {'sekunde': f'{sekunde:.0f}s', 'teil': teil, 'text': text}


def _bewertet(kanal):
    """Nur oeffentliche Videos, die mindestens 48 h alt sind - mit Erfolgswert.
    Wert = Aufrufe relativ zum Kanal-Median x gesehener Anteil."""
    grenze = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
    vs = [v for v in laden(kanal)['videos'].values() if v.get('oeffentlich') and v['veroeffentlicht'] <= grenze]
    if not vs:
        return []
    median = statistics.median(v['aufrufe'] for v in vs) or 1
    for v in vs:
        basis = v.get('engaged') or v['aufrufe']
        # Teilen und Abos wiegen schwer (Recherche: Teilen ~8x Like), dazu der gesehene Anteil
        v['wert'] = (basis / median * ((v.get('anteil_prozent') or 50) / 100)
                     * (1 + 8 * (v.get('teilungen') or 0) / max(basis, 1) + 5 * (v.get('abos') or 0) / max(basis, 1)))
    return vs


def waehlen(kanal, schluessel, optionen):
    """Eine Einstellung waehlen: zu wenig Daten -> die am seltensten getestete;
    sonst meist die beste, manchmal bewusst eine andere (Neugier)."""
    optionen = list(optionen)
    if len(optionen) <= 1:
        return optionen[0] if optionen else None
    vs = _bewertet(kanal)
    werte = {o: [v['wert'] for v in vs if v['einstellungen'].get(schluessel) == o] for o in optionen}
    zu_wenig = [o for o in optionen if len(werte[o]) < MIN_DATEN]
    if zu_wenig:
        return min(zu_wenig, key=lambda o: len(werte[o]))
    if random.random() < NEUGIER:
        return random.choice(optionen)
    return max(optionen, key=lambda o: statistics.mean(werte[o]))


def vorbilder(kanal, n=3):
    """Hooks unserer erfolgreichsten Videos - eigene Texte, frei verwendbar."""
    vs = sorted(_bewertet(kanal), key=lambda v: -v['wert'])
    return [f"HOOK: {v['hook']} | STRUCTURE: {' -> '.join(v.get('gliederung', []))} "
            f"({v['aufrufe']} views, {v.get('anteil_prozent', '?')}% watched)" for v in vs[:n] if v['hook']]


def bericht(kanal):
    vs = _bewertet(kanal)
    if not vs:
        return f'{kanal}: noch keine auswertbaren Videos (oeffentlich und aelter als 48 h)'
    zeilen = [f'{kanal}: {len(vs)} Videos ausgewertet']
    for schluessel in ('stimme', 'winkel', 'format', 'laenge', 'hook_art', 'teile'):
        gruppen = {}
        for v in vs:
            gruppen.setdefault(str(v['einstellungen'].get(schluessel)), []).append(v['wert'])
        zeilen.append(f'  {schluessel}: ' + ', '.join(f'{k} {statistics.mean(w):.2f} ({len(w)})'
                                                       for k, w in sorted(gruppen.items(), key=lambda x: -statistics.mean(x[1]))))
    return '\n'.join(zeilen)


if __name__ == '__main__':
    import sys
    for k in sys.argv[1:] or [p.stem for p in Path('kanaele').glob('*.json')]:
        try:
            abrufen(k)
            print(bericht(k))
        except Exception as e:
            print(f'{k}: Abruf fehlgeschlagen:', str(e)[:200])
