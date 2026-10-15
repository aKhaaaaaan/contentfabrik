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


def telegram(methode, felder, datei=None, feld='video', typ='video/mp4'):
    token = os.environ['TELEGRAM_BOT_TOKEN']
    grenze = uuid.uuid4().hex
    teile = []
    for k, v in felder.items():
        # GEMESSEN 09.10.2026 (Pilot 37840254844): ein dict (link_preview_options) wurde als
        # Python-Text {'is_disabled': True} gesendet -> Telegram lehnte ab, Lauf brach ab.
        if isinstance(v, (dict, list, bool)):
            v = json.dumps(v)
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    if datei:
        name, inhalt = datei
        teile.append(f'--{grenze}\r\nContent-Disposition: form-data; name="{feld}"; filename="{name}"\r\n'
                     f'Content-Type: {typ}\r\n\r\n'.encode() + inhalt + b'\r\n')
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


def vorschaubild_senden(chat, pfad, variante='A'):
    """Langvideo: Vorschaubild als DATEI (volle Qualitaet, 1280x720) - Telegram-Fotos werden
    verkleinert. Darf den bereits gelieferten Versand nie kippen."""
    if not pfad.exists():
        return False
    try:
        # Drei Varianten fuer YouTube Studio „Test & Compare" (bis zu 3, kostenlos, gewinnt nach Wiedergabezeit)
        telegram('sendDocument', {'chat_id': chat, 'caption': f'Vorschaubild {variante} fuer YouTube (1280x720). '
                                  'A als Thumbnail einsetzen; A, B und C unter „Test & Compare" testen.'},
                 (pfad.name, pfad.read_bytes()), feld='document', typ='image/jpeg')
        return True
    except (RuntimeError, OSError) as e:
        print('Vorschaubild nicht gesendet:', str(e)[:120])
        return False


def senden(skript_pfad, video_pfad):
    skript = json.loads(Path(skript_pfad).read_text(encoding='utf-8'))
    kritik_pfad = Path(skript_pfad).with_name('kritik.json')
    kritik = json.loads(kritik_pfad.read_text(encoding='utf-8')) if kritik_pfad.exists() else None
    note, gruende = bewerten(skript, kritik)
    from qualitaet import ENTWURF_MIN, nur_ki_geschmack, nur_bildbezug
    # Entwurf (Nutzerentscheidung 08.10.2026): nur wenn AUSSCHLIESSLICH KI-Geschmacksnoten
    # sperren und die Note >= ENTWURF_MIN ist. Fakten/Technik/Endton bleiben harte Sperren.
    entwurf = bool(gruende) and os.environ.get('CF_ENTWURF') == '1' \
        and nur_ki_geschmack(gruende) and (note or 0) >= ENTWURF_MIN
    # Nutzerentscheidung 15.10.2026: nur an Bildbezug gescheitert -> markierter Entwurf, Nutzer entscheidet.
    bildentwurf = bool(gruende) and os.environ.get('CF_ENTWURF') == '1' and nur_bildbezug(gruende)
    entwurf = entwurf or bildentwurf
    bild_nummern = ', '.join(g.split(':')[0].replace('Einstellung ', '') for g in gruende
                             if g.startswith('Einstellung '))
    if gruende and not entwurf:
        raise ValueError('Video bleibt gesperrt: ' + '; '.join(gruende))
    video = Path(video_pfad).read_bytes()
    import lernen
    import hashlib
    sha = hashlib.sha256(video).hexdigest()
    if kritik.get('video_sha256') != sha:
        raise ValueError('Videodatei wurde seit der Kritik/Endton-Pruefung geaendert; erneut pruefen')
    if lernen.abgelehnt(sha):
        raise ValueError('Dieses Video wurde vom Nutzer abgelehnt; kein erneuter Versand')
    komprimiert = False
    if len(video) > GRENZE * 0.98:
        # GEMESSEN: 121-s-Video = 56 MB, Telegram-Bots duerfen hoechstens 50 MB
        # senden -> der Nutzer bekam „Lauf abgebrochen" statt des Videos.
        # Kopie mit passender Bitrate, gleiche Aufloesung, Ton unveraendert.
        video = verkleinern(video_pfad)
        komprimiert = True
        if len(video) > GRENZE:
            sys.exit(f'Video auch verkleinert zu gross ({len(video) // 2**20} MB > 50 MB)')
    import texte
    titel = texte.upload_titel(skript)
    lang = videoformat(skript) == 'lang'
    tags = ' '.join('#' + h.lstrip('#') for h in skript.get('hashtags', []))
    # CC-Lizenzen verlangen Urheber, Lizenz und Quelle - automatisch anhaengen
    qpfad = Path(skript_pfad).with_name('quellen.json')
    quellen = json.loads(qpfad.read_text(encoding='utf-8')) if qpfad.exists() else []
    skript['beschreibung'] = texte.beschreibung_mit_quellen(skript['beschreibung'], quellen)
    chat = os.environ['TELEGRAM_CHAT_ID']
    try:
        ersatz = json.loads(Path(video_pfad).with_name('messung.json').read_text(encoding='utf-8')).get('stimme_ersatz')
    except (OSError, ValueError):
        ersatz = False
    # 1. Das Video selbst - kurze Bildunterschrift, damit es gut lesbar bleibt
    import bewertung
    import kanalstandard
    profil = kanalstandard.nach_name(skript.get('kanal')) or {}
    tik_config = profil.get('tiktok_entwurf') or {}
    tik_freigabe = not lang and tik_config.get('aktiv') is True and tik_config.get('freigabe') == 'telegram'
    import re
    upload_run = re.search(r'/actions/runs/(\d+)', os.environ.get('CF_ORIGINAL_URL', ''))
    upload_run = upload_run.group(1) if upload_run else os.environ.get('GITHUB_RUN_ID')
    tik_freigabe = tik_freigabe and bool(upload_run)
    video_antwort = telegram('sendVideo', {'chat_id': chat, 'supports_streaming': 'true',
                           'reply_markup': json.dumps(bewertung.knoepfe(sha, tiktok=tik_freigabe)),
                           'caption': (f"⚠️ ENTWURF - Bildpruefung NICHT bestanden: Bilder {bild_nummern} passen "
                                       f"nicht genau zum Satz. Fakten, Technik und Ton bestanden. Du entscheidest.\n\n"
                                       if bildentwurf else
                                       f"⚠️ ENTWURF - KI-Note {note}/10, nicht freigegeben. Du entscheidest.\n"
                                       f"KI-Kritik: {str((kritik or {}).get('fazit', ''))[:300]}\n\n" if entwurf else '')
                                      + ("⚠️ ERSATZSTIMME Kokoro - Orus war nicht verfuegbar (Kontingent/Limit?). "
                                         "Lieber nicht hochladen.\n\n" if ersatz else '')
                                      + f"🎬 {skript['kanal'][:100]}\n{titel[:200]}\n\n"
                                      f"✅ Fakten und Technik bestanden · KI-Bewertung "
                                      f"{f'{note}/10' if note is not None else 'nicht durchgefuehrt'}\n"
                                      "Bewerte unten: 📖 Story · 🎬 Video. Antworte auf dieses Video mit Kritik."
                                      + ('\nZum Upload auf „✅ TikTok-Entwurf hochladen“ tippen. '
                                         'Story-/Videonoten geben keinen Upload frei.' if tik_freigabe else '')
                                      + (f"\n📈 Warum heute: {os.environ['CF_TRENDGRUND'][:300]}"
                                         if os.environ.get('CF_TRENDGRUND') else '')
                                      + ('\nKomprimierte Vorschau; Original siehe Begleitnachricht.'
                                         if komprimiert and os.environ.get('CF_ORIGINAL_URL') else
                                         '\nFuer Telegram komprimierte Kopie.' if komprimiert else '')},
             (Path(video_pfad).name, video))
    message_id = video_antwort.get('result', {}).get('message_id')
    print('Telegram-Video bestaetigt; message_id:', message_id)
    if message_id is not None:
        try:  # Zuordnung fuer Knoepfe/Antworten; darf den gelieferten Versand nicht kippen
            bewertung.video_merken(message_id, sha, skript, kritik, upload_run_id=upload_run)
        except (OSError, ValueError) as e:
            print('Video-Zuordnung fuer Bewertung nicht gespeichert:', str(e)[:120])
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
        basis = Path(skript_pfad).with_name('thumbnail.jpg')
        for v, pfad in zip('ABC', [basis, basis.with_name('thumbnail_b.jpg'), basis.with_name('thumbnail_c.jpg')]):
            vorschaubild_senden(chat, pfad, v)
        print('Gesendet:', antwort.get('ok'))
        return
    # Video-Inbox kann keine Caption annehmen. Text trotzdem automatisch erzeugen;
    # Telegram und spaeter Direct Post verwenden dieselbe Quelle inklusive Nennungen.
    tiktok = texte.tiktok_text(skript)
    Path(skript_pfad).with_name('tiktok-text.txt').write_text(tiktok, encoding='utf-8')
    if texte.tiktok_laenge(tiktok) > 2200:
        telegram('sendMessage', {'chat_id': chat, 'text':
                 '📱 TikTok-Text ist laenger als 2.200 Zeichen. Titel/Hashtags vor dem Posten kuerzen; '
                 'Quellen- und Lizenzangaben vollstaendig erhalten. KI-generierte Inhalte einschalten.'})
    kopieren_senden(chat, 'TikTok (KI-generierte Inhalte einschalten)', tiktok)
    print('Gesendet:', antwort.get('ok'))


if __name__ == '__main__':
    senden(sys.argv[1], sys.argv[2])
