"""Bestaetigtes Video exakt per SHA laden, harte Gates pruefen, als TikTok-Entwurf hochladen."""
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.parse
import urllib.request
import zipfile

import kanalstandard
import lernen
import tiktok
from tiktok_entwurf import konto_finden, hinweis
from tiktok_tokens import atomar

QUEUE = Path('verlauf/tiktok-freigaben.json')
AKTIV = ('freigegeben', 'PROCESSING_UPLOAD', 'PROCESSING_DOWNLOAD', 'wartet_api', 'postfach_voll')
# TikTok-Doku (Upload-Endpunkt, geprueft 14.10.2026): hoechstens 5 offene Entwuerfe je 24 h,
# danach HTTP 403 spam_risk_too_many_pending_share. Das ist kein Fehler der Datei: spaeter erneut.
POSTFACH_VOLL_PAUSE_S = 3600
FERTIG = ('SEND_TO_USER_INBOX', 'PUBLISH_COMPLETE', 'gesperrt', 'fehlgeschlagen', 'FAILED')


def offen(e):
    return e['status'] in AKTIV or (e['status'] in FERTIG and not e.get('gemeldet'))


def melden(e, konto, q):
    terminal = e['status'] in FERTIG
    if (e['status'] not in FERTIG + ('PROCESSING_UPLOAD', 'PROCESSING_DOWNLOAD', 'wartet_api', 'postfach_voll')
            or (terminal and e.get('gemeldet'))
            or (not terminal and e['status'] in e.get('status_meldungen', []))) or not all(os.environ.get(k) for k in (
            'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID')):
        return
    text = _stand_text(e, konto)
    try:
        from freigabe import telegram
        telegram('sendMessage', {'chat_id': os.environ['TELEGRAM_CHAT_ID'], 'text': text})
        if e['status'] == 'SEND_TO_USER_INBOX' and e.get('tiktok_text'):
            # Genau jetzt wird der Text gebraucht; beim Videoversand lag er oft Stunden zurueck.
            from freigabe import kopieren_senden
            kopieren_senden(os.environ['TELEGRAM_CHAT_ID'], 'TikTok-Text zum Einfuegen', e['tiktok_text'])
        if terminal:
            e['gemeldet'] = True
        else:
            e.setdefault('status_meldungen', []).append(e['status'])
        speichern(q)
    except Exception:
        pass


def _stand_text(e, konto):
    status = e['status']
    prefix = f'TikTok @{konto}: '
    if status in ('SEND_TO_USER_INBOX', 'PUBLISH_COMPLETE'):
        return hinweis(status, konto)
    messages = {
        'freigegeben': 'Freigabe gespeichert; der automatische Upload ist vorgemerkt. '
                      'TikTok hat noch keine Zustellung bestaetigt.',
        'PROCESSING_UPLOAD': 'Die Datei wurde uebertragen und wird von TikTok verarbeitet. '
                             'Die Postfach-Benachrichtigung ist noch nicht bestaetigt.',
        'PROCESSING_DOWNLOAD': 'TikTok verarbeitet die Datei. Die Postfach-Benachrichtigung '
                               'ist noch nicht bestaetigt.',
        'wartet_api': 'Der Upload oder die Statusabfrage konnte nicht abgeschlossen werden. '
                      'Die Pipeline versucht es erneut; eine Zustellung ist noch nicht bestaetigt.',
        'abgelehnt': 'Dieses Video ist abgelehnt; kein Upload wird gestartet.',
        'postfach_voll': 'TikTok nimmt gerade keinen weiteren Entwurf an (hoechstens 5 offene Entwuerfe '
                         'in 24 Stunden). Bitte offene Entwuerfe in der App veroeffentlichen oder loeschen. '
                         'Der Upload wird automatisch stuendlich erneut versucht.',
        'gesperrt': 'Die Datei, Qualitaetspruefung oder Kontozuordnung ist gesperrt. '
                    'Kein neuer Upload wird automatisch gestartet.',
        'fehlgeschlagen': 'Upload oder Statusabfrage nach drei Versuchen fehlgeschlagen. '
                         'Die Zustellung ist nicht bestaetigt; kein neuer Upload wird gestartet.',
        'FAILED': 'TikTok hat die Verarbeitung abgelehnt. Kein neuer Upload wird gestartet.',
    }
    return prefix + messages.get(status, 'Status unbekannt; Zustellung nicht bestaetigt.')


def status_text(video):
    """Nur gespeicherte Freigabe lesen: Statusklick autorisiert niemals einen Upload."""
    e = next((x for x in laden() if x.get('id') == video.get('video_sha256')), None)
    profil = kanalstandard.nach_name(video.get('kanal')) or {}
    konto = profil.get('tiktok_name', '?')
    from bildbezug import revision_gruende
    if revision_gruende(video.get('video_sha256')):
        return (f'TikTok @{konto}: Die nachtraegliche Bild-Text-Pruefung sperrt diese Videodatei. '
                'Die Motive passen nicht ausreichend zum Sprechtext. Warte auf die korrigierte Fassung; '
                'fuer dieses Original wird kein neuer Upload gestartet.')
    if e is None:
        return (f'TikTok @{konto}: Fuer dieses Video ist noch keine Uploadfreigabe gespeichert. '
                'Story-/Videonoten starten keinen Upload. Tippe beim Video auf '
                '"TikTok-Entwurf hochladen", wenn es passt.')
    return _stand_text(e, konto)


def laden():
    return json.loads(QUEUE.read_text(encoding='utf-8')) if QUEUE.exists() else []


def speichern(d):
    atomar(QUEUE, (json.dumps(d, indent=1, ensure_ascii=False) + '\n').encode())


def gleiches_thema(video, q):
    """Telegram-Nummer einer frueheren, nicht abgelehnten TikTok-Freigabe desselben Kanals und Themas.

    GEMESSEN 18.10.2026 (TikTok-Profile): Airbnb (Telegram 501 + 548: 431 + 255 Aufrufe), Fincept (508 + 530:
    182 + 155) - je zwei Fassungen desselben Themas hochgeladen, weil die Sperre nur die Datei (SHA) kannte.
    Eine abgelehnte, gesperrte oder gescheiterte erste Fassung blockiert nicht.
    """
    thema = str(video.get('thema') or '').strip().lower()
    if not thema:
        return None
    try:
        videos = json.loads(Path('verlauf/telegram-videos.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        videos = []
    zu_sha = {v.get('video_sha256'): v for v in videos if isinstance(v, dict)}
    for e in q:
        if e.get('kanal') != video.get('kanal') or e.get('video_sha256') == video.get('video_sha256') \
                or e.get('status') in ('abgelehnt', 'gesperrt', 'fehlgeschlagen', 'FAILED') \
                or lernen.abgelehnt(e.get('video_sha256') or ''):
            continue
        v = zu_sha.get(e.get('video_sha256')) or {}
        if str(e.get('thema') or v.get('thema') or '').strip().lower() == thema:
            # Nutzerentscheidung 21.10.2026: nach 60 Tagen mit neuem Titel wieder hochladen (neue Zuschauer).
            import themen
            try:
                alter = (datetime.datetime.now(datetime.timezone.utc)
                         - datetime.datetime.fromisoformat(e.get('datum_utc') or v.get('datum_utc'))).days
            except (TypeError, ValueError):
                alter = 0
            if alter >= themen.WIEDERHOLUNG_TAGE and themen._titel_norm(v.get('titel')) \
                    != themen._titel_norm(video.get('titel')):
                continue
            return v.get('message_id') or '?'
    return None


def entscheiden(video, passt, update_id):
    sha = video.get('video_sha256') or ''
    profil = kanalstandard.nach_name(video.get('kanal')) or {}
    cfg = profil.get('tiktok_entwurf') or {}
    if not re.fullmatch(r'[a-f0-9]{64}', sha) or cfg.get('aktiv') is not True or cfg.get('freigabe') != 'telegram':
        return 'Fuer dieses Video ist kein TikTok-Entwurf-Upload eingerichtet.'
    q = laden()
    alt = next((x for x in q if x['id'] == sha), None)
    if not passt:
        eintrag = {'id': f'tiktok-ablehnen-{update_id}', 'video_sha256': sha, 'status': 'abgelehnt',
                   'kanal': video.get('kanal'), 'wortlaut': 'Nutzer hat dieses Video vor TikTok-Upload abgelehnt.'}
        import bewertung
        bewertung._eintragen(eintrag)
        if alt:
            alt['status'] = 'abgelehnt'
            speichern(q)
        return 'Abgelehnt gespeichert. Diese Datei wird nicht zu TikTok hochgeladen.'
    if lernen.abgelehnt(sha):
        return 'Dieses Video wurde bereits abgelehnt und bleibt fuer Uploads gesperrt.'
    if not str(video.get('upload_run_id') or '').isdigit():
        return 'Originaldatei nicht zugeordnet - kein Upload gestartet.'
    if alt:
        return 'Freigabe war schon gespeichert. Es wird kein zweiter Upload gestartet.\n' + status_text(video)
    frueher = gleiches_thema(video, q)
    if frueher:
        return (f'Zu diesem Thema liegt schon ein TikTok-Entwurf (Telegram {frueher}, juenger als 60 Tage). Kein zweiter Upload: '
                'zwei Fassungen desselben Themas teilen sich die Aufrufe. Soll die neue Fassung hin, '
                'die alte in TikTok loeschen und hier beim alten Video "Ablehnen" tippen, dann erneut "Passt".')
    q.append({'id': sha, 'video_sha256': sha, 'kanal': video['kanal'], 'run_id': str(video['upload_run_id']),
              'thema': video.get('thema'), 'status': 'freigegeben', 'update_id': update_id,
              'datum_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    speichern(q)
    return ('Passt gespeichert. Der automatische Upload ins TikTok-Postfach wird vorbereitet. '
            'Du erhaeltst eine weitere Nachricht, sobald TikTok die Zustellung bestaetigt. '
            'Der Abholer laeuft etwa alle 5 Minuten; GitHub kann den Start verzoegern.')


class OhneTokenRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != 'https':
            raise RuntimeError('Unsicherer Artefakt-Redirect')
        r = super().redirect_request(req, fp, code, msg, headers, newurl)
        if r and urllib.parse.urlsplit(req.full_url).netloc != urllib.parse.urlsplit(newurl).netloc:
            r.remove_header('Authorization')
        return r


def _github(url, roh=False):
    token = os.environ['GITHUB_TOKEN']
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json', 'User-Agent': 'contentfabrik-tiktok'})
    with urllib.request.build_opener(OhneTokenRedirect()).open(req, timeout=60) as r:
        data = r.read(128 * 1024 * 1024 + 1)
    if len(data) > 128 * 1024 * 1024:
        raise ValueError('TikTok-Artefakt zu gross')
    return data if roh else json.loads(data)


class ArtefaktFehltNoch(RuntimeError):
    """Lauf gerade beendet, Artefakt bei GitHub noch nicht abrufbar - normaler Wartezustand."""


# GEMESSEN 17.10.2026 (Tesla, Klick 18:50, Job-Ende 18:45): erster Versuch "wartet_api" samt
# Fehlermeldung auf Telegram, der zweite 5 Min. spaeter klappte. Bis 3 Std. nach dem Klick zaehlt
# ein fehlendes Artefakt nicht als Fehlversuch und loest keine Meldung aus.
ARTEFAKT_WARTEN_S = 3 * 3600


def original_laden(eintrag, ordner):
    run = eintrag['run_id']
    if not str(run).isdigit():
        raise ValueError('Ungueltiger Originallauf')
    repo = os.environ.get('GITHUB_REPOSITORY', 'aKhaaaaaan/contentfabrik')
    api = f'https://api.github.com/repos/{repo}'
    d = _github(f'{api}/actions/runs/{run}/artifacts?per_page=100')
    profil = kanalstandard.nach_name(eintrag['kanal'])
    slug = next(k for k, p in kanalstandard.alle().items() if p['name'] == profil['name'])
    a = next((a for a in d['artifacts'] if a['name'] in (f'video-{slug}', f'pilot-{slug}-short')
              and not a['expired']), None)
    if a is None:
        if any(a['name'] in (f'video-{slug}', f'pilot-{slug}-short') and a['expired'] for a in d['artifacts']):
            raise FileNotFoundError('Originalartefakt abgelaufen')
        raise ArtefaktFehltNoch('Originalartefakt noch nicht verfuegbar')
    blob = _github(f'{api}/actions/artifacts/{a["id"]}/zip', roh=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for name in ('short.mp4', 'skript.json', 'kritik.json'):
            files = [p for p in z.infolist() if Path(p.filename).name == name]
            if len(files) != 1 or files[0].file_size > 128 * 1024 * 1024:
                raise ValueError('Originalartefakt ist unvollstaendig oder mehrdeutig')
            # Nur ausdruecklich ausgewaehlte Dateien unter festem Namen, keine Zip-Pfade extrahieren.
            (Path(ordner) / name).write_bytes(z.read(files[0]))


def pruefen(eintrag, ordner):
    from qualitaet import bewerten, nur_ki_geschmack, ENTWURF_MIN
    from dramaturgie import videoformat
    p = Path(ordner)
    with (p / 'short.mp4').open('rb') as f:
        sha = hashlib.file_digest(f, 'sha256').hexdigest()
    s, k = [json.loads((p / (name + '.json')).read_text(encoding='utf-8')) for name in ('skript', 'kritik')]
    if sha != eintrag['video_sha256'] or k.get('video_sha256') != sha or s.get('kanal') != eintrag['kanal'] \
            or videoformat(s) != 'short' or lernen.abgelehnt(sha):
        raise ValueError('Freigabe gehoert nicht zu dieser Datei oder Datei wurde abgelehnt')
    note, gruende = bewerten(s, k)
    # Menschliches „Passt“ kann KI-Geschmack und (seit 15.10.2026, Nutzerentscheidung) einen reinen
    # Bildbezug-Befund ueberstimmen, nie Fakten, Technik oder Endton.
    from qualitaet import nur_bildbezug
    if gruende and not ((nur_ki_geschmack(gruende) and (note or 0) >= ENTWURF_MIN) or nur_bildbezug(gruende)):
        raise ValueError('Harte Qualitaetssperre - kein TikTok-Upload')


def abarbeiten():
    q = laden()
    if not any(offen(e) for e in q):
        return
    if not all(os.environ.get(k) for k in ('TIKTOK_CLIENT_KEY', 'TIKTOK_CLIENT_SECRET', 'TIKTOK_TOKENS',
                                          'TIKTOK_TOKEN_CACHE', 'GITHUB_TOKEN')):
        print('TikTok-Freigaben warten auf die Einrichtung der GitHub-Secrets.')
        return
    for e in q:
        if e['status'] == 'postfach_voll' and e.get('naechster_versuch', '') >                 datetime.datetime.now(datetime.timezone.utc).isoformat():
            continue
        if e['status'] not in AKTIV:
            profil = kanalstandard.nach_name(e['kanal']) or {}
            melden(e, profil.get('tiktok_name', '?'), q)
            continue
        profil = kanalstandard.nach_name(e['kanal']) or {}
        konto = profil.get('tiktok_name')
        cfg = profil.get('tiktok_entwurf') or {}
        if cfg.get('aktiv') is not True or cfg.get('freigabe') != 'telegram' or lernen.abgelehnt(e['video_sha256']):
            e['status'] = 'abgelehnt'
            speichern(q)
            continue
        journal = Path('verlauf/tiktok') / f'{e["video_sha256"]}.json'
        try:
            oid = konto_finden(konto)
            stand = json.loads(journal.read_text(encoding='utf-8')) if journal.exists() else {}
            if stand.get('publish_id'):
                if stand.get('konto_sha256') != hashlib.sha256(oid.encode()).hexdigest() \
                        or stand.get('video_sha256') != e['video_sha256']:
                    raise ValueError('Uploadjournal passt nicht zur Freigabe')
                status = tiktok.status_abfragen(stand['publish_id'], open_id=oid)
                stand.update(status)
                if tiktok.leer_verwerfen(stand):
                    print('TikTok-Freigabe:', e['video_sha256'][:16], 'leerer Upload verworfen - neue Uebertragung')
                    atomar(journal, json.dumps(stand, indent=2).encode())
                    with tempfile.TemporaryDirectory(prefix='contentfabrik-tiktok-') as tmp:
                        original_laden(e, tmp)
                        pruefen(e, tmp)
                        e['status'] = tiktok.entwurf(Path(tmp) / 'short.mp4', oid, journal, max_warte_s=0)
                else:
                    atomar(journal, json.dumps(stand, indent=2).encode())
                    e['status'] = stand['status']
            else:
                with tempfile.TemporaryDirectory(prefix='contentfabrik-tiktok-') as tmp:
                    original_laden(e, tmp)
                    pruefen(e, tmp)
                    try:
                        import texte
                        e['tiktok_text'] = texte.tiktok_text(json.loads(
                            (Path(tmp) / 'skript.json').read_text(encoding='utf-8')))
                    except Exception:
                        pass  # Komfort: fehlt der Text, bleibt der Upload trotzdem moeglich.
                    e['status'] = tiktok.entwurf(Path(tmp) / 'short.mp4', oid, journal, max_warte_s=0)
            e.pop('fehler_typ', None)
        except (ValueError, FileNotFoundError):
            e['status'] = 'gesperrt'
        except ArtefaktFehltNoch:
            alter = (datetime.datetime.now(datetime.timezone.utc)
                     - datetime.datetime.fromisoformat(e['datum_utc'])).total_seconds()
            if alter < ARTEFAKT_WARTEN_S:
                print('TikTok-Freigabe:', e['video_sha256'][:16], 'wartet auf das Videoartefakt')
                continue
            e['versuche'] = e.get('versuche', 0) + 1
            e['status'] = 'wartet_api' if e['versuche'] < 3 else 'fehlgeschlagen'
            e['fehler_typ'] = 'ArtefaktFehltNoch'
        except Exception as err:
            if 'spam_risk_too_many_pending_share' in str(err):
                e['status'] = 'postfach_voll'
                e['naechster_versuch'] = (datetime.datetime.now(datetime.timezone.utc)
                                          + datetime.timedelta(seconds=POSTFACH_VOLL_PAUSE_S)).isoformat()
                speichern(q)
                melden(e, konto, q)
                continue
            e['versuche'] = e.get('versuche', 0) + 1
            e['status'] = 'wartet_api' if e['versuche'] < 3 else 'fehlgeschlagen'
            e['fehler_typ'] = type(err).__name__
        speichern(q)  # Originalhash/publish_id vor jeder weiteren Bearbeitung dauerhaft sichern.
        melden(e, konto, q)
        print('TikTok-Freigabe:', e['video_sha256'][:16], e['status'])
