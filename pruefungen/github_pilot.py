"""Bestehenden GitHub-Zugang nutzen; keine Zugangsdaten speichern oder ausgeben."""
import argparse
import io
import json
import os
import subprocess
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO = 'aKhaaaaaan/contentfabrik'


def zugang():
    for name in ('GH_TOKEN', 'GITHUB_TOKEN'):
        if os.environ.get(name):
            return os.environ[name]
    p = subprocess.run(['git', '-c', 'credential.interactive=never', 'credential', 'fill'],
                       input='protocol=https\nhost=github.com\n\n', text=True,
                       capture_output=True, timeout=30,
                       env={**os.environ, 'GIT_TERMINAL_PROMPT': '0', 'GCM_INTERACTIVE': 'Never'})
    daten = dict(line.split('=', 1) for line in p.stdout.splitlines() if '=' in line)
    if p.returncode or not daten.get('password'):
        raise RuntimeError('Gespeicherter GitHub-Zugang nicht verfuegbar')
    return daten['password']


def api(pfad, daten=None, roh=False):
    req = urllib.request.Request('https://api.github.com/' + pfad,
                                 data=json.dumps(daten).encode() if daten is not None else None,
                                 headers={'Authorization': 'Bearer ' + zugang(),
                                          'Accept': 'application/vnd.github+json',
                                          'Content-Type': 'application/json',
                                          'X-GitHub-Api-Version': '2022-11-28',
                                          'User-Agent': 'contentfabrik-pilot'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            inhalt = r.read()
            return inhalt if roh else json.loads(inhalt) if inhalt else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'GitHub-Abfrage fehlgeschlagen: HTTP {e.code}') from None


def status():
    repo = api('repos/' + REPO)
    print(json.dumps({'repository': repo['full_name'], 'private': repo['private'],
                      'default_branch': repo['default_branch'],
                      'push_erlaubt': repo.get('permissions', {}).get('push')}, ensure_ascii=False))
    workflows = api('repos/' + REPO + '/actions/workflows')
    print(json.dumps({'workflows': [{'id': w['id'], 'path': w['path'], 'state': w['state']}
                                  for w in workflows['workflows']]}, ensure_ascii=False))
    runs = api('repos/' + REPO + '/actions/runs?per_page=15')
    print(json.dumps({'runs': [{k: r.get(k) for k in (
        'id', 'name', 'display_title', 'event', 'status', 'conclusion', 'head_sha',
        'head_branch', 'created_at', 'updated_at', 'html_url')}
        for r in runs['workflow_runs']]}, ensure_ascii=False))


def details(run):
    jobs = api(f'repos/{REPO}/actions/runs/{run}/jobs')
    print(json.dumps({'jobs': [{k: j.get(k) for k in ('id', 'name', 'status', 'conclusion', 'steps')}
                              for j in jobs['jobs']]}, ensure_ascii=False))
    artifacts = api(f'repos/{REPO}/actions/runs/{run}/artifacts')
    print(json.dumps({'artifacts': [{k: a.get(k) for k in ('id', 'name', 'size_in_bytes', 'expired')}
                                   for a in artifacts['artifacts']]}, ensure_ascii=False))
    if all(j['status'] == 'completed' for j in jobs['jobs']):
        with zipfile.ZipFile(io.BytesIO(api(f'repos/{REPO}/actions/runs/{run}/logs', roh=True))) as logs:
            for name in logs.namelist():
                if any(w in name.lower() for w in ('baut', 'bauen', 'video und skript', 'freigabe')):
                    zeilen = logs.read(name).decode('utf-8-sig', errors='replace').splitlines()
                    erlaubt = ('/10', 'Traceback', 'Error:', 'Sperr', 'Gesendet:', 'Min.',
                               'Fakten', 'fehler', 'abgebrochen', 'Budget', 'PILOT:', 'bestanden')
                    print(json.dumps({'schritt': name, 'auszug': [z[:600] for z in zeilen
                                       if any(w in z for w in erlaubt)][-60:]}, ensure_ascii=False))


def secrets():
    daten = api(f'repos/{REPO}/actions/secrets')
    print(json.dumps({'secret_namen': [s['name'] for s in daten['secrets']]}))


def dispatch(args):
    inputs = {'kanal': args.kanal, 'videoformat': args.videoformat,
              'thema': args.thema, 'telegram': args.telegram}
    api(f'repos/{REPO}/actions/workflows/pilot.yml/dispatches', {'ref': 'main', 'inputs': inputs})
    print(json.dumps({'gestartet': inputs}, ensure_ascii=False))


def download(artifact):
    ziel = Path('ausgabe/github') / str(artifact)
    ziel.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(api(f'repos/{REPO}/actions/artifacts/{artifact}/zip', roh=True))) as archiv:
        for eintrag in archiv.infolist():
            pfad = (ziel / eintrag.filename).resolve()
            if not pfad.is_relative_to(ziel.resolve()):
                raise RuntimeError('Artefakt enthaelt unzulaessigen Pfad')
        archiv.extractall(ziel)
    print(json.dumps({'artefakt': artifact, 'ordner': str(ziel.resolve())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    befehle = parser.add_subparsers(dest='befehl', required=True)
    befehle.add_parser('status')
    befehle.add_parser('secrets')
    p = befehle.add_parser('details')
    p.add_argument('run', type=int)
    p = befehle.add_parser('download')
    p.add_argument('artifact', type=int)
    p = befehle.add_parser('dispatch')
    p.add_argument('kanal', choices=['business-origin-stories', 'ai-tools-explained'])
    p.add_argument('videoformat', choices=['short', 'lang'])
    p.add_argument('--thema', default='')
    p.add_argument('--telegram', action='store_true')
    args = parser.parse_args()
    if args.befehl == 'status':
        status()
    elif args.befehl == 'secrets':
        secrets()
    elif args.befehl == 'details':
        details(args.run)
    elif args.befehl == 'download':
        download(args.artifact)
    else:
        dispatch(args)
