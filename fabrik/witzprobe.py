"""Witz-Probe 31.10.2026 (Nutzer: Zeichentrick- und alte Comedy-Clips "machen das Video interessanter"): fuer
Beispielsaetze beider Kanaele die echte Clip-Suche (archivclip.fuer_einstellung, witz=True) laufen lassen und jeden
Treffer mit Satz, Film, Note und Lizenz nach Telegram schicken. Kein Video, beruehrt weder Verlauf noch Budget."""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import archivclip  # noqa: E402

SAETZE = [
    ('Business', 'Sales doubled in a single year.', 'sales money growth'),
    ('Business', 'The factory could not keep up with the orders.', 'factory workers rush'),
    ('Business', 'The bank refused to lend them a single dollar.', 'bank money loan'),
    ('Business', 'Customers lined up around the block.', 'store customers crowd'),
    ('KI', 'The machine answers your question in seconds.', 'machine thinking answer'),
    ('KI', 'You stop copy-pasting between apps.', 'office typing paper'),
    ('KI', 'The robot writes the code while you watch.', 'robot machine work'),
    ('KI', 'Your files pile up faster than you can sort them.', 'office paper pile'),
]


def telegram(pfad, text):
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not (token and chat):
        return
    api = f'https://api.telegram.org/bot{token}'
    if pfad:
        subprocess.run(['curl', '-s', '-F', f'chat_id={chat}', '-F', f'video=@{pfad}', '-F', 'supports_streaming=true',
                        '-F', f'caption={text[:1000]}', f'{api}/sendVideo'], capture_output=True, timeout=120)
    else:
        subprocess.run(['curl', '-s', '-d', f'chat_id={chat}', '--data-urlencode', f'text={text[:3500]}',
                        f'{api}/sendMessage'], capture_output=True, timeout=60)


def main(ordner='probe'):
    aus = Path(ordner)
    aus.mkdir(exist_ok=True)
    benutzt, ergebnis = set(), []
    for n, (kanal, satz, suche) in enumerate(SAETZE):
        try:
            video, _, quelle = archivclip.fuer_einstellung(satz, '', suche, 3.0, aus / f'witz_{n}', archiv=False,
                                                          benutzt=benutzt, witz=True)
        except Exception as e:  # eine Probe darf nicht die anderen kippen
            print(n, 'Fehler:', type(e).__name__, str(e)[:120])
            video, quelle = None, None
        ergebnis.append({'kanal': kanal, 'satz': satz, 'video': str(video) if video else None, 'quelle': quelle})
        if video:
            telegram(video, f'Witz-Probe {kanal}: "{satz}"\n{quelle.get("seite")}\nNote {quelle.get("note")}/10, '
                            f'{quelle.get("lizenz")}')
    (aus / 'ergebnis.json').write_text(json.dumps(ergebnis, indent=1, ensure_ascii=False), encoding='utf-8')
    treffer = sum(1 for e in ergebnis if e['video'])
    ohne = [f"{e['kanal']}: {e['satz']}" for e in ergebnis if not e['video']]
    telegram(None, f'Witz-Probe fertig: {treffer} von {len(SAETZE)} Saetzen mit Clip.'
             + ('\nOhne passenden Clip (bliebe gemalt):\n- ' + '\n- '.join(ohne) if ohne else ''))
    print(json.dumps(ergebnis, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main(*sys.argv[1:])
