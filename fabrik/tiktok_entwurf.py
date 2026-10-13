"""AI-Tagesvideos nach bestaetigter Telegram-Zustellung ins TikTok-Postfach hochladen."""
import datetime
import hashlib
import json
import os
from pathlib import Path

import tiktok
import texte
from tiktok_tokens import atomar


def konto_finden(name):
    name = name.lower().lstrip('@')
    if os.environ.get('TIKTOK_TOKENS'):
        daten = json.loads(os.environ['TIKTOK_TOKENS'])
        treffer = [oid for oid, d in daten.items() if isinstance(d, dict)
                   and str(d.get('konto', '')).lower().lstrip('@') == name
                   and 'video.upload' in d.get('rechte', '').split(',')]
    else:
        treffer = [oid for konto, oid in tiktok.konten() if konto.lower().lstrip('@') == name]
    if len(treffer) != 1:
        raise ValueError('TikTok-Konto nicht eindeutig verbunden oder video.upload fehlt')
    return treffer[0]


def hinweis(status, konto):
    if status == 'SEND_TO_USER_INBOX':
        return (f'TikTok hat die Zustellung ins Postfach von @{konto} bestaetigt. '
                'Wechsle in der TikTok-App zu diesem Konto und oeffne Posteingang / Systembenachrichtigungen. '
                'Oeffne dort die Upload-Benachrichtigung, '
                'pruefe das Video, kopiere den automatisch erzeugten TikTok-Text aus Telegram und '
                'schalte KI-generierte Inhalte ein. TikToks Video-Entwurf-API nimmt keine Beschreibung '
                'oder Hashtags entgegen; der Text wird deshalb noch nicht automatisch eingetragen.')
    if status == 'PUBLISH_COMPLETE':
        return f'TikTok meldet: Der Entwurf fuer @{konto} wurde bereits in der App veroeffentlicht.'
    return f'TikTok-Upload fuer @{konto}: {status}. Zustellung ins Postfach noch nicht bestaetigt.'


def tageslauf(slug, ausgabe='ausgabe'):
    aus = Path(ausgabe)
    profil = json.loads(Path(f'kanaele/{slug}.json').read_text(encoding='utf-8'))
    config = profil.get('tiktok_entwurf') or {}
    if config.get('aktiv') is not True:
        return {'status': 'deaktiviert'}
    result = {'konto': profil['tiktok_name'], 'status': 'nicht_eingerichtet'}
    def ergebnis():
        aus.mkdir(parents=True, exist_ok=True)
        atomar(aus / 'tiktok.json', json.dumps(result, ensure_ascii=False, indent=2).encode())
        print(json.dumps(result, ensure_ascii=False))
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
                f.write(f"\nTikTok @{result['konto']}: **{result['status']}**\n")
        return result
    if config.get('freigabe') == 'telegram':
        try:
            b = json.loads((aus / 'bericht.json').read_text(encoding='utf-8'))
            result['status'] = 'wartet_auf_telegram_freigabe' if b.get('status') == 'gesendet' \
                and b.get('kanal') == slug else 'kein_zugestelltes_tagesvideo'
        except (OSError, ValueError):
            result['status'] = 'kein_zugestelltes_tagesvideo'
        return ergebnis()
    # In CI keine lokalen Konten suchen und keine interaktive Anmeldung starten.
    if os.environ.get('GITHUB_ACTIONS') == 'true' and not all(os.environ.get(n) for n in (
            'TIKTOK_CLIENT_KEY', 'TIKTOK_CLIENT_SECRET', 'TIKTOK_TOKENS', 'TIKTOK_TOKEN_CACHE')):
        return ergebnis()
    try:
        bericht = json.loads((aus / 'bericht.json').read_text(encoding='utf-8'))
        import budget
        if bericht.get('status') != 'gesendet' or bericht.get('kanal') != slug or bericht.get('datum') != budget.heute():
            result['status'] = 'kein_zugestelltes_tagesvideo'
            return ergebnis()
        skript = json.loads((aus / 'skript.json').read_text(encoding='utf-8'))
        kritik = json.loads((aus / 'kritik.json').read_text(encoding='utf-8'))
        from dramaturgie import videoformat
        from qualitaet import bewerten
        import lernen
        video = aus / 'short.mp4'
        with video.open('rb') as f:
            sha = hashlib.file_digest(f, 'sha256').hexdigest()
        if skript.get('kanal') != profil['name'] or videoformat(skript) == 'lang' \
                or bewerten(skript, kritik)[1] or kritik.get('video_sha256') != sha or lernen.abgelehnt(sha):
            result['status'] = 'qualitaetssperre'
            return ergebnis()
        result['titel'] = texte.upload_titel(skript, datetime.date.fromisoformat(bericht['datum']))
        oid = konto_finden(result['konto'])
        journal = Path('verlauf/tiktok') / f'{slug}-{sha}.json'
        result['status'] = tiktok.entwurf(video, oid, journal_pfad=journal)
        result['hinweis'] = hinweis(result['status'], result['konto'])
        # Ein TikTok-/Hinweisfehler darf ein schon geliefertes Telegram-Video nie als fehlend markieren.
        if os.environ.get('TELEGRAM_BOT_TOKEN') and os.environ.get('TELEGRAM_CHAT_ID'):
            from freigabe import telegram
            try:
                telegram('sendMessage', {'chat_id': os.environ['TELEGRAM_CHAT_ID'], 'text': result['hinweis']})
            except Exception:
                result['hinweis_zugestellt'] = False
    except Exception as e:
        result.update(status='fehler', fehler_typ=type(e).__name__)
        # Exception-Texte koennen geheime Upload-URLs enthalten. Nur den Typ ausgeben.
    return ergebnis()


def secrets_vorbereiten(konto):
    """Nur das ausdruecklich benannte Konto fuer das GitHub-Secret exportieren; nichts hochladen."""
    oid = konto_finden(konto)
    d = json.loads((tiktok.GEHEIM / f'tiktok-{oid}.json').read_text(encoding='utf-8'))
    if 'video.upload' not in d.get('rechte', '').split(','):
        raise ValueError('Konto hat video.upload nicht freigegeben')
    name = konto.lower().lstrip('@')
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789._' for c in name):
        raise ValueError('Ungueltiger TikTok-Kontoname')
    pfad = tiktok.GEHEIM / f'github-tiktok-tokens-{name}.json'
    atomar(pfad, json.dumps({oid: {k: d[k] for k in ('konto', 'refresh_token', 'rechte')}}, indent=2).encode())
    print('Secret TIKTOK_TOKENS vorbereitet in:', pfad)
    print('TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET und TIKTOK_TOKENS selbst in GitHub Actions eintragen.')
