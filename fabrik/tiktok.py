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
import hashlib, http.server, json, os, secrets, sys, time, urllib.parse, urllib.request, urllib.error, webbrowser
from pathlib import Path

GEHEIM = Path(os.environ.get('CF_GEHEIM', Path.home() / 'Downloads' / 'contentfabrik-geheim'))
RUECKSPRUNG = 'https://contentfabrik.pages.dev/tiktok-callback'
API = 'https://open.tiktokapis.com/v2/'
RECHTE = 'user.info.basic,video.upload,video.publish'


def _schluessel():
    k, s = os.environ.get('TIKTOK_CLIENT_KEY'), os.environ.get('TIKTOK_CLIENT_SECRET')
    if not (k and s) and os.name == 'nt':
        import subprocess  # lokal: per setx gesetzt, in dieser Shell evtl. noch nicht geladen
        hol = lambda n: subprocess.run(['powershell', '-NoProfile', '-Command',
                                        f"[Environment]::GetEnvironmentVariable('{n}','User')"],
                                       capture_output=True, text=True).stdout.strip()
        k, s = k or hol('TIKTOK_CLIENT_KEY'), s or hol('TIKTOK_CLIENT_SECRET')
    if not (k and s):
        raise RuntimeError('TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET fehlen')
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
        import tiktok_tokens
        wert = tiktok_tokens.laden(secret)[open_id]
        refresh = wert['refresh_token'] if isinstance(wert, dict) else wert
        datei = None
    else:
        datei = GEHEIM / f'tiktok-{open_id}.json'
        refresh = json.loads(datei.read_text(encoding='utf-8'))['refresh_token']
    t = _post(API + 'oauth/token/', {'client_key': key, 'client_secret': secret, 'grant_type': 'refresh_token',
                                     'refresh_token': refresh})
    if 'access_token' not in t:
        raise RuntimeError('TikTok-Zugang abgelaufen - bitte neu anmelden (tiktok.py anmelden)')
    if t.get('open_id') and t['open_id'] != open_id:
        raise RuntimeError('TikTok-Zugang gehoert zu einem anderen Konto')
    if datei is None and t.get('refresh_token') and t['refresh_token'] != refresh:
        tiktok_tokens.speichern(open_id, t['refresh_token'], secret)
    if datei and t.get('refresh_token') and t['refresh_token'] != refresh:  # TikTok kann ihn erneuern
        d = json.loads(datei.read_text(encoding='utf-8')); d['refresh_token'] = t['refresh_token']
        from tiktok_tokens import atomar
        atomar(datei, json.dumps(d, indent=2).encode())
    return t['access_token']


def hochladen(video_pfad, skript_pfad, open_id):
    skript = json.loads(Path(skript_pfad).read_text(encoding='utf-8'))
    import texte
    qpfad = Path(skript_pfad).with_name('quellen.json')
    quellen = json.loads(qpfad.read_text(encoding='utf-8')) if qpfad.exists() else []
    caption = texte.tiktok_text(skript, quellen=quellen)
    if texte.tiktok_laenge(caption) > 2200:
        raise ValueError('TikTok-Caption zu lang; Quellenangaben nicht automatisch abschneiden')
    token = zugang(open_id)
    # Pflicht laut Doku: vor dem Posten die Moeglichkeiten des Kontos abfragen
    info = _post(API + 'post/publish/creator_info/query/', token=token, json_daten={}).get('data', {})
    erlaubt = info.get('privacy_level_options', [])
    privat = 'SELF_ONLY'  # ungepruefte App: nur privat (Doku); nach der Pruefung waehlt der Nutzer
    if erlaubt and privat not in erlaubt:
        sys.exit(f'Konto erlaubt kein SELF_ONLY: {erlaubt}')
    daten = Path(video_pfad).read_bytes()
    groesse = len(daten)
    init = _post(API + 'post/publish/video/init/', token=token, json_daten={
        'post_info': {'title': caption, 'privacy_level': privat, 'disable_duet': False,
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


def entwurf(video_pfad, open_id, journal_pfad=None, max_warte_s=90):
    """Video als ENTWURF ins TikTok-Postfach des Kontos (Scope video.upload, „Upload to TikTok").
    Nutzerwunsch 10.10.2026: Upload automatisieren. Direct Post ist ohne TikTok-Pruefung nur privat
    (SELF_ONLY, privates Konto noetig) und die Pruefung schliesst private Werkzeuge aus. Beim Entwurf
    tippt der Nutzer auf die Benachrichtigung und veroeffentlicht selbst - oeffentlich, mit eigener
    Musik und Beschreibung. Gibt den Endstatus zurueck ('SEND_TO_USER_INBOX' = angekommen)."""
    pfad = Path(video_pfad)
    groesse = pfad.stat().st_size
    if groesse <= 0:
        raise ValueError('Leeres TikTok-Video')
    with pfad.open('rb') as f:
        sha = hashlib.file_digest(f, 'sha256').hexdigest()
    konto = hashlib.sha256(open_id.encode()).hexdigest()
    journal = Path(journal_pfad) if journal_pfad else GEHEIM / 'uploads' / f'{konto}-{sha}.json'
    stand = json.loads(journal.read_text(encoding='utf-8')) if journal and journal.exists() else {}
    if stand and (stand.get('video_sha256') != sha or stand.get('konto_sha256') != konto):
        raise ValueError('TikTok-Uploadjournal gehoert zu einem anderen Video/Konto')
    def sichern():
        if journal:
            from tiktok_tokens import atomar
            atomar(journal, json.dumps(stand, indent=2).encode())
    if stand.get('status') in ('SEND_TO_USER_INBOX', 'PUBLISH_COMPLETE'):
        return stand['status']
    if stand.get('status') == 'FAILED':
        raise RuntimeError('Vorheriger TikTok-Upload fehlgeschlagen; vor neuem Upload pruefen')
    if stand and not stand.get('publish_id') and stand.get('status') not in ('INIT_ABGELEHNT', TRANSFER_LEER):
        raise RuntimeError('Vorherige TikTok-Initialisierung unbestaetigt; vor neuem Upload pruefen')
    token = zugang(open_id)
    if not stand.get('publish_id'):
        # Falls /init nach Annahme die Verbindung verliert, nicht blind einen zweiten Upload starten.
        stand.update(video_sha256=sha, konto_sha256=konto, status='INIT_UNKLAR')
        sichern()
        chunk, anzahl = chunk_plan(groesse)
        try:
            d = _daten(_post(API + 'post/publish/inbox/video/init/', token=token, json_daten={
                'source_info': {'source': 'FILE_UPLOAD', 'video_size': groesse, 'chunk_size': chunk,
                                'total_chunk_count': anzahl}}))
        except TikTokAPIError:
            stand['status'] = 'INIT_ABGELEHNT'  # API bestaetigt Ablehnung; spaeterer Neuversuch ist sicher.
            sichern()
            raise
        stand.update(publish_id=d['publish_id'], status='PROCESSING_UPLOAD', init_zeit=time.time())
        sichern()  # publish_id vor dem ersten Byte sichern; keine Upload-URL/Schluessel ins Journal
        with pfad.open('rb') as f:
            offset = 0
            for i in range(anzahl):
                daten = f.read(chunk if i < anzahl - 1 else groesse - offset)
                req = urllib.request.Request(d['upload_url'], data=daten, method='PUT', headers={
                    'Content-Type': 'video/mp4', 'Content-Length': str(len(daten)),
                    'Content-Range': f'bytes {offset}-{offset + len(daten) - 1}/{groesse}'})
                try:
                    with urllib.request.urlopen(req, timeout=120) as reply:
                        if reply.status != (201 if i == anzahl - 1 else 206):
                            raise RuntimeError('TikTok hat den Dateitransfer nicht bestaetigt')
                except (urllib.error.URLError, TimeoutError):
                    raise RuntimeError('TikTok-Dateitransfer unbestaetigt; bestehenden Status pruefen') from None
                offset += len(daten)
    ende = time.monotonic() + max_warte_s
    while True:
        s = status_abfragen(stand['publish_id'], token=token)
        stand.update(s)
        sichern()
        if stand['status'] in ('SEND_TO_USER_INBOX', 'PUBLISH_COMPLETE', 'FAILED') or time.monotonic() >= ende:
            break
        time.sleep(min(6, max(0, ende - time.monotonic())))
    if stand['status'] == 'FAILED':
        raise RuntimeError('TikTok-Verarbeitung fehlgeschlagen: ' + str(stand.get('fail_reason', 'unbekannt')))
    print(json.dumps({'publish_id': stand['publish_id'], 'status': stand['status']}))
    return stand['status']


class TikTokAPIError(RuntimeError):
    pass


# GEMESSEN 17.10.2026 (Tesla, publish_id ...7294614): /init angenommen, Dateitransfer abgebrochen.
# Danach meldete TikTok fuer immer PROCESSING_UPLOAD mit uploaded_bytes 0; jeder Durchlauf fragte nur
# den Status ab, das Video kam nie an. Nach LEER_NACH_S ohne ein einziges Byte gilt der Upload als
# leer und wird neu angemeldet - ohne angekommene Bytes kein Doppel-Entwurf moeglich.
TRANSFER_LEER = 'TRANSFER_LEER'
LEER_NACH_S = 15 * 60


def leer_verwerfen(stand, jetzt=None):
    """True (und Journal fuer Neustart vorbereitet), wenn der Upload seit LEER_NACH_S bei 0 Bytes steht."""
    jetzt = time.time() if jetzt is None else jetzt
    if stand.get('status') != 'PROCESSING_UPLOAD' or stand.get('uploaded_bytes') != 0 \
            or jetzt - float(stand.get('init_zeit') or 0) < LEER_NACH_S:
        return False
    stand.setdefault('verworfene_publish_ids', []).append(stand.pop('publish_id'))
    stand.pop('uploaded_bytes', None)
    stand.pop('init_zeit', None)
    stand['status'] = TRANSFER_LEER
    return True


def _daten(reply):
    error = reply.get('error')
    code = error.get('code') if isinstance(error, dict) else None
    if code and code != 'ok':
        raise TikTokAPIError('TikTok-Anfrage fehlgeschlagen: ' + str(code))
    if reply.get('_http') or code != 'ok' or not isinstance(reply.get('data'), dict):
        raise RuntimeError('TikTok-Anfrage mit ungueltiger Antwort')
    return reply['data']


def status_abfragen(publish_id, open_id=None, token=None):
    d = _daten(_post(API + 'post/publish/status/fetch/', token=token or zugang(open_id),
                     json_daten={'publish_id': publish_id}))
    if not isinstance(d.get('status'), str) or not d['status']:
        raise RuntimeError('TikTok-Antwort ohne Status')
    return {k: d[k] for k in ('status', 'uploaded_bytes', 'fail_reason') if k in d}


def chunk_plan(groesse):
    """TikTok: max. 64 MB je Stueck; Restbytes in das letzte Stueck (max. 128 MB)."""
    chunk = min(groesse, 64 * 1024 * 1024)
    if chunk <= 0:
        raise ValueError('Leeres TikTok-Video')
    anzahl = max(1, groesse // chunk)
    if groesse > chunk and anzahl == 1:
        chunk, anzahl = groesse // 2, 2
    if anzahl > 1000:
        raise ValueError('TikTok-Video zu gross')
    return chunk, anzahl


def konten():
    """Lokal angemeldete TikTok-Konten: [(konto, open_id)] - ohne Schluessel auszugeben."""
    aus = []
    for p in sorted(GEHEIM.glob('tiktok-*.json')):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
            aus.append((d.get('konto', '?'), d['open_id']))
        except (OSError, ValueError, KeyError):
            continue
    return aus


if __name__ == '__main__':
    if sys.argv[1:2] == ['anmelden']:
        anmelden()
    elif sys.argv[1:2] == ['hochladen']:
        hochladen(sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1:2] == ['entwurf']:
        entwurf(sys.argv[2], sys.argv[3])
    elif sys.argv[1:2] == ['konten']:
        for name, oid in konten():
            print(name, oid[:6] + '...')
    elif sys.argv[1:2] == ['status']:
        print(json.dumps(status_abfragen(sys.argv[2], sys.argv[3])))
    elif sys.argv[1:2] == ['tageslauf']:
        from tiktok_entwurf import tageslauf
        tageslauf(sys.argv[2])
    elif sys.argv[1:2] == ['secrets-vorbereiten']:
        from tiktok_entwurf import secrets_vorbereiten
        secrets_vorbereiten(sys.argv[2])
    elif sys.argv[1:2] == ['freigaben']:
        from tiktok_freigabe import abarbeiten
        abarbeiten()
    else:
        print(__doc__)
