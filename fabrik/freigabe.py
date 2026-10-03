"""Schickt ein fertiges Video zur Freigabe aufs Handy (Telegram).

Bis Google das Projekt geprueft hat, bleibt jeder API-Upload fuer immer privat
(GEPRUEFT 02.10.2026, videos.insert-Doku). Darum vorerst: Video + Texte aufs
Handy, der Nutzer laedt es mit der YouTube-/TikTok-App selbst hoch.

Aufruf:  python fabrik/freigabe.py ausgabe/skript.json ausgabe/short.mp4
Umgebung: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
import json, os, sys, uuid, urllib.request, urllib.error
from pathlib import Path

GRENZE = 50 * 1024 * 1024  # Telegram-Bots duerfen hoechstens 50 MB senden


def telegram(methode, felder, datei=None):
    token = os.environ['TELEGRAM_BOT_TOKEN']
    grenze = uuid.uuid4().hex
    teile = []
    for k, v in felder.items():
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    if datei:
        name, inhalt = datei
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="video"; filename="{name}"\r\n'
                     'Content-Type: video/mp4\r\n\r\n'.encode() + inhalt + b'\r\n')
    teile.append(f'--{grenze}--\r\n'.encode())
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/{methode}', data=b''.join(teile),
                                 headers={'Content-Type': f'multipart/form-data; boundary={grenze}'})
    try:
        return json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        sys.exit(f'Telegram lehnt ab ({e.code}): {e.read().decode(errors="replace")[:300].replace(token, "***")}')


def planungszeit(uhrzeit_ny, jetzt=None):
    """Naechster Termin zur festen New-Yorker Uhrzeit, in Berliner Zeit.
    Unsere Kanaele sind englisch, das Publikum sitzt vor allem in den USA -
    der Nutzer laedt morgens hoch und PLANT die Veroeffentlichung, statt
    nachts wach zu sein. Sommer-/Winterzeit rechnet zoneinfo (beide Laender
    stellen an verschiedenen Tagen um)."""
    import datetime
    try:
        from zoneinfo import ZoneInfo
        ny, berlin = ZoneInfo('America/New_York'), ZoneInfo('Europe/Berlin')
    except Exception:
        return ''
    jetzt = jetzt or datetime.datetime.now(ny)
    h, m = map(int, uhrzeit_ny.split(':'))
    termin = jetzt.astimezone(ny).replace(hour=h, minute=m, second=0, microsecond=0)
    if termin <= jetzt + datetime.timedelta(minutes=30):  # Zeit zum Hochladen lassen
        termin += datetime.timedelta(days=1)
    b = termin.astimezone(berlin)
    tage = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
    return f"{tage[b.weekday()]} {b:%d.%m.} {b:%H:%M} Uhr Berlin (= {termin:%H:%M} New York)"


def senden(skript_pfad, video_pfad):
    skript = json.loads(Path(skript_pfad).read_text(encoding='utf-8'))
    video = Path(video_pfad).read_bytes()
    if len(video) > GRENZE:
        sys.exit(f'Video zu gross fuer Telegram ({len(video) // 2**20} MB > 50 MB)')
    titel = ' '.join(z.replace('*', '') for z in skript['titel'])
    tags = ' '.join('#' + h.lstrip('#') for h in skript.get('hashtags', []))
    chat = os.environ['TELEGRAM_CHAT_ID']
    # 1. Das Video selbst - kurze Bildunterschrift, damit es gut lesbar bleibt
    telegram('sendVideo', {'chat_id': chat, 'supports_streaming': 'true',
                           'caption': f"🎬 {skript['kanal']}\n{titel}\n\nPrüfung: "
                                      f"{'✅ bestanden' if skript.get('pruefung', {}).get('ok') else '⚠️ offen'}"},
             (Path(video_pfad).name, video))
    # 2. Die Texte einzeln - antippen kopiert sie (Monospace-Format in Telegram)
    def code(t):
        return '<code>' + t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') + '</code>'
    zeit = planungszeit(skript.get('posten_ny', '15:00'))
    text = ((f'⏰ <b>Planen für: {zeit}</b>\n\n' if zeit else '')
            + '<b>Zum Hochladen (antippen = kopieren):</b>\n\nTitel:\n' + code(f'{titel} #shorts')
            + '\n\nBeschreibung:\n' + code(f"{skript['beschreibung']}\n\n{tags}")
            + '\n\n<i>In der App „Veränderte oder synthetische Inhalte“ auf „Ja“ stellen (KI-Stimme).</i>')
    antwort = telegram('sendMessage', {'chat_id': chat, 'parse_mode': 'HTML', 'text': text})
    print('Gesendet:', antwort.get('ok'))


if __name__ == '__main__':
    senden(sys.argv[1], sys.argv[2])
