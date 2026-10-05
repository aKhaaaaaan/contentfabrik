"""Schickt ein fertiges Video zur Freigabe aufs Handy (Telegram).

Bis Google das Projekt geprueft hat, bleibt jeder API-Upload fuer immer privat
(GEPRUEFT 02.10.2026, videos.insert-Doku). Darum vorerst: Video + Texte aufs
Handy, der Nutzer laedt es mit der YouTube-/TikTok-App selbst hoch.

Aufruf:  python fabrik/freigabe.py ausgabe/skript.json ausgabe/short.mp4
Umgebung: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""
import json, os, sys, uuid, urllib.request, urllib.error
from pathlib import Path
from qualitaet import bewerten
from dramaturgie import videoformat

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
        with urllib.request.urlopen(req, timeout=300) as r:
            antwort = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Telegram lehnt ab ({e.code}): '
                           + e.read().decode(errors='replace')[:300].replace(token, '***')) from None
    if antwort.get('ok') is not True:
        raise RuntimeError('Telegram hat die Zustellung nicht bestaetigt')
    return antwort


def esc(text):
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def kopiertexte(text, grenze=3500):
    """HTML-Nachrichten aufteilen, ohne Entitaeten oder Text abzuschneiden.

    Vorsichtshalber auch UTF-16-Laenge des escapten Textes begrenzen.
    Telegram bekommt damit vollstaendige Quellen-/Lizenzangaben.
    """
    teil, laenge = [], 0
    for zeichen in text:
        escaped = esc(zeichen)
        n = len(escaped.encode('utf-16-le')) // 2
        if teil and laenge + n > grenze:
            yield '<code>' + ''.join(teil) + '</code>'
            teil, laenge = [], 0
        teil.append(escaped)
        laenge += n
    if teil:
        yield '<code>' + ''.join(teil) + '</code>'


def kopieren_senden(chat, titel, text):
    for nr, teil in enumerate(kopiertexte(text), 1):
        telegram('sendMessage', {'chat_id': chat, 'parse_mode': 'HTML',
                                 'text': f'<b>{esc(titel)} (Teil {nr}):</b>\n' + teil})


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
    kritik_pfad = Path(skript_pfad).with_name('kritik.json')
    kritik = json.loads(kritik_pfad.read_text(encoding='utf-8')) if kritik_pfad.exists() else None
    note, gruende = bewerten(skript, kritik)
    if gruende:
        raise ValueError('Video bleibt gesperrt: ' + '; '.join(gruende))
    video = Path(video_pfad).read_bytes()
    komprimiert = False
    if len(video) > GRENZE * 0.98:
        # GEMESSEN: 121-s-Video = 56 MB, Telegram-Bots duerfen hoechstens 50 MB
        # senden -> der Nutzer bekam „Lauf abgebrochen" statt des Videos.
        # Kopie mit passender Bitrate, gleiche Aufloesung, Ton unveraendert.
        video = verkleinern(video_pfad)
        komprimiert = True
        if len(video) > GRENZE:
            sys.exit(f'Video auch verkleinert zu gross ({len(video) // 2**20} MB > 50 MB)')
    titel = ' '.join(z.replace('*', '') for z in skript['titel'])
    lang = videoformat(skript) == 'lang'
    tags = ' '.join('#' + h.lstrip('#') for h in skript.get('hashtags', []))
    # CC-Lizenzen verlangen Urheber, Lizenz und Quelle - automatisch anhaengen
    qpfad = Path(skript_pfad).with_name('quellen.json')
    quellen = json.loads(qpfad.read_text(encoding='utf-8')) if qpfad.exists() else []
    fotos = [q for q in quellen if q.get('quelle') == 'Wikimedia Commons']
    musik = [q for q in quellen if q.get('quelle') == 'Musik']
    if musik:
        skript['beschreibung'] += '\n' + musik[0]['nennung']
    if any(q.get('quelle') == 'Illustration' for q in quellen):
        skript['beschreibung'] += '\nIllustrations are AI-generated.'
    if fotos:
        skript['beschreibung'] += '\nPhotos (Wikimedia Commons): ' + '; '.join(
            f"{q['von']}, {q['lizenz']} ({q['seite']})" for q in fotos)
        # CC BY verlangt den Hinweis, DASS geaendert wurde; BY-SA verlangt, die
        # geaenderte Fassung des FOTOS unter BY-SA zu stellen. Ob ein Foto im
        # Video das ganze Video zur Bearbeitung macht, ist offen (CC-FAQ und
        # Commons-Hilfe lassen es offen, GEPRUEFT 03.10.2026) - wir erfuellen
        # die Pflichten fuer das Foto selbst; Verbot haette die Haelfte der
        # passenden Firmenfotos gekostet (GEMESSEN: 56 von 102 bei 8 Firmen).
        skript['beschreibung'] += ' - cropped, animated and captioned' + (
            '; these modified photos are licensed under the same CC BY-SA license'
            if any('SA' in q['lizenz'] for q in fotos) else '')
    chat = os.environ['TELEGRAM_CHAT_ID']
    # 1. Das Video selbst - kurze Bildunterschrift, damit es gut lesbar bleibt
    telegram('sendVideo', {'chat_id': chat, 'supports_streaming': 'true',
                           'caption': f"🎬 {skript['kanal'][:100]}\n{titel[:200]}\n\n"
                                      f"✅ Fakten und Technik bestanden · Original {note}/10"
                                      + ('\nKomprimierte Vorschau; Original siehe Begleitnachricht.'
                                         if komprimiert and os.environ.get('CF_ORIGINAL_URL') else
                                         '\nFuer Telegram komprimierte Kopie.' if komprimiert else '')},
             (Path(video_pfad).name, video))
    # 2. Die Texte einzeln - antippen kopiert sie (Monospace-Format in Telegram)
    zeit = planungszeit(skript.get('posten_ny', '15:00'))
    pruef = ''
    if kritik:
        pruef = (f"🟢 <b>KI-Prüfung: {note}/10</b> – "
                 f"{esc(kritik.get('fazit', '')[:200])}\n"
                 + ''.join(f"• {esc(p.get('zeit', '')[:10])} {esc(p.get('text', '')[:120])}\n"
                           for p in kritik.get('probleme', [])[:5])
                 + '\n')
    story = skript.get('story')
    if story:
        pruef = f"📖 <b>Story: {story['note']}/10</b>\n" + pruef
    text = (pruef + (f'⏰ <b>Planen für: {zeit}</b>\n\n' if zeit else '')
            + '<i>In der App „Veränderte oder synthetische Inhalte“ auf „Ja“ stellen (KI-Stimme).</i>')
    antwort = telegram('sendMessage', {'chat_id': chat, 'parse_mode': 'HTML', 'text': text})
    original = os.environ.get('CF_ORIGINAL_URL', '')
    if original:
        telegram('sendMessage', {'chat_id': chat, 'text':
                 'Original in voller Qualitaet, Skript und Pruefbericht im privaten GitHub-Artefakt '
                 '(GitHub-Anmeldung erforderlich):\n' + original})
    kopieren_senden(chat, 'Skript', '\n\n'.join(t['text'] for t in skript['teile']))
    kopieren_senden(chat, 'YouTube-Titel', titel if lang else f'{titel} #shorts')
    kopieren_senden(chat, 'YouTube-Beschreibung', f"{skript['beschreibung']}\n\n{tags}")
    if lang:
        print('Gesendet:', antwort.get('ok'))
        return
    # 3. TikTok von Hand - eigene Nachricht, damit die Texte nicht an Telegrams
    # 4096-Zeichen-Grenze stossen. GEMESSEN 03.10.2026: Ein neues Konto wurde
    # nach API-Uploads einer ungeprueften App gesperrt („Spam und irrefuehrendes
    # Kontoverhalten"), Hand-Uploads im zweiten Konto gehen. Bis zur TikTok-
    # Pruefung laedt der Nutzer darum selbst hoch. CC BY verlangt die Nennung
    # auch auf TikTok - Musik/Fotos stehen deshalb mit im Text.
    nennung = '\n'.join(z for z in skript['beschreibung'].split('\n') if z.startswith(('Music:', 'Photos')))
    tiktok = f'{titel} {tags}' + (f'\n\n{nennung}' if nennung else '')
    if len(tiktok) > 2200:
        telegram('sendMessage', {'chat_id': chat, 'text':
                 '📱 TikTok-Text ist laenger als 2.200 Zeichen. Titel/Hashtags vor dem Posten kuerzen; '
                 'Quellen- und Lizenzangaben vollstaendig erhalten. KI-generierte Inhalte einschalten.'})
    kopieren_senden(chat, 'TikTok (KI-generierte Inhalte einschalten)', tiktok)
    print('Gesendet:', antwort.get('ok'))


if __name__ == '__main__':
    senden(sys.argv[1], sys.argv[2])
