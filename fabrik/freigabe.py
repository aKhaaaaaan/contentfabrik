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


def verkleinern(video_pfad):
    import subprocess, tempfile
    dauer = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                  video_pfad], capture_output=True, text=True, check=True).stdout)
    ziel_bit = int(46 * 8 * 1024 * 1024 / dauer) - 160_000  # 46 MB Ziel, Platz fuer den Ton
    aus = Path(tempfile.gettempdir()) / 'telegram.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', video_pfad, '-c:v', 'libx264', '-preset', 'medium',
                    '-b:v', str(ziel_bit), '-maxrate', str(int(ziel_bit * 1.3)), '-bufsize', str(ziel_bit * 2),
                    '-c:a', 'copy', '-movflags', '+faststart', str(aus)], check=True)
    print(f'Fuer Telegram verkleinert: {len(Path(video_pfad).read_bytes()) // 2**20} MB -> '
          f'{aus.stat().st_size // 2**20} MB ({ziel_bit // 1000} kbit/s)')
    return aus.read_bytes()


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
    if len(video) > GRENZE * 0.98:
        # GEMESSEN: 121-s-Video = 56 MB, Telegram-Bots duerfen hoechstens 50 MB
        # senden -> der Nutzer bekam „Lauf abgebrochen" statt des Videos.
        # Kopie mit passender Bitrate, gleiche Aufloesung, Ton unveraendert.
        video = verkleinern(video_pfad)
        if len(video) > GRENZE:
            sys.exit(f'Video auch verkleinert zu gross ({len(video) // 2**20} MB > 50 MB)')
    titel = ' '.join(z.replace('*', '') for z in skript['titel'])
    tags = ' '.join('#' + h.lstrip('#') for h in skript.get('hashtags', []))
    # CC-Lizenzen verlangen Urheber, Lizenz und Quelle - automatisch anhaengen
    qpfad = Path(skript_pfad).with_name('quellen.json')
    fotos = [q for q in (json.loads(qpfad.read_text(encoding='utf-8')) if qpfad.exists() else [])
             if q.get('quelle') == 'Wikimedia Commons']
    musik = [q for q in (json.loads(qpfad.read_text(encoding='utf-8')) if qpfad.exists() else [])
             if q.get('quelle') == 'Musik']
    if musik:
        skript['beschreibung'] += '\n' + musik[0]['nennung']
    if fotos:
        skript['beschreibung'] += '\nPhotos (Wikimedia Commons): ' + '; '.join(
            f"{q['von']}, {q['lizenz']} ({q['seite']})" for q in fotos)
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
    kritik_pfad = Path(skript_pfad).with_name('kritik.json')
    kritik = json.loads(kritik_pfad.read_text(encoding='utf-8')) if kritik_pfad.exists() else None
    def esc(t):
        return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    pruef = ''
    if kritik:
        note = kritik['note']
        pruef = (f"{'🟢' if note >= 8 else '🟡' if note >= 6 else '🔴'} <b>KI-Prüfung: {note}/10</b> – "
                 f"{esc(kritik['fazit'])}\n"
                 + ''.join(f"• {esc(p['zeit'])} {esc(p['text'])}\n" for p in kritik['probleme'][:5])
                 + ''.join(f'• ⚙️ {esc(b)}\n' for b in kritik.get('technik', {}).get('befunde', []))
                 + '\n')
    story = skript.get('story')
    if story:
        pruef = f"📖 <b>Story: {story['note']}/10</b>\n" + pruef
    text = (pruef + (f'⏰ <b>Planen für: {zeit}</b>\n\n' if zeit else '')
            + '<b>Zum Hochladen (antippen = kopieren):</b>\n\nTitel:\n' + code(f'{titel} #shorts')
            + '\n\nBeschreibung:\n' + code(f"{skript['beschreibung']}\n\n{tags}")
            + '\n\n<i>In der App „Veränderte oder synthetische Inhalte“ auf „Ja“ stellen (KI-Stimme).</i>')
    antwort = telegram('sendMessage', {'chat_id': chat, 'parse_mode': 'HTML', 'text': text})
    # 3. TikTok von Hand - eigene Nachricht, damit die Texte nicht an Telegrams
    # 4096-Zeichen-Grenze stossen. GEMESSEN 03.10.2026: Ein neues Konto wurde
    # nach API-Uploads einer ungeprueften App gesperrt („Spam und irrefuehrendes
    # Kontoverhalten"), Hand-Uploads im zweiten Konto gehen. Bis zur TikTok-
    # Pruefung laedt der Nutzer darum selbst hoch. CC BY verlangt die Nennung
    # auch auf TikTok - Musik/Fotos stehen deshalb mit im Text.
    nennung = '\n'.join(z for z in skript['beschreibung'].split('\n') if z.startswith(('Music:', 'Photos')))
    tiktok = f'{titel} {tags}' + (f'\n\n{nennung}' if nennung else '')
    telegram('sendMessage', {'chat_id': chat, 'parse_mode': 'HTML', 'text':
             '📱 <b>TikTok</b> (Text antippen = kopieren):\n\n' + code(tiktok[:2200])
             + '\n\n<i>Beim Posten „Weitere Optionen“ → „KI-generierte Inhalte“ einschalten.</i>'})
    print('Gesendet:', antwort.get('ok'))


if __name__ == '__main__':
    senden(sys.argv[1], sys.argv[2])
