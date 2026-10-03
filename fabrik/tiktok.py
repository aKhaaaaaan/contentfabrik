"""TikTok: einmalige Anmeldung je Konto + Hochladen ueber die offizielle Content Posting API.

Anmelden:   python fabrik/tiktok.py anmelden
Hochladen:  python fabrik/tiktok.py hochladen <video.mp4> <skript.json> <open_id>

Ablauf der Anmeldung (Login Kit, Web): Browser -> TikTok -> Ruecksprung auf
https://contentfabrik.pages.dev/tiktok-callback -> diese Seite reicht code/state
an 127.0.0.1:<port> weiter (Port steckt im state) -> Tausch gegen Schluessel.
Dauer-Schluessel liegen nur in Downloads/contentfabrik-geheim (tiktok-<open_id>.json).

GEPRUEFT 03.10.2026 (TikTok-Doku): „All content posted by unaudited clients
will be restricted to private viewing mode" - ungepruefte Apps posten nur
SELF_ONLY, und das Konto muss privat sein
(Fehler unaudited_client_can_only_post_to_private_accounts).
"""
import http.server, json, os, secrets, sys, time, urllib.parse, urllib.request, urllib.error, webbrowser
from pathlib import Path

GEHEIM = Path(os.environ.get('CF_GEHEIM', Path.home() / 'Downloads' / 'contentfabrik-geheim'))
RUECKSPRUNG = 'https://contentfabrik.pages.dev/tiktok-callback'
API = 'https://open.tiktokapis.com/v2/'
RECHTE = 'user.info.basic,video.upload,video.publish'


def _schluessel():
    k, s = os.environ.get('TIKTOK_CLIENT_KEY'), os.environ.get('TIKTOK_CLIENT_SECRET')
    if not (k and s):
        import subprocess  # lokal: per setx gesetzt, in dieser Shell evtl. noch nicht geladen
        hol = lambda n: subprocess.run(['powershell', '-NoProfile', '-Command',
                                        f"[Environment]::GetEnvironmentVariable('{n}','User')"],
                                       capture_output=True, text=True).stdout.strip()
        k, s = k or hol('TIKTOK_CLIENT_KEY'), s or hol('TIKTOK_CLIENT_SECRET')
    if not (k and s):
        sys.exit('TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET fehlen')
    return k, s


def _post(url, daten=None, token=None, json_daten=None):
    kopf = {'Authorization': 'Bearer ' + token} if token else {}
    if json_daten is not None:
        body, kopf['Content-Type'] = json.dumps(json_daten).encode(), 'application/json; charset=UTF-8'
    else:
        body, kopf['Content-Type'] = urllib.parse.urlencode(daten or {}).encode(), 'application/x-www-form-urlencoded'
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(url, data=body, headers=kopf), timeout=60))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode() or '{}') | {'_http': e.code}


def anmelden():
    key, secret = _schluessel()
    antwort = {}

    class Empfang(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = {k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).items()}
            if 'code' not in q and 'error' not in q:
                self.send_response(404); self.end_headers(); return
            antwort.update(q)
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
            try:
                self.wfile.write('<h2>Fertig - dieses Fenster kann zu.</h2>'.encode())
            except Exception:
                pass

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(('127.0.0.1', 0), Empfang)
    zustand = f'{server.server_port}.{secrets.token_urlsafe(12)}'
    url = 'https://www.tiktok.com/v2/auth/authorize/?' + urllib.parse.urlencode({
        'client_key': key, 'response_type': 'code', 'scope': RECHTE, 'redirect_uri': RUECKSPRUNG, 'state': zustand})
    print('Browser oeffnet sich (TikTok-Anmeldung). Falls nicht, diese Adresse oeffnen:\n' + url)
    webbrowser.open(url)
    while 'code' not in antwort and 'error' not in antwort:
        server.handle_request()
    if antwort.get('state') != zustand or 'code' not in antwort:
        sys.exit('Anmeldung abgebrochen: ' + antwort.get('error_description', antwort.get('error', 'falscher Zustand')))
    t = _post(API + 'oauth/token/', {'client_key': key, 'client_secret': secret, 'code': antwort['code'],
                                     'grant_type': 'authorization_code', 'redirect_uri': RUECKSPRUNG})
    if 'refresh_token' not in t:
        sys.exit(f'Kein Dauer-Schluessel von TikTok: {t.get("error")} {t.get("error_description", "")}')
    info = json.load(urllib.request.urlopen(urllib.request.Request(
        API + 'user/info/?fields=open_id,display_name', headers={'Authorization': 'Bearer ' + t['access_token']})))
    name = info.get('data', {}).get('user', {}).get('display_name', '?')
    datei = GEHEIM / f"tiktok-{t['open_id']}.json"
    datei.write_text(json.dumps({'konto': name, 'open_id': t['open_id'], 'refresh_token': t['refresh_token'],
                                 'rechte': t.get('scope', '')}, indent=2), encoding='utf-8')
    print(f"\nAngemeldet bei TikTok: {name}  (Rechte: {t.get('scope')})\nGespeichert in {datei}")


def zugang(open_id):
    key, secret = _schluessel()
    if os.environ.get('TIKTOK_TOKENS'):
        refresh = json.loads(os.environ['TIKTOK_TOKENS'])[open_id]
        datei = None
    else:
        datei = GEHEIM / f'tiktok-{open_id}.json'
        refresh = json.loads(datei.read_text(encoding='utf-8'))['refresh_token']
    t = _post(API + 'oauth/token/', {'client_key': key, 'client_secret': secret, 'grant_type': 'refresh_token',
                                     'refresh_token': refresh})
    if 'access_token' not in t:
        sys.exit(f'TikTok-Zugang abgelaufen: {t.get("error")} - bitte neu anmelden (tiktok.py anmelden)')
    if datei and t.get('refresh_token') and t['refresh_token'] != refresh:  # TikTok kann ihn erneuern
        d = json.loads(datei.read_text(encoding='utf-8')); d['refresh_token'] = t['refresh_token']
        datei.write_text(json.dumps(d, indent=2), encoding='utf-8')
    return t['access_token']


def hochladen(video_pfad, skript_pfad, open_id):
    token = zugang(open_id)
    skript = json.loads(Path(skript_pfad).read_text(encoding='utf-8'))
    # Pflicht laut Doku: vor dem Posten die Moeglichkeiten des Kontos abfragen
    info = _post(API + 'post/publish/creator_info/query/', token=token, json_daten={}).get('data', {})
    erlaubt = info.get('privacy_level_options', [])
    privat = 'SELF_ONLY'  # ungepruefte App: nur privat (Doku); nach der Pruefung waehlt der Nutzer
    if erlaubt and privat not in erlaubt:
        sys.exit(f'Konto erlaubt kein SELF_ONLY: {erlaubt}')
    titel = ' '.join(z.replace('*', '') for z in skript['titel'])
    tags = ' '.join('#' + h.lstrip('#') for h in skript.get('hashtags', []))
    daten = Path(video_pfad).read_bytes()
    groesse = len(daten)
    init = _post(API + 'post/publish/video/init/', token=token, json_daten={
        'post_info': {'title': f'{titel} {tags}'[:2200], 'privacy_level': privat, 'disable_duet': False,
                      'disable_stitch': False, 'disable_comment': False, 'brand_content_toggle': False,
                      'brand_organic_toggle': False, 'is_aigc': True},  # KI-Stimme -> als KI gekennzeichnet
        # Ein Stueck reicht bis 64 MB (unsere Videos: 20-56 MB)
        'source_info': {'source': 'FILE_UPLOAD', 'video_size': groesse, 'chunk_size': groesse,
                        'total_chunk_count': 1}})
    if init.get('error', {}).get('code') not in (None, 'ok'):
        sys.exit(f"TikTok lehnt ab: {init['error'].get('code')} - {init['error'].get('message')}")
    d = init['data']
    urllib.request.urlopen(urllib.request.Request(d['upload_url'], data=daten, method='PUT', headers={
        'Content-Type': 'video/mp4', 'Content-Length': str(groesse),
        'Content-Range': f'bytes 0-{groesse - 1}/{groesse}'}), timeout=600)
    for _ in range(40):  # TikTok verarbeitet das Video - Status abfragen
        s = _post(API + 'post/publish/status/fetch/', token=token, json_daten={'publish_id': d['publish_id']})
        status = s.get('data', {}).get('status')
        print('TikTok-Status:', status)
        if status in ('PUBLISH_COMPLETE', 'FAILED', 'SEND_TO_USER_INBOX'):
            break
        time.sleep(6)
    if status == 'FAILED':
        sys.exit(f"TikTok-Verarbeitung fehlgeschlagen: {s.get('data', {}).get('fail_reason')}")
    print(json.dumps({'publish_id': d['publish_id'], 'status': status, 'sichtbarkeit': privat}, indent=2))


if __name__ == '__main__':
    if sys.argv[1:2] == ['anmelden']:
        anmelden()
    elif sys.argv[1:2] == ['hochladen']:
        hochladen(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(__doc__)
