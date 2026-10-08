"""Laedt ein fertiges Video auf YouTube hoch - IMMER privat.

Oeffentlich wird es erst durch die Freigabe des Nutzers (Konzept: jedes Video
wird vorher abgenickt). Solange Google das Projekt nicht geprueft hat, sperrt
YouTube ohnehin jedes per API hochgeladene Video auf privat.

Aufruf:  python fabrik/hochladen.py ausgabe/skript.json ausgabe/short.mp4 <kanal_id>
Schluessel: Downloads/contentfabrik-geheim/ (client_secret*.json, token-<kanal_id>.json)
"""
import json, os, sys, urllib.parse, urllib.request, urllib.error
from pathlib import Path

GEHEIM = Path(os.environ.get('CF_GEHEIM', Path.home() / 'Downloads' / 'contentfabrik-geheim'))
# YouTube-Kategorien: 28 Wissenschaft & Technik, 27 Bildung, 24 Unterhaltung


def kategorie(name):
    """YouTube-Kategorie aus dem Kanalprofil (kanalstandard: '27' Bildung)."""
    import kanalstandard
    return str((kanalstandard.nach_name(name) or kanalstandard.STANDARD)['youtube_kategorie'])


def zugang(kanal_id):
    c = json.loads(sorted(GEHEIM.glob('client_secret*.json'))[0].read_text(encoding='utf-8'))['installed']
    t = json.loads((GEHEIM / f'token-{kanal_id}.json').read_text(encoding='utf-8'))
    d = json.load(urllib.request.urlopen(urllib.request.Request(c['token_uri'], data=urllib.parse.urlencode({
        'client_id': c['client_id'], 'client_secret': c['client_secret'],
        'refresh_token': t['refresh_token'], 'grant_type': 'refresh_token'}).encode())))
    return d['access_token'], t['kanal']


def metadaten(skript):
    sauber = lambda z: z.replace('*', '').strip()
    titel = f"{sauber(skript['titel'][0])} {sauber(skript['titel'][1])}"
    if len(titel) > 90:  # Grenze 100 Zeichen, Platz fuer #shorts
        titel = titel[:90].rsplit(' ', 1)[0]
    tags = [h.lstrip('#') for h in skript.get('hashtags', [])]
    beschreibung = skript['beschreibung'] + '\n\n' + ' '.join('#' + t for t in tags)
    return {
        'snippet': {'title': titel + ' #shorts', 'description': beschreibung[:4900], 'tags': tags,
                    'categoryId': kategorie(skript.get('kanal')), 'defaultLanguage': 'en',
                    'defaultAudioLanguage': 'en'},
        'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': False,
                   # Pflicht laut YouTube-Richtlinie: KI-Stimme = synthetischer Inhalt
                   'containsSyntheticMedia': True},
    }


def hochladen(skript_pfad, video_pfad, kanal_id):
    token, kanal = zugang(kanal_id)
    skript = json.loads(Path(skript_pfad).read_text(encoding='utf-8'))
    daten = Path(video_pfad).read_bytes()
    # Fortsetzbarer Upload (offizieller Weg), 2 Schritte: Sitzung, dann Datei
    start = urllib.request.Request(
        'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
        data=json.dumps(metadaten(skript)).encode(), method='POST',
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json; charset=UTF-8',
                 'X-Upload-Content-Type': 'video/mp4', 'X-Upload-Content-Length': str(len(daten))})
    try:
        ziel = urllib.request.urlopen(start).headers['Location']
        video = json.load(urllib.request.urlopen(urllib.request.Request(
            ziel, data=daten, method='PUT', headers={'Content-Type': 'video/mp4'}), timeout=600))
        # GEMESSEN 02.10.2026: Beim Hochladen mitgeschickt, fehlte die
        # KI-Kennzeichnung danach; erst ein Nachsetzen per Update hielt.
        status = {**video['status'], 'containsSyntheticMedia': True}
        video['status'] = json.load(urllib.request.urlopen(urllib.request.Request(
            'https://www.googleapis.com/youtube/v3/videos?part=status', method='PUT',
            data=json.dumps({'id': video['id'], 'status': status}).encode(),
            headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})))['status']
        if not video['status'].get('containsSyntheticMedia'):
            print('WARNUNG: KI-Kennzeichnung nicht gesetzt - bitte in YouTube Studio pruefen.', file=sys.stderr)
    except urllib.error.HTTPError as e:
        sys.exit(f'Hochladen fehlgeschlagen ({e.code}): {e.read().decode(errors="replace")[:500]}')
    print(json.dumps({'kanal': kanal, 'video_id': video['id'], 'titel': video['snippet']['title'],
                      'status': video['status']['privacyStatus'],
                      'link': 'https://youtube.com/shorts/' + video['id']}, indent=2, ensure_ascii=False))
    return video['id']


if __name__ == '__main__':
    hochladen(sys.argv[1], sys.argv[2], sys.argv[3])
