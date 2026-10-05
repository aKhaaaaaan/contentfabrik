"""Ein Video je Kanal - mit Qualitaetsschwelle und Lernen.

Ablauf je Versuch: Skript (mit gelernten Regeln) -> Video -> KI-Pruefung ->
Regeln aus der Pruefung lernen. Ab Note 8 wird das Video aufs Handy geschickt;
darunter neue Versuche (GEMELDET: „solange bis wir 8/10 oder drueber haben"),
jeder mit den frisch gelernten Regeln und den Problemen des Vorversuchs.
Grenze ist ein Zeitbudget je Kanal und Tag: Ohne Grenze koennte ein schwerer
Tag das Gratis-Kontingent (2.000 Min./Monat) aufbrauchen - dann stoppt GitHub
alle Laeufe bis Monatsende und es gaebe GAR KEINE Videos mehr.
Ist das Budget erreicht: das BESTE Video trotzdem, mit Note und Gruenden
(taeglicher Beitrag ist fuer die Kanaele Pflicht). Kein Video nur, wenn die
Faktenpruefung bei allen Themen scheitert - Falschaussagen gehen nie raus.

GEMELDET: „Bitte nur 9/10 oder 10/10 posten" -> „8/10 kann auch gehen, aber
das Tool soll aus dem Feedback lernen und besser werden".

Aufruf:  python fabrik/lauf.py kanaele/ai-tools-explained.json [thema]
"""
import datetime, json, os, re, shutil, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

# GEMELDET: „Das Ziel ist immer 10/10, nicht bis 8/10." Verbessert wird bis
# 10 oder bis das Zeitbudget erreicht ist; unter 8 gibt es zusaetzlich eine Warnung.
ZIEL = 10
SCHWELLE = 8
# 2.000 Gratis-Minuten / 30 Tage / 2 Kanaele = ~33 Min. je Kanal und Tag
BUDGET_S = 30 * 60      # Zeitbudget je Kanal und Tag
VERSUCH_S = 25 * 60     # gemessen: ~12 Min. Bau + bis zu 15 Min. Skript mit Story-Pruefung
VERSUCHE_MAX = 5
PY = sys.executable


def melden(text):
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if token and chat:
        urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', data=urllib.parse.urlencode(
            {'chat_id': chat, 'text': text}).encode(), timeout=30)


def verlauf_eintragen(kanal, skript, status, note, abschnitte=None):
    p = Path('verlauf') / f'{kanal}.json'
    p.parent.mkdir(exist_ok=True)
    v = json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
    # Wird ein zuerst verworfener Versuch doch gesendet: nur EIN Eintrag je Thema und Tag
    heute = datetime.date.today().isoformat()
    v = [e for e in v if not (e.get('datum') == heute and e.get('thema') == skript['thema'])]
    # GEMELDET: aus erfolgreichen Videos Stimmen, Einstellungen UND Story-Aufbau
    # lernen - darum alles festhalten, was ein Video ausmacht (erfolg.py wertet aus).
    teile = skript.get('teile', [])
    erster = (teile[0]['text'] if teile else '').split('. ')[0]
    art = ('frage' if erster.rstrip().endswith('?') else 'zahl' if re.search(r'\d', erster)
           else 'widerspruch' if re.search(r'\b(but|yet|never|only|nobody|without)\b', erster, re.I) else 'aussage')
    worte = sum(len(t['text'].split()) for t in teile)
    story = skript.get('story') or {}
    v.append({'datum': datetime.date.today().isoformat(), 'thema': skript['thema'], 'titel': skript['titel'],
              'status': status, 'note': note, 'hook': erster,
              'einstellungen': {'stimme': skript.get('stimme'), 'winkel': skript.get('winkel'),
                                'format': skript.get('format'), 'hook_art': art, 'teile': len(teile),
                                'laenge': 'kurz' if worte < 190 else 'mittel' if worte < 240 else 'lang',
                                'story_note': story.get('note')},
              'gliederung': [' '.join(t['text'].split()[:7]) for t in teile],
              'abschnitte_s': abschnitte})
    p.write_text(json.dumps(v, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def main(kanal_pfad, thema=''):
    import lernen, themen
    kanal = Path(kanal_pfad).stem
    # Thema aus Telegram hat Vorrang (GEMELDET: eigene Themen einbringen)
    if not thema:
        thema = themen.nehmen(kanal)
        if thema:
            print(f'Thema aus Telegram: {thema}')
    bester = None  # (note, ordner, kritik)
    start = time.time()
    versuch = 0
    # Neuer Versuch nur, wenn er noch sicher ins Zeitbudget passt
    while versuch < VERSUCHE_MAX and (versuch == 0 or time.time() - start + VERSUCH_S <= BUDGET_S):
        versuch += 1
        ordner = Path(f'versuch{versuch}')
        shutil.rmtree(ordner, ignore_errors=True)
        r = subprocess.run([PY, 'fabrik/skript.py', kanal_pfad, str(ordner / 'skript.json'), thema])
        if r.returncode == 2:  # Faktenpruefung fuer alle Themen nicht bestanden
            if (ordner / 'skript.json').exists():
                verlauf_eintragen(kanal, json.loads((ordner / 'skript.json').read_text(encoding='utf-8')),
                                  'faktenpruefung', None)
            continue
        # GEMESSEN 04.10.2026: Ein Absturz im Skript (statt Code 2) kippte den ganzen Lauf -
        # kein Video an diesem Tag. Jeder Fehler zaehlt jetzt nur als ein verbrauchter Versuch.
        if r.returncode != 0:
            print(f'Versuch {versuch}: Skript fehlgeschlagen (Code {r.returncode}) - naechster Versuch')
            continue
        b = subprocess.run([PY, 'fabrik/bauen.py', str(ordner / 'skript.json'), str(ordner)])
        if b.returncode != 0:
            print(f'Versuch {versuch}: Videobau fehlgeschlagen - naechster Versuch')
            continue
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
            story = skript.get('story') or {}
            lern = dict(kritik)
            lern['probleme'] = kritik.get('probleme', []) + [{'zeit': '-', 'art': 'story', 'text': w}
                                                             for w in story.get('schwaechen', [])]
            lernen.aktualisieren(kanal, lern)
        except Exception as e:  # Lernen darf das Video nie verhindern
            print('Lernen nicht moeglich:', str(e)[:150])
        print(f'Versuch {versuch}: {note}/10')
        if bester is None or note > bester[0]:
            bester = (note, ordner, kritik)
        if note >= ZIEL:
            break
        verlauf_eintragen(kanal, skript, 'unter_schwelle', note)  # Thema nicht noch einmal versuchen
        thema = ''  # naechster Versuch: neues Thema, mit den eben gelernten Regeln
        print(f'Unter {ZIEL}/10 - neuer Versuch ({(time.time() - start) / 60:.0f} von '
              f'{BUDGET_S // 60} Min. verbraucht)')

    if bester is None:
        melden(f'⚠️ Heute kein Video für {kanal}: Faktenprüfung bei allen Themen nicht bestanden.')
        return 0
    note, ordner, kritik = bester
    aus = Path('ausgabe')
    shutil.rmtree(aus, ignore_errors=True)
    shutil.copytree(ordner, aus)
    skript = json.loads((aus / 'skript.json').read_text(encoding='utf-8'))
    # GEMELDET 05.10.2026: „Bitte keine schlechten Videos unter 8/10." (Vorher kam das
    # beste Video auch darunter - ein 3/10-Flop landete auf Telegram.) Unter 8 wird nichts
    # verschickt; Status 'unter_ziel' -> das naechste Zeitfenster am selben Tag versucht
    # den Kanal erneut (Vorpruefung zaehlt nur 'gesendet'). Gelernt wurde aus jeder Pruefung.
    if note < SCHWELLE:
        verlauf_eintragen(kanal, skript, 'unter_ziel', note)
        melden(f'🔁 {kanal}: bestes Video heute erst {note}/10 (Ziel {SCHWELLE}+) - nicht verschickt. '
               'Das Tool hat aus den Prüfungen gelernt und versucht es im nächsten Zeitfenster neu.')
        return 0
    subprocess.run([PY, 'fabrik/freigabe.py', str(aus / 'skript.json'), str(aus / 'short.mp4')], check=True)
    messung = json.loads((aus / 'messung.json').read_text(encoding='utf-8')) \
        if (aus / 'messung.json').exists() else {}
    verlauf_eintragen(kanal, skript, 'gesendet', note, messung.get('abschnitte_s'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ''))
