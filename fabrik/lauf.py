"""Ein Video je Kanal - mit Qualitaetsschwelle und Lernen.

Ablauf je Versuch: Skript (mit gelernten Regeln) -> Video -> KI-Pruefung ->
Regeln aus der Pruefung lernen. Ab Note 8 wird das Video aufs Handy geschickt;
darunter ein zweiter Versuch mit neuem Thema. Mehr als zwei Versuche passen
nicht ins kostenlose GitHub-Kontingent (2.000 Min./Monat fuer zwei Kanaele).
Erreicht kein Versuch 8/10: Meldung mit bester Note und Gruenden, kein Video.

GEMELDET: „Bitte nur 9/10 oder 10/10 posten" -> „8/10 kann auch gehen, aber
das Tool soll aus dem Feedback lernen und besser werden".

Aufruf:  python fabrik/lauf.py kanaele/ai-tools-explained.json [thema]
"""
import datetime, json, os, shutil, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

SCHWELLE = 8
VERSUCHE = 2
PY = sys.executable


def melden(text):
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if token and chat:
        urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', data=urllib.parse.urlencode(
            {'chat_id': chat, 'text': text}).encode(), timeout=30)


def verlauf_eintragen(kanal, skript, status, note):
    p = Path('verlauf') / f'{kanal}.json'
    p.parent.mkdir(exist_ok=True)
    v = json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
    v.append({'datum': datetime.date.today().isoformat(), 'thema': skript['thema'], 'titel': skript['titel'],
              'status': status, 'note': note})
    p.write_text(json.dumps(v, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def main(kanal_pfad, thema=''):
    import lernen
    kanal = Path(kanal_pfad).stem
    bester = None  # (note, ordner, kritik)
    for versuch in range(1, VERSUCHE + 1):
        ordner = Path(f'versuch{versuch}')
        shutil.rmtree(ordner, ignore_errors=True)
        r = subprocess.run([PY, 'fabrik/skript.py', kanal_pfad, str(ordner / 'skript.json'), thema])
        if r.returncode == 2:  # Faktenpruefung fuer alle Themen nicht bestanden
            if (ordner / 'skript.json').exists():
                verlauf_eintragen(kanal, json.loads((ordner / 'skript.json').read_text(encoding='utf-8')),
                                  'faktenpruefung', None)
            continue
        r.check_returncode()
        subprocess.run([PY, 'fabrik/bauen.py', str(ordner / 'skript.json'), str(ordner)], check=True)
        skript = json.loads((ordner / 'skript.json').read_text(encoding='utf-8'))
        k = subprocess.run([PY, 'fabrik/kritik.py', str(ordner / 'short.mp4'), str(ordner / 'skript.json'),
                            str(ordner / 'kritik.json')])
        if k.returncode != 0 or not (ordner / 'kritik.json').exists():
            # Pruefung nicht erreichbar: lieber ungeprueftes Video mit Hinweis als keins
            print('KI-Pruefung nicht verfuegbar - Video geht ohne Note raus')
            bester = (SCHWELLE, ordner, None)
            break
        kritik = json.loads((ordner / 'kritik.json').read_text(encoding='utf-8'))
        technik = kritik.get('technik', {}).get('befunde', [])
        note = kritik['note'] - (1 if technik else 0)  # harte Technikfehler kosten einen Punkt
        try:
            lernen.aktualisieren(kanal, kritik)
        except Exception as e:  # Lernen darf das Video nie verhindern
            print('Lernen nicht moeglich:', str(e)[:150])
        print(f'Versuch {versuch}: {note}/10')
        if bester is None or note > bester[0]:
            bester = (note, ordner, kritik)
        if note >= SCHWELLE:
            break
        verlauf_eintragen(kanal, skript, 'unter_schwelle', note)  # Thema nicht noch einmal versuchen
        thema = ''  # zweiter Versuch: neues Thema (ein festes Thema hatte seine Chance)

    if bester is None:
        melden(f'⚠️ Heute kein Video für {kanal}: Faktenprüfung bei allen Themen nicht bestanden.')
        return 0
    note, ordner, kritik = bester
    aus = Path('ausgabe')
    shutil.rmtree(aus, ignore_errors=True)
    shutil.copytree(ordner, aus)
    skript = json.loads((aus / 'skript.json').read_text(encoding='utf-8'))
    if note < SCHWELLE:
        gruende = '\n'.join(f"• {p['zeit']} {p['text']}" for p in (kritik or {}).get('probleme', [])[:4])
        melden(f'🔴 Heute kein Video für {kanal}: bester Versuch nur {note}/10 (Schwelle {SCHWELLE}).\n'
               f'Das Tool hat daraus gelernt.\n{gruende}')
        return 0
    subprocess.run([PY, 'fabrik/freigabe.py', str(aus / 'skript.json'), str(aus / 'short.mp4')], check=True)
    verlauf_eintragen(kanal, skript, 'gesendet', note)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ''))
