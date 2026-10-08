"""Skript -> Video -> Pruefung -> Lernen -> Telegram-Vorschau.

Nur mit bestandener Fakten- und Technikpruefung und Skript-/Video-Note >= 7. Ziel bleibt
10/10; alle Zeitfenster teilen sich ein gespeichertes Tagesbudget je Kanal.
Aufruf: python fabrik/lauf.py kanaele/ai-tools-explained.json [thema]
"""
import datetime, json, os, re, shutil, signal, subprocess, sys, time, urllib.parse, urllib.request, uuid
from pathlib import Path
import budget
from qualitaet import SCHWELLE, bewerten, skript_gruende, rang

# GEMELDET: „Das Ziel ist immer 10/10, nicht bis 8/10." Verbessert wird bis
# 10 oder bis das Zeitbudget erreicht ist; unter 7 bleibt das Video gesperrt.
ZIEL = 10
# 2.000 Gratis-Minuten / 30 Tage / 2 Kanaele = ~33 Min. je Kanal und Tag
BUDGET_S = 45 * 60      # Zeitbudget je Kanal und Tag; GEMESSEN 08.10.2026: Bau mit bezahlten
# Cloudflare-Bildern braucht ~35-40 Min (20-25 Einstellungen inkl. Bildpruefung) - 30 Min reichten 3x nicht.
VERSUCH_S = 25 * 60     # gemessen: ~12 Min. Bau + bis zu 15 Min. Skript mit Story-Pruefung
VERSUCHE_MAX = 5
KORREKTUREN_MAX = 2
KORREKTUR_S = 4 * 60   # Mindestreserve fuer Plan, Teilbau und erneute Pruefung
SENDEN_S = 180  # Zeit fuer Kopie und Telegram innerhalb des Budgets lassen
NEUBAU_MIN_S = 600  # Kleine Restfenster nicht mit einem neuen Skript verbrauchen.
PY = sys.executable


def start_moeglich(kanal, thema=''):
    """Knappe Restfenster nur fuer einen gueltigen vorhandenen Teilbau nutzen."""
    frei = budget.rest(kanal, BUDGET_S)
    if frei >= NEUBAU_MIN_S:
        return True
    if frei <= SENDEN_S:
        return False
    import entwurf_cache, themen
    return entwurf_cache.laden(kanal, f'kanaele/{kanal}.json', thema or themen.nehmen(kanal)) is not None


def melden(text):
    if os.environ.get('CF_PILOT') == '1' or os.environ.get('CF_WORKFLOW_STATUS') == '1':
        print(text)
        return
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if token and chat:
        try:
            with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage',
                    data=urllib.parse.urlencode({'chat_id': chat, 'text': text}).encode(), timeout=30) as r:
                if json.load(r).get('ok') is not True:
                    print('Statusmeldung wurde von Telegram abgelehnt')
        except Exception:
            print('Statusmeldung konnte nicht zugestellt werden')


def schritt(argumente, deadline):
    """Bei Zeitablauf auch ffmpeg/andere Kindprozesse des Arbeiters beenden."""
    rest = deadline - time.monotonic()
    if rest <= 0:
        raise subprocess.TimeoutExpired(argumente, 0)
    p = subprocess.Popen([PY, *argumente], start_new_session=os.name != 'nt',
                         env={**os.environ, 'CF_SCHRITT_ENDE': str(deadline)})
    try:
        return p.wait(timeout=rest)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            try:
                subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True,
                               creationflags=subprocess.CREATE_NO_WINDOW, timeout=15)
            finally:
                if p.poll() is None:
                    p.kill()
        else:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        p.wait()
        raise


def verlauf_eintragen(kanal, skript, status, note, abschnitte=None, messung=None):
    p = Path('verlauf') / f'{kanal}.json'
    p.parent.mkdir(exist_ok=True)
    v = json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
    # Wird ein zuerst verworfener Versuch doch gesendet: nur EIN Eintrag je Thema und Tag
    heute = budget.heute()
    v = [e for e in v if not (e.get('datum') == heute and e.get('thema') == skript['thema'])]
    # GEMELDET: aus erfolgreichen Videos Stimmen, Einstellungen UND Story-Aufbau
    # lernen - darum alles festhalten, was ein Video ausmacht (erfolg.py wertet aus).
    teile = skript.get('teile', [])
    erster = (teile[0]['text'] if teile else '').split('. ')[0]
    art = ('frage' if erster.rstrip().endswith('?') else 'zahl' if re.search(r'\d', erster)
           else 'widerspruch' if re.search(r'\b(but|yet|never|only|nobody|without)\b', erster, re.I) else 'aussage')
    worte = sum(len(t['text'].split()) for t in teile)
    story = skript.get('story') or {}
    v.append({'datum': heute, 'thema': skript['thema'], 'titel': skript['titel'],
              'status': status, 'note': note, 'hook': erster,
              'einstellungen': {'stimme': skript.get('stimme'), 'winkel': skript.get('winkel'),
                                'format': skript.get('format'), 'hook_art': art, 'teile': len(teile),
                                'videoformat': skript.get('videoformat', 'short'),
                                'laenge': 'kurz' if worte < 190 else 'mittel' if worte < 240 else 'lang',
                                'story_note': story.get('note')},
              'gliederung': [' '.join(t['text'].split()[:7]) for t in teile],
              'abschnitte_s': abschnitte})
    v[-1]['einstellungen'].update(
        tempo=(messung or {}).get('tempo', skript.get('tempo', 1.05)),
        untertitel_profil=skript.get('untertitel_profil', 'standard'),
        musik_pegel=skript.get('musik_pegel', 0.1), effekt_pegel=skript.get('effekt_pegel', 1.0))
    p.write_text(json.dumps(v, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def main(kanal_pfad, thema='', entwurf=''):
    import themen
    kanal = Path(kanal_pfad).stem
    budgetkanal = f'pilot-{kanal}' if os.environ.get('CF_PILOT') == '1' else kanal
    if not Path(kanal_pfad).is_file():
        raise ValueError(f'Kanal-Datei fehlt: {kanal_pfad}')
    if budget.rest(budgetkanal, BUDGET_S) <= SENDEN_S:
        print(f'{kanal}: Tagesbudget verbraucht - keine neue Produktion')
        return 0
    reservierung = budget.reservieren(budgetkanal, BUDGET_S)
    start = time.monotonic()
    try:
        return produzieren(kanal_pfad, kanal, thema, start, reservierung[0], themen,
                           **({'entwurf': entwurf} if entwurf else {}))
    finally:
        budget.abschliessen(budgetkanal, reservierung, time.monotonic() - start)


def produzieren(kanal_pfad, kanal, thema, start, frei, themen, entwurf=''):
    import lernen
    import entwurf_cache
    import illustration
    illustration.KONTINGENT_LEER.unlink(missing_ok=True)  # Merker gilt nur fuer diesen Lauf
    # Thema aus Telegram hat Vorrang (GEMELDET: eigene Themen einbringen)
    aus_warteschlange = not thema
    if not thema:
        thema = themen.nehmen(kanal)
        if thema:
            print(f'Thema aus Telegram: {thema}')
    festes_thema = thema
    bester = None  # nur Kandidaten mit bestandenen Pruefungen
    arbeit_ende = start + frei - SENDEN_S
    letzter_grund = 'Kein Versuch abgeschlossen'
    versuch = 0
    korrekturen = 0
    basis = None  # bereits gebautes Video, das weiter verbessert/geprueft wird
    bau_basis = None  # noch unvollstaendiger Bau; geprueftes Skript bleibt erhalten
    if not entwurf and os.environ.get('CF_PILOT') != '1':
        bau_basis = entwurf_cache.laden(kanal, kanal_pfad, festes_thema)
        if bau_basis:
            print('Geprueften Entwurf aus vorherigem Lauf fortsetzen; keine neue Skriptanfrage')
        else:
            # Vorab geschriebenes, geprueftes Skript (vorrat.py, nachts) - spart die Skriptphase.
            import vorrat
            bau_basis = vorrat.nehmen(kanal_pfad, festes_thema)
    ausstehende_korrektur = None  # auch nach einem Ausfall der Video-Pruefung
    bericht = {'id': os.environ.get('GITHUB_RUN_ID') or uuid.uuid4().hex,
               'kanal': kanal, 'datum': budget.heute(), 'runden': [], 'status': 'offen'}
    def protokoll(status):
        bericht['status'] = status
        bericht['grund'] = letzter_grund if status not in ('gesendet', 'pilot_bestanden') else ''
        bericht['sekunden'] = round(time.monotonic() - start, 1)
        aus = Path('ausgabe')
        aus.mkdir(exist_ok=True)
        (aus / 'bericht.json').write_text(json.dumps(bericht, indent=2, ensure_ascii=False), encoding='utf-8')
        pfad = Path('verlauf/messungen') / f'{kanal}.json'
        pfad.parent.mkdir(parents=True, exist_ok=True)
        liste = json.loads(pfad.read_text(encoding='utf-8')) if pfad.exists() else []
        liste = [e for e in liste if e.get('id') != bericht['id']]
        pfad.write_text(json.dumps((liste + [bericht])[-60:], indent=2, ensure_ascii=False), encoding='utf-8')
    # Neuer Versuch nur, wenn er noch sicher ins Zeitbudget passt
    while versuch < VERSUCHE_MAX and (versuch == 0 or time.monotonic()
            + (KORREKTUR_S if basis or bau_basis else VERSUCH_S) <= arbeit_ende):
        versuch += 1
        ordner = Path(f'versuch{versuch}')
        shutil.rmtree(ordner, ignore_errors=True)
        rundenstart = time.monotonic()
        plan = None
        runde = {'runde': versuch, 'art': 'korrektur' if basis else 'produktion'}
        bericht['runden'].append(runde)
        phase = 'Skript'
        try:
            if bau_basis:
                ordner.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bau_basis / 'skript.json', ordner / 'skript.json')
                r = 0
                runde['art'] = 'bau_fortsetzen'
            elif basis:
                if basis[1] is None:
                    # Ein API-Ausfall rechtfertigt kein neues Skript oder Rendern.
                    shutil.copytree(basis[0], ordner)
                    r = 0
                    runde['art'] = 'pruefung_wiederholen'
                elif korrekturen < KORREKTUREN_MAX:
                    korrekturen += 1
                    r = schritt(['fabrik/nachbessern.py', str(basis[0]), kanal_pfad, str(ordner)], arbeit_ende)
                    if r == 2:
                        letzter_grund = 'Keine weitere gezielte Korrektur moeglich'
                        runde['status'] = 'keine_korrektur'
                        break
                    if r == 0:
                        plan = json.loads((ordner / 'korrektur.json').read_text(encoding='utf-8'))
                        runde['plan'] = plan
                        ausstehende_korrektur = {'vorher': basis[1], 'plan': plan,
                                                'start': rundenstart,
                                                'id': f'{bericht["id"]}-{versuch}'}
                else:
                    runde['status'] = 'korrekturgrenze'
                    break
            else:
                # Auch im Ersatzfenster Zeit fuer Bilder, Rendern und Pruefung lassen.
                skript_ende = min(arbeit_ende, time.monotonic()
                                  + min(480, max(0, arbeit_ende - time.monotonic()) * .4))
                try:
                    r = schritt(['fabrik/pilot_entwurf.py', entwurf, kanal_pfad, str(ordner / 'skript.json')]
                                if entwurf else
                                ['fabrik/skript.py', kanal_pfad, str(ordner / 'skript.json'), thema], skript_ende)
                except subprocess.TimeoutExpired:
                    pfad = ordner / 'skript.json'
                    if not pfad.exists() or skript_gruende(json.loads(pfad.read_text(encoding='utf-8'))):
                        raise
                    print('Skriptphase beendet; vollstaendig gepruefte Zwischenfassung wird gebaut')
                    runde['skript_zwischenfassung'] = True
                    r = 0
            if r != 0:
                letzter_grund = ('Faktenpruefung nicht bestanden' if r == 2 else
                                'Skriptqualitaet unter Freigabe' if r == 3 else f'Skript fehlgeschlagen (Code {r})')
                print(f'Versuch {versuch}: {letzter_grund}')
                runde['status'] = 'skriptfehler'
                runde.update(exitcode=r, grund=letzter_grund)
                if basis:
                    break
                if (ordner / 'skript.json').exists():
                    abgelehnt = json.loads((ordner / 'skript.json').read_text(encoding='utf-8'))
                    runde.update(sperrgruende=skript_gruende(abgelehnt),
                                 story_note=(abgelehnt.get('story') or {}).get('note'),
                                 skript_probleme=abgelehnt.get('pruefung', {}).get('probleme', []))
                    verlauf_eintragen(kanal, abgelehnt,
                                      'faktenpruefung' if r == 2 else 'skriptqualitaet' if r == 3 else 'skriptfehler', None)
                if entwurf:
                    break  # Eine gesperrte feste Vorlage nicht unveraendert erneut pruefen.
                continue
            skript = json.loads((ordner / 'skript.json').read_text(encoding='utf-8'))
            skriptfehler = skript_gruende(skript)
            if skriptfehler:
                letzter_grund = '; '.join(skriptfehler)
                runde.update(status='skriptqualitaet', sperrgruende=skriptfehler)
                verlauf_eintragen(kanal, skript, 'skriptqualitaet', None)
                if basis:
                    break
                continue
            runde['skript_s'] = round(time.monotonic() - rundenstart, 1)
            phase = 'Videobau'
            bau_start = time.monotonic()
            b = (0 if basis and basis[1] is None else schritt(
                ['fabrik/bauen.py', str(ordner / 'skript.json'), str(ordner)]
                + ([str(bau_basis)] if bau_basis else [str(basis[0])] if basis else []), arbeit_ende))
            runde['bau_s'] = round(time.monotonic() - bau_start, 1)
            if b != 0:
                letzter_grund = 'Videobau fehlgeschlagen'
                import illustration
                kontingent_leer = illustration.KONTINGENT_LEER.exists()
                if kontingent_leer:
                    # Ein neuer Versuch erzeugt ohne Bildkontingent nur denselben Fehler.
                    letzter_grund = ('Cloudflare-Bildkontingent aufgebraucht - neue Bilder erst nach '
                                     'Freigabe durch Cloudflare; Skript bleibt im Vorrat')
                print(f'Versuch {versuch}: {letzter_grund}')
                verlauf_eintragen(kanal, skript, 'baufehler', None)
                runde['status'] = 'baufehler'
                if basis or kontingent_leer:
                    break
                bau_basis = ordner
                continue
            bau_basis = None
            (ordner / 'kritik.json').unlink(missing_ok=True)
            phase = 'Video-Pruefung'
            pruef_start = time.monotonic()
            k = schritt(['fabrik/kritik.py', str(ordner / 'short.mp4'), str(ordner / 'skript.json'),
                         str(ordner / 'kritik.json')], arbeit_ende)
            runde['pruefung_s'] = round(time.monotonic() - pruef_start, 1)
            if k != 0 or not (ordner / 'kritik.json').exists():
                letzter_grund = 'Video-Pruefung nicht verfuegbar'
                print(letzter_grund + ' - Video bleibt gesperrt')
                verlauf_eintragen(kanal, skript, 'pruefung_fehlt', None)
                runde['status'] = 'pruefung_fehlt'
                basis = (ordner, None)
                continue
            kritik = json.loads((ordner / 'kritik.json').read_text(encoding='utf-8'))
            note, gruende = bewerten(skript, kritik)
            messung = json.loads((ordner / 'messung.json').read_text(encoding='utf-8')) \
                if (ordner / 'messung.json').exists() else {}
            runde.update(note=note, sperrgruende=gruende, messung=messung,
                         kategorien=kritik.get('kategorien', {}), probleme=kritik.get('probleme', []),
                         sekunden=round(time.monotonic() - rundenstart, 1), status='geprueft')
            if ausstehende_korrektur:
                a = ausstehende_korrektur
                runde['plan'] = a['plan']
                runde['lernergebnis'] = lernen.korrektur_eintragen(
                    kanal, a['vorher'], kritik, a['plan'], time.monotonic() - a['start'], a['id'])
                ausstehende_korrektur = None
        except subprocess.TimeoutExpired:
            letzter_grund = f'{phase}-Zeitlimit erreicht (Arbeiter beendet)'
            print(letzter_grund)
            runde['status'] = 'zeitbudget'
            runde['phase'] = phase
            break
        except (ValueError, KeyError, TypeError, OSError) as e:
            letzter_grund = f'Versuch fehlgeschlagen ({type(e).__name__})'
            print(letzter_grund)
            runde['status'] = 'fehler'
            if basis:
                break
            continue
        finally:
            runde.setdefault('sekunden', round(time.monotonic() - rundenstart, 1))
            if os.environ.get('CF_PILOT') != '1' and (ordner / 'skript.json').exists():
                try:
                    entwurf_cache.sichern(kanal, kanal_pfad, festes_thema, ordner)
                except (OSError, ValueError, KeyError, TypeError):
                    print('Entwurf-/Teilbau-Sicherung fehlgeschlagen; keine falsche Freigabe')
            if ausstehende_korrektur and 'lernergebnis' not in runde:
                # Auch abgebrochene Korrekturen bleiben sichtbar; ohne Note kein
                # Urteil ueber den Nutzen einer Einstellung ableiten.
                try:
                    a = ausstehende_korrektur
                    runde['lernergebnis'] = lernen.korrektur_eintragen(
                        kanal, a['vorher'], {}, a['plan'], time.monotonic() - a['start'], a['id'])
                except (OSError, ValueError):
                    print('Korrektur-Ergebnis konnte nicht gespeichert werden')
        print(f'Versuch {versuch}: {note}/10; Sperrgruende: {gruende}')
        if not gruende and (bester is None or rang(kritik) > rang(bester[2])):
            bester = (note, ordner, kritik)
        # Weitere Korrekturen setzen auf dem besten bestandenen Video auf.
        # Ohne bestandenen Kandidaten wird der zuletzt gepruefte Entwurf repariert.
        basis = (bester[1], bester[2]) if bester else (ordner, kritik)
        if not gruende and note >= ZIEL:
            break
        # Lernen als begrenzter Kindprozess: API-Haenger verbrauchen nicht den ganzen Tag.
        try:
            story = skript.get('story') or {}
            lern = dict(kritik)
            lern['probleme'] = kritik.get('probleme', []) + [{'zeit': '-', 'art': 'story', 'text': w}
                                                             for w in story.get('schwaechen', [])]
            lern['probleme'] += [{'zeit': '-', 'art': 'technik', 'text': str(b)}
                                 for b in kritik.get('technik', {}).get('befunde', [])]
            lp = ordner / 'lernfeedback.json'
            lp.write_text(json.dumps(lern, ensure_ascii=False), encoding='utf-8')
            if schritt(['fabrik/lernen.py', kanal, str(lp)], min(arbeit_ende, time.monotonic() + 90)):
                print('Lernen fehlgeschlagen - Kandidat bleibt erhalten')
        except Exception:
            print('Lernen nicht moeglich - Kandidat bleibt erhalten')
        letzter_grund = '; '.join(gruende) if gruende else f'Ziel {ZIEL}/10 noch nicht erreicht'
        verlauf_eintragen(kanal, skript, 'unter_ziel' if gruende else 'kandidat', note)
        thema = festes_thema
        print(f'{(time.monotonic() - start) / 60:.1f} Min. im aktuellen Lauf verbraucht')

    if bester is None:
        # Den letzten Versuch fuer die Fehlersuche als Artefakt behalten.
        if versuch and ordner.exists():
            aus = Path('ausgabe')
            shutil.rmtree(aus, ignore_errors=True)
            shutil.copytree(ordner, aus)
        melden(f'🔁 {kanal}: noch kein freigabefaehiges Video. Grund: {letzter_grund}. '
               'Weitere Zeitfenster versuchen es nur, solange Tagesbudget uebrig ist.')
        protokoll('gesperrt')
        return 2 if os.environ.get('CF_PILOT') == '1' else 0
    note, ordner, kritik = bester
    aus = Path('ausgabe')
    shutil.rmtree(aus, ignore_errors=True)
    shutil.copytree(ordner, aus)
    skript = json.loads((aus / 'skript.json').read_text(encoding='utf-8'))
    messung = json.loads((aus / 'messung.json').read_text(encoding='utf-8')) \
        if (aus / 'messung.json').exists() else {}
    if os.environ.get('CF_PILOT') == '1':
        verlauf_eintragen(kanal, skript, 'pilot', note, messung.get('abschnitte_s'), messung)
        protokoll('pilot_bestanden')
        return 0
    try:
        code = schritt(['fabrik/freigabe.py', str(aus / 'skript.json'), str(aus / 'short.mp4')], start + frei)
    except (subprocess.TimeoutExpired, OSError):
        protokoll('zustellfehler')
        raise
    if code:
        protokoll('zustellfehler')
        raise RuntimeError(f'Telegram-Zustellung fehlgeschlagen (Code {code})')
    verlauf_eintragen(kanal, skript, 'gesendet', note, messung.get('abschnitte_s'), messung)
    entwurf_cache.erledigen(kanal)
    import vorrat
    vorrat.erledigen(kanal, skript)
    if aus_warteschlange and festes_thema:
        themen.erledigen(kanal, festes_thema)
    protokoll('gesendet')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '',
                  sys.argv[3] if len(sys.argv) > 3 else ''))
