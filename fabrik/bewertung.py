"""Bewertung gelieferter Videos direkt in Telegram: Knoepfe unter dem Video.

GEMELDET 07.10.2026: „Kann ich vom Telegram-Kanal aus, wenn die Videos ankommen,
die mir gefallen oder nicht, ablehnen oder akzeptieren?" Bisher ging nur freier
Text mit „Feedback:", ohne Bezug zu einem bestimmten Video.

Ablauf: freigabe.py haengt die Knoepfe an und merkt sich message_id -> Video
(verlauf/telegram-videos.json, wird vom Videolauf gesichert). Der Themenlauf
(alle 4 h) holt Knopfdruecke und Antworten auf ein Video ab und legt sie in
lernen/redaktion.json ab. Ein Ablehnen sperrt die Datei fuer erneuten Versand
(lernen.abgelehnt) und fliesst als Lernhinweis in kuenftige Skripte.

Das ist ein schnelles Nutzerurteil, KEINE vollstaendige Sichtpruefung im Sinne
von qualitaetsserie.bewertung_eintragen (dort sind acht Pruefpunkte Pflicht).
"""
import datetime
import re
import json
from pathlib import Path

VIDEOS = Path('verlauf/telegram-videos.json')
REDAKTION = Path('lernen/redaktion.json')
NOTEN = ('4', '5', '6', '7', '8', '9', '10')


def knoepfe(sha):
    kurz = sha[:16]
    return {'inline_keyboard': [
        [{'text': '✅ Gefällt mir', 'callback_data': f'bw:{kurz}:ok'},
         {'text': '❌ Ablehnen', 'callback_data': f'bw:{kurz}:nein'}],
        [{'text': ('≤4' if n == '4' else n), 'callback_data': f'bw:{kurz}:{n}'} for n in NOTEN]]}


def _lesen(pfad, standard):
    return json.loads(pfad.read_text(encoding='utf-8')) if pfad.exists() else standard


def _schreiben(pfad, daten):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix('.tmp')
    tmp.write_text(json.dumps(daten, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(pfad)


def video_merken(message_id, sha, skript, kritik=None):
    titel = ' '.join(z.replace('*', '') for z in skript.get('titel', []))
    liste = [v for v in _lesen(VIDEOS, []) if v.get('message_id') != message_id]
    kritik = kritik if isinstance(kritik, dict) else {}
    liste.append({'message_id': message_id, 'video_sha256': sha, 'kanal': skript.get('kanal'),
                  'thema': skript.get('thema'), 'titel': titel,
                  # Fuer das Lernen aus der Nutzernote: was die KI an genau diesem Video bemaengelte.
                  'ki_note': kritik.get('note'),
                  'ki_probleme': [f"[{p.get('art', '')}] {str(p.get('text', ''))[:200]}"
                                  for p in (kritik.get('probleme') or []) if isinstance(p, dict)][:8],
                  'datum_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    _schreiben(VIDEOS, liste[-200:])


def video_zu(message_id=None, kurz=None):
    for v in reversed(_lesen(VIDEOS, [])):
        if message_id is not None and v.get('message_id') == message_id:
            return v
        if kurz and v.get('video_sha256', '').startswith(kurz):
            return v
    return None


def _eintragen(eintrag):
    d = _lesen(REDAKTION, {})
    liste = d.get('nutzerfeedback', [])
    if any(e.get('id') == eintrag['id'] for e in liste):
        return False
    d['nutzerfeedback'] = liste + [eintrag]
    _schreiben(REDAKTION, d)
    return True


def knopf(update_id, callback):
    """Knopfdruck speichern; gibt die Bestaetigung fuer den Nutzer zurueck."""
    teile = str(callback.get('data', '')).split(':')
    if len(teile) != 3 or teile[0] != 'bw' or teile[2] not in ('ok', 'nein') + NOTEN:
        return 'Unbekannter Knopf - nichts gespeichert.'
    _, kurz, wert = teile
    video = video_zu((callback.get('message') or {}).get('message_id'), kurz) or {}
    note = int(wert) if wert.isdigit() else None
    status = 'abgelehnt' if wert == 'nein' or (note is not None and note <= 4) else \
        'gefaellt' if wert == 'ok' else 'benotet'
    titel = video.get('titel') or 'Video ' + kurz
    eintrag = {'id': f'telegram-knopf-{update_id}', 'quelle': 'telegram-knopf',
               'datum_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'kanal': video.get('kanal'), 'thema': video.get('thema'), 'titel': titel,
               'video_sha256': video.get('video_sha256'), 'video_sha256_prefix': kurz,
               'status': status, 'note': note,
               'wortlaut': f'Nutzerknopf zu „{titel}": ' + (
                   f'Note {note}/10' if note is not None else 'gefaellt' if wert == 'ok' else 'abgelehnt')}
    ki = video.get('ki_note')
    if note is not None and isinstance(ki, (int, float)) and ki - note >= 2:
        # Kalibrierung: KI deutlich milder als der Nutzer (Nintendo: KI 9, Nutzer < 5).
        eintrag['wortlaut'] += f' (KI-Bewertung war {ki}/10 - die KI war zu mild)'
    if not _eintragen(eintrag):
        return 'Bewertung war schon gespeichert.'
    import lernen
    lernen.nutzerfeedback(eintrag['wortlaut'], eintrag['id'])
    if status == 'abgelehnt' or (note is not None and note <= 7):
        aus_nutzernote_lernen(video, note, status)
    return (f'❌ Abgelehnt gespeichert: {titel}. Diese Datei wird nicht erneut gesendet. '
            'Antworte auf das Video mit einem Satz, was nicht passt.' if status == 'abgelehnt' else
            f'✅ Gespeichert: {titel} - ' + (f'Note {note}/10.' if note is not None else 'gefaellt dir.'))


def aus_nutzernote_lernen(video, note, status):
    """Eine schwache Nutzernote macht die KI-Befunde GENAU dieses Videos zu Kanal-Regeln.
    GEMESSEN 09.10.2026: Knopf-Noten landeten nur als nackter Satz „Note 6/10" im Regelbuch -
    der Autor erfuhr nie, WAS schlecht war. Ohne gespeicherte Befunde (aeltere Videos) nichts tun."""
    befunde = video.get('ki_probleme') or []
    kanal = re.sub(r'[^a-z0-9]+', '-', str(video.get('kanal') or '').lower()).strip('-')
    if not befunde or not kanal:
        return False
    urteil = 'abgelehnt' if status == 'abgelehnt' else f'{note}/10'
    try:
        import lernen
        lernen.aktualisieren(kanal, {'kategorien': {}, 'probleme': [
            {'art': 'nutzer', 'text': f'The channel owner rated this video {urteil}; these review findings '
                                      f'are therefore confirmed weaknesses: {b}'} for b in befunde]})
        return True
    except Exception as e:  # Lernen darf die Knopf-Bestaetigung nie kippen
        print('Lernen aus Nutzernote nicht moeglich:', type(e).__name__)
        return False


def antwort_auf_video(update_id, nachricht):
    """Text als Antwort auf ein geliefertes Video: Feedback mit Videobezug. None = kein Video."""
    bezug = (nachricht.get('reply_to_message') or {}).get('message_id')
    video = video_zu(bezug) if bezug is not None else None
    if not video:
        return None
    text = (nachricht.get('text') or '').strip()[:1500]
    eintrag = {'id': f'telegram-antwort-{update_id}', 'quelle': 'telegram-antwort',
               'datum_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'kanal': video.get('kanal'), 'thema': video.get('thema'), 'titel': video.get('titel'),
               'video_sha256': video.get('video_sha256'), 'status': 'kommentar',
               'wortlaut': f'Nutzerkommentar zu „{video.get("titel")}": {text}'}
    if _eintragen(eintrag):
        import lernen
        lernen.nutzerfeedback(eintrag['wortlaut'], eintrag['id'])
    return f'Danke - als Feedback zu „{video.get("titel")}" gespeichert.'
