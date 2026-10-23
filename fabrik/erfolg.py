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
TikTok (seit 23.10.2026, Recht video.list): Aufrufe/Likes/Teilungen je Video, s. tiktok_abrufen.

Daten: erfolg/<kanal>.json (im Projekt, nach jedem Lauf gesichert).
"""
import datetime, json, math, os, random, re, statistics, urllib.error, urllib.parse, urllib.request
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
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(c['token_uri'], data=urllib.parse.urlencode({
            'client_id': c['client_id'], 'client_secret': c['client_secret'], 'refresh_token': token,
            'grant_type': 'refresh_token'}).encode()), timeout=30))
    except urllib.error.HTTPError as e:
        # invalid_grant = Zugang im Google-Konto widerrufen (oder abgelaufen).
        # Andere Fehler (Netz, 5xx) duerfen NICHT zum Loeschen fuehren.
        if 'invalid_grant' in e.read().decode(errors='replace'):
            return WIDERRUFEN
        raise
    return d['access_token']


WIDERRUFEN = 'widerrufen'


def _hole(url, token):
    return json.load(urllib.request.urlopen(urllib.request.Request(
        url, headers={'Authorization': 'Bearer ' + token}), timeout=30))


def _norm(titel):
    # Uploadtitel traegt seit 11.10. den Serienzusatz, Verlauf speichert den Basistitel.
    # Nur den kontrollierten Schlusszusatz entfernen, keine beliebigen Titelwoerter.
    titel = re.sub(r'\s+\|\s+AI Tool\s+#\d+(?=\s*(?:#\w+\s*)*$)', '', titel or '', flags=re.I)
    return re.sub(r'[^a-z0-9]', '', re.sub(r'#\w+', '', titel.lower()))


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
    if token == WIDERRUFEN:
        # YouTube-Entwicklerrichtlinie III.E.4: Wird die Erlaubnis widerrufen,
        # muessen die gespeicherten API-Daten binnen 30 Tagen weg (GEPRUEFT
        # 03.10.2026). Der taegliche Abruf ist zugleich die verlangte Pruefung
        # „alle 30 Tage, ob die Erlaubnis noch besteht".
        p = ORDNER / f'{kanal}.json'
        if p.exists():
            rest = {'videos': {}, 'tiktok': laden(kanal)['tiktok']} if 'tiktok' in laden(kanal) else None
            p.unlink()
            if rest:  # TikTok-Zahlen stammen nicht von YouTube und bleiben
                p.write_text(json.dumps(rest, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f'{kanal}: YouTube-Zugang widerrufen - gespeicherte Zahlen geloescht')
        return
    API ='https://www.googleapis.com/youtube/v3/'
    uploads = _hole(API + 'channels?part=contentDetails&mine=true', token)['items'][0]['contentDetails'][
        'relatedPlaylists']['uploads']
    ids = [i['contentDetails']['videoId'] for i in _hole(
        API + f'playlistItems?part=contentDetails&maxResults=50&playlistId={uploads}', token).get('items', [])]
    if not ids:
        print(f'{kanal}: keine Uploads')
        return
    videos = _hole(API + 'videos?part=snippet,statistics,status&id=' + ','.join(ids), token)['items']
    # Gesehener Anteil und weitere beobachtbare Publikums-Signale getrennt abrufen.
    heute = datetime.date.today()
    # Offizielle Analytics-Metriken; keine bekannten festen Algorithmus-Gewichte.
    # "Angesehen vs. weggewischt" bleibt eine gesonderte Studio-Kennzahl.
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
        alt = daten['videos'].get(v['id'], {})
        daten['videos'][v['id']] = {
            **{k: alt[k] for k in ('kurve', 'kurve_stand', 'kurve_aufrufe', 'absprung') if k in alt},
            'titel': v['snippet']['title'], 'veroeffentlicht': v['snippet']['publishedAt'][:10],
            'oeffentlich': v['status']['privacyStatus'] == 'public',
            'aufrufe': int(s.get('viewCount', 0)), 'likes': int(s.get('likeCount', 0)),
            'kommentare': int(s.get('commentCount', 0)), **bindung.get(v['id'], {}),
            'einstellungen': eintrag.get('einstellungen', {}), 'hook': eintrag.get('hook', ''),
            'gliederung': eintrag.get('gliederung', []),
        }
    # Erst genuegend Daten, danach bei Wachstum oder nach einer Woche erneut.
    neue_lehren = []
    for vid, v in daten['videos'].items():
        if not kurve_faellig(v, heute):
            continue
        try:
            k = _hole(ANALYTICS + urllib.parse.urlencode({**zeitraum, 'metrics': 'audienceWatchRatio',
                                                          'dimensions': 'elapsedVideoTimeRatio',
                                                          'filters': f'video=={vid}'}), token)
            v['kurve'] = [[round(r[0], 2), round(r[1], 3)] for r in k.get('rows', [])]
            if not v['kurve']:
                continue  # nicht als dauerhaft fertig behandeln
            v['kurve_stand'], v['kurve_aufrufe'] = heute.isoformat(), v['aufrufe']
        except Exception as e:
            print('Kurve nicht verfuegbar:', vid, str(e)[:120])
            continue
        lehre = absprung(v, unsere)
        vorher = v.pop('absprung', None)
        if lehre:
            v['absprung'] = lehre
            if lehre != vorher:
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


TIKTOK_SEITEN = 3   # je 20 Videos: deckt rund zwei Monate taeglicher Shorts ab


def _tiktok_videos(kanal):
    """Rohliste von video.list (Recht seit 23.10.2026 erteilt) fuer das Konto des Kanals."""
    import tiktok, tiktok_entwurf
    name = json.loads(Path(f'kanaele/{kanal}.json').read_text(encoding='utf-8')).get('tiktok_name')
    if not name:
        return None
    token = tiktok.zugang(tiktok_entwurf.konto_finden(name))
    felder = 'id,title,video_description,create_time,duration,view_count,like_count,comment_count,share_count'
    videos, cursor = [], None
    for _ in range(TIKTOK_SEITEN):
        r = tiktok._post(tiktok.API + 'video/list/?fields=' + felder, token=token,
                         json_daten={'max_count': 20, **({'cursor': cursor} if cursor else {})})
        if (r.get('error') or {}).get('code', 'ok') != 'ok':
            raise RuntimeError(f"TikTok video.list: {r['error'].get('code')}")
        d = r.get('data') or {}
        videos += d.get('videos') or []
        if not d.get('has_more'):
            break
        cursor = d.get('cursor')
    return videos


def tiktok_zuordnen(videos, verlauf):
    """TikTok-Videos unseren gesendeten Videos zuordnen. Der Nutzer uebernimmt den Telegram-Text,
    die TikTok-Caption beginnt daher mit dem Uploadtitel (GEMESSEN 23.10.2026: 40 von 40 so).
    Mehrfach gepostete Videos zaehlen nur einmal (das mit den meisten Aufrufen)."""
    unsere = {}
    for e in verlauf:
        if e.get('status') == 'gesendet':
            schluessel = _norm(' '.join(e.get('titel') or []).replace('*', ''))
            if len(schluessel) >= 10:
                unsere[schluessel] = e
    treffer = {}
    for v in videos:
        kopf = re.split(r'\s+\|\s+AI Tool\b', v.get('title') or v.get('video_description') or '')[0]
        n = _norm(kopf)
        passend = [k for k in unsere if n.startswith(k)]
        if not passend:
            continue
        k = max(passend, key=len)
        if k in treffer and treffer[k]['aufrufe'] >= (v.get('view_count') or 0):
            continue
        e = unsere[k]
        treffer[k] = {
            'id': str(v['id']), 'titel': ' '.join(e['titel']).replace('*', ''),
            'veroeffentlicht': datetime.datetime.fromtimestamp(
                v.get('create_time') or 0, datetime.timezone.utc).date().isoformat(),
            'oeffentlich': True, 'aufrufe': v.get('view_count') or 0, 'likes': v.get('like_count') or 0,
            'kommentare': v.get('comment_count') or 0, 'teilungen': v.get('share_count') or 0,
            'video_s': v.get('duration'), 'einstellungen': e.get('einstellungen', {}),
            'hook': e.get('hook', ''), 'gliederung': e.get('gliederung', [])}
    return {t.pop('id'): t for t in treffer.values()}


def tiktok_abrufen(kanal):
    """Aufrufe/Likes/Teilungen je TikTok-Video in erfolg/<kanal>.json['tiktok'] (ersetzt den alten Stand)."""
    videos = _tiktok_videos(kanal)
    if videos is None:
        print(f'{kanal}: kein TikTok-Konto im Profil - uebersprungen')
        return
    pfad = Path(f'verlauf/{kanal}.json')
    verlauf = json.loads(pfad.read_text(encoding='utf-8')) if pfad.exists() else []
    daten = laden(kanal)
    # Aeltere Videos fallen aus den letzten 60 heraus - ihre letzten Zahlen bleiben stehen.
    neu = tiktok_zuordnen(videos, verlauf)
    alle = {**daten.get('tiktok', {}), **neu}
    beste = {}
    for tid, t in alle.items():
        if t['titel'] not in beste or alle[beste[t['titel']]]['aufrufe'] < t['aufrufe']:
            beste[t['titel']] = tid
    daten['tiktok'] = {tid: alle[tid] for tid in beste.values()}
    daten['tiktok_stand'] = datetime.date.today().isoformat()
    ORDNER.mkdir(exist_ok=True)
    (ORDNER / f'{kanal}.json').write_text(json.dumps(daten, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"{kanal}: {len(neu)} von {len(videos)} TikTok-Videos zugeordnet, {len(daten['tiktok'])} gespeichert")


def kurve_faellig(v, heute):
    if not v.get('oeffentlich') or v.get('aufrufe', 0) < 100 \
            or v['veroeffentlicht'] > (heute - datetime.timedelta(days=2)).isoformat():
        return False
    if not v.get('kurve') or not v.get('kurve_stand'):
        return True
    return v['aufrufe'] >= max(100, v.get('kurve_aufrufe', 0) * 1.5) \
        or v['kurve_stand'] <= (heute - datetime.timedelta(days=7)).isoformat()


def absprung(v, unsere):
    """Auffaellige lokale Verluste; Zusammenhang ist noch keine Ursache."""
    eintrag = unsere.get(_norm(v['titel'])) or {}
    abschnitte, gliederung = eintrag.get('abschnitte_s') or [], eintrag.get('gliederung') or []
    kurve = v.get('kurve') or []
    if not abschnitte or len(kurve) < 3 or v.get('aufrufe', 0) < 100:
        return None
    if any(not isinstance(r, (list, tuple)) or len(r) != 2 or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
            for x in r) or not 0 <= r[0] <= 1 or r[1] < 0 for r in kurve):
        return None
    kurve = sorted(kurve)
    # Zwei nachfolgende Messpunkte muessen einen lokalen Verlust bestaetigen.
    kandidaten = [(vor[1] - max(jetzt[1], danach[1]), jetzt[0])
                   for vor, jetzt, danach in zip(kurve, kurve[1:], kurve[2:])
                   if 0 < jetzt[0] - vor[0] <= .050001 and 0 < danach[0] - jetzt[0] <= .050001
                   and jetzt[0] <= .9]
    if not kandidaten:
        return None
    verlust, stelle = max(kandidaten)
    if verlust < .099999:
        return None
    sekunde = stelle * sum(abschnitte)
    summe, teil = 0, len(abschnitte) - 1
    for i, d in enumerate(abschnitte):
        summe += d
        if sekunde <= summe:
            teil = i
            break
    name = 'the hook' if teil == 0 else 'the ending' if teil == len(abschnitte) - 1 else f'part {teil + 1}'
    text = (f'Observed audienceWatchRatio fell by at least {verlust * 100:.0f} percentage points '
            f'near second {sekunde:.0f}, during {name}: '
            f'"{gliederung[teil] if teil < len(gliederung) else ""}...". Inspect the promise, new '
            'information, visual evidence and pacing there. This association does not establish '
            'why viewers left; test one change and confirm across comparable videos. '
            f'Format: {eintrag.get("einstellungen", {}).get("videoformat", "short")}.')
    return {'sekunde': f'{sekunde:.0f}s', 'teil': teil, 'verlust': round(verlust, 3), 'text': text}


def _bewertet(kanal, videoformat='short'):
    """Nur oeffentliche Videos, die mindestens 48 h alt sind - mit Erfolgswert.
    Wert = Aufrufe relativ zum Kanal-Median x gesehener Anteil."""
    grenze = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
    daten = laden(kanal)
    def passend(v):
        return v.get('oeffentlich') and v['veroeffentlicht'] <= grenze and (
            videoformat is None or v.get('einstellungen', {}).get('videoformat', 'short') == videoformat)
    vs = [v for v in daten['videos'].values() if passend(v)]
    tt = [dict(v, plattform='tiktok') for v in daten.get('tiktok', {}).values() if passend(v)]
    if not vs:
        return _tiktok_bewertet(tt, .5)
    def basis(v):
        return v['engaged'] if v.get('engaged') is not None else v['aufrufe']
    median = statistics.median(basis(v) for v in vs) or 1
    for v in vs:
        gesehen = basis(v)
        anteil = v['anteil_prozent'] if v.get('anteil_prozent') is not None else 50
        # 8/5 sind bestehende Projekt-Heuristiken, KEINE Gewichte des YouTube-Algorithmus.
        # Ein gemessener Nullwert darf niemals durch viele Roh-Aufrufe/50 Prozent ersetzt werden.
        v['wert'] = (gesehen / median * (anteil / 100)
                     * (1 + 8 * (v.get('teilungen') or 0) / max(gesehen, 1)
                        + 5 * (v.get('abos') or 0) / max(gesehen, 1)))
    return vs + _tiktok_bewertet(tt, statistics.median(v['wert'] for v in vs) or .5)


def _tiktok_bewertet(tt, mitte):
    """TikTok liefert keinen gesehenen Anteil. Wert = Aufrufe relativ zum TikTok-Median x Teilungs-Bonus,
    dann so skaliert, dass der TikTok-Median dem YouTube-Median entspricht: Plattformen mit
    unterschiedlichem Zahlenniveau verzerren waehlen() sonst zugunsten der groesseren."""
    if not tt:
        return []
    median = statistics.median(v['aufrufe'] for v in tt) or 1
    roh = [v['aufrufe'] / median * (1 + 8 * (v.get('teilungen') or 0) / max(v['aufrufe'], 1)) for v in tt]
    faktor = mitte / (statistics.median(roh) or 1)
    for v, r in zip(tt, roh):
        v['wert'] = r * faktor
    return tt


def waehlen(kanal, schluessel, optionen, videoformat='short'):
    """Eine Einstellung waehlen: zu wenig Daten -> die am seltensten getestete;
    sonst meist die beste, manchmal bewusst eine andere (Neugier)."""
    optionen = list(optionen)
    if len(optionen) <= 1:
        return optionen[0] if optionen else None
    vs = _bewertet(kanal, videoformat)
    werte = {o: [v['wert'] for v in vs if v['einstellungen'].get(schluessel) == o] for o in optionen}
    zu_wenig = [o for o in optionen if len(werte[o]) < MIN_DATEN]
    if zu_wenig:
        return min(zu_wenig, key=lambda o: len(werte[o]))
    if random.random() < NEUGIER:
        return random.choice(optionen)
    return max(optionen, key=lambda o: statistics.mean(werte[o]))


def vorbilder(kanal, n=3, videoformat='short'):
    """Hooks unserer erfolgreichsten Videos - eigene Texte, frei verwendbar."""
    vs = sorted(_bewertet(kanal, videoformat), key=lambda v: -v['wert'])
    return [f"HOOK: {v['hook']} | STRUCTURE: {' -> '.join(v.get('gliederung', []))} "
            + (f"({v['aufrufe']} TikTok views, {v.get('teilungen', 0)} shares)" if v.get('plattform') == 'tiktok'
               else f"({v['aufrufe']} views, {v.get('anteil_prozent', '?')}% watched)") for v in vs[:n] if v['hook']]


def bericht(kanal):
    vs = _bewertet(kanal, None)
    if not vs:
        return f'{kanal}: noch keine auswertbaren Videos (oeffentlich und aelter als 48 h)'
    zeilen = [f'{kanal}: {len(vs)} Videos ausgewertet']
    for schluessel in ('videoformat', 'stimme', 'winkel', 'format', 'laenge', 'hook_art', 'teile'):
        gruppen = {}
        for v in vs:
            gruppen.setdefault(str(v['einstellungen'].get(schluessel)), []).append(v['wert'])
        zeilen.append(f'  {schluessel}: ' + ', '.join(f'{k} {statistics.mean(w):.2f} ({len(w)})'
                                                       for k, w in sorted(gruppen.items(), key=lambda x: -statistics.mean(x[1]))))
    return '\n'.join(zeilen)


if __name__ == '__main__':
    import sys
    if sys.argv[1:2] == ['tiktok']:  # eigener Schritt: braucht TikTok-Zugang + Token-Cache (themen.yml)
        sys.path.insert(0, str(Path(__file__).parent))
        for k in sys.argv[2:] or [p.stem for p in Path('kanaele').glob('*.json')]:
            try:
                tiktok_abrufen(k)
            except Exception as e:
                print(f'{k}: TikTok-Abruf fehlgeschlagen:', str(e)[:200])
        sys.exit(0)
    for k in sys.argv[1:] or [p.stem for p in Path('kanaele').glob('*.json')]:
        try:
            abrufen(k)
            print(bericht(k))
        except Exception as e:
            print(f'{k}: Abruf fehlgeschlagen:', str(e)[:200])
