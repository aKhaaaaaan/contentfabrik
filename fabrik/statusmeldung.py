"""Bestaetigte Telegram-Statusmeldungen; keine Video-Freigabe und keine KI-Aufrufe."""
import argparse
import json
import os
from pathlib import Path
from freigabe import telegram
from qualitaet import skript_gruende


def lesen(pfad):
    try:
        d = json.loads(Path(pfad).read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def fehlergrund(ordner='ausgabe'):
    bericht = lesen(Path(ordner) / 'bericht.json')
    skript = lesen(Path(ordner) / 'skript.json')
    if bericht.get('status') == 'pilot_bestanden':
        return 'Video-Pruefung bestanden, aber Sicherung oder Telegram-Zustellung nicht abgeschlossen.'
    gruende = []
    if bericht.get('grund'):
        gruende.append(str(bericht['grund']))
    if skript:
        pruefung = skript.get('pruefung')
        if not isinstance(pruefung, dict) or pruefung.get('ok') is not True:
            gruende.append('Faktenpruefung nicht bestanden.')
        else:
            story = skript.get('story') or {}
            if story.get('note') is not None:
                gruende.append(f"Skript/Story: {story['note']}/10; erforderlich mindestens 9/10.")
            gruende.extend(skript_gruende(skript)[:3])
    if not gruende:
        for r in reversed(bericht.get('runden', [])):
            if r.get('sperrgruende'):
                gruende.extend(str(g) for g in r['sperrgruende'][:3])
                break
    return ' '.join(dict.fromkeys(gruende))[:600] or 'Cloud-Lauf fehlgeschlagen oder abgebrochen; Details im Laufbericht.'


def text(phase, env=None):
    e = os.environ if env is None else env
    kanal = e.get('KANAL', 'Contentfabrik')[:100]
    art = 'Langvideo' if e.get('VIDEOFORMAT') == 'lang' else 'Short'
    thema = e.get('THEMA', '')[:120]
    url = e.get('CF_ORIGINAL_URL', '')
    titel = f'{kanal} · {art}' + (f' · {thema}' if thema else '')
    if phase == 'start':
        return (f'🎬 {titel}: Probelauf gestartet.\n'
                'Ich melde auch einen Fehlschlag. Ein Video kommt erst nach bestandenem Fakten-/Technikcheck '
                'und mindestens 9/10 fuer Story und Video.\n' + url)
    if phase == 'fehlgeschlagen':
        grund = e.get('GRUND') or fehlergrund()
        return f'⚠️ {titel}: Kein freigegebenes Video zugestellt.\nGrund: {grund[:600]}\n{url}'
    if phase == 'nachricht':
        return e.get('NACHRICHT', '')
    raise ValueError('Unbekannte Statusmeldung')


def senden(nachricht):
    if not nachricht.strip() or len(nachricht.encode('utf-16-le')) // 2 > 3500:
        raise ValueError('Statusnachricht leer oder zu lang')
    antwort = telegram('sendMessage', {'chat_id': os.environ['TELEGRAM_CHAT_ID'], 'text': nachricht})
    if antwort.get('ok') is not True:
        raise RuntimeError('Telegram hat die Statusmeldung nicht bestaetigt')
    print('Telegram-Statusmeldung bestaetigt; message_id:', antwort.get('result', {}).get('message_id'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['start', 'fehlgeschlagen', 'nachricht', 'grund'])
    args = parser.parse_args()
    if args.phase == 'grund':
        grund = fehlergrund().replace('\n', ' ').replace('\r', ' ')
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
                f.write('grund=' + grund + '\n')
        print(grund)
    else:
        senden(text(args.phase))
