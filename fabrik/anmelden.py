"""Einmal je Kanal am PC: Google-Anmeldung, im Google-Fenster den Kanal waehlen.

Speichert einen Dauer-Schluessel (refresh_token) je Kanal in
Downloads/contentfabrik-geheim/ - NIE im Projekt, nie im Chat.

Aufruf:  python fabrik/anmelden.py
Ablauf:  Browser oeffnet sich -> Konto -> KANAL waehlen -> „Zulassen".

Ohne Zusatzpakete: offizieller OAuth-Weg fuer Desktop-Apps (Loopback + PKCE),
https://developers.google.com/identity/protocols/oauth2/native-app
"""
import base64, hashlib, http.server, json, os, secrets, sys, urllib.parse, urllib.request, webbrowser
from pathlib import Path

GEHEIM = Path(os.environ.get('CF_GEHEIM', Path.home() / 'Downloads' / 'contentfabrik-geheim'))
# Hochladen, Kanaldaten lesen, Zahlen fuers Dashboard - nichts weiter.
RECHTE = ['https://www.googleapis.com/auth/youtube.upload',
          'https://www.googleapis.com/auth/youtube.readonly',
          'https://www.googleapis.com/auth/yt-analytics.readonly']


def client():
    dateien = sorted(GEHEIM.glob('client_secret*.json'))
    if not dateien:
        sys.exit(f'Keine client_secret-Datei in {GEHEIM}')
    return json.loads(dateien[0].read_text(encoding='utf-8'))['installed']


def anmelden():
    c = client()
    pruef = secrets.token_urlsafe(64)
    zustand = secrets.token_urlsafe(16)
    antwort = {}

    class Empfang(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if 'code' not in q and 'error' not in q:
                self.send_response(404); self.end_headers(); return
            antwort.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8'); self.end_headers()
            ok = 'code' in q and q.get('state', [''])[0] == zustand
            self.wfile.write(('<h2>Fertig - dieses Fenster kann zu.</h2>' if ok else
                              '<h2>Abgebrochen - bitte noch einmal starten.</h2>').encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(('127.0.0.1', 0), Empfang)
    ruf = f'http://127.0.0.1:{server.server_port}'
    url = c['auth_uri'] + '?' + urllib.parse.urlencode({
        'client_id': c['client_id'], 'redirect_uri': ruf, 'response_type': 'code',
        'scope': ' '.join(RECHTE), 'state': zustand,
        # offline + consent: nur so gibt Google einen Dauer-Schluessel heraus
        'access_type': 'offline', 'prompt': 'consent select_account',
        'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(pruef.encode()).digest()).rstrip(b'=').decode(),
        'code_challenge_method': 'S256'})
    print('Browser oeffnet sich. Falls nicht, diese Adresse oeffnen:\n' + url)
    webbrowser.open(url)
    while 'code' not in antwort and 'error' not in antwort:
        server.handle_request()
    if antwort.get('state') != zustand or 'code' not in antwort:
        sys.exit('Anmeldung abgebrochen: ' + antwort.get('error', 'falscher Zustand'))

    token = json.load(urllib.request.urlopen(urllib.request.Request(c['token_uri'], data=urllib.parse.urlencode({
        'code': antwort['code'], 'client_id': c['client_id'], 'client_secret': c['client_secret'],
        'redirect_uri': ruf, 'grant_type': 'authorization_code', 'code_verifier': pruef}).encode())))
    if 'refresh_token' not in token:
        sys.exit('Google hat keinen Dauer-Schluessel geliefert - bitte noch einmal starten.')

    kanal = json.load(urllib.request.urlopen(urllib.request.Request(
        'https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true',
        headers={'Authorization': 'Bearer ' + token['access_token']})))['items'][0]
    name = kanal['snippet']['title']
    datei = GEHEIM / f"token-{kanal['id']}.json"
    datei.write_text(json.dumps({'kanal': name, 'kanal_id': kanal['id'], 'refresh_token': token['refresh_token'],
                                 'rechte': token.get('scope', '')}, indent=2), encoding='utf-8')
    print(f"\nAngemeldet: {name}  ({kanal['statistics'].get('subscriberCount', '?')} Abonnenten)")
    print(f'Gespeichert in {datei}')


if __name__ == '__main__':
    anmelden()
