"""Skript -> Video -> Pruefung -> Lernen -> Telegram-Vorschau.

Nur mit bestandener Fakten- und Technikpruefung und Skript-/Video-Note >= 7. Ziel bleibt
10/10; alle Zeitfenster teilen sich ein gespeichertes Tagesbudget je Kanal.
Aufruf: python fabrik/lauf.py kanaele/ai-tools-explained.json [thema]
"""
import datetime, json, os, re, shutil, signal, subprocess, sys, time, urllib.parse, urllib.request, uuid
from pathlib import Path
import budget
from qualitaet import SCHWELLE, ENTWURF_MIN, bewerten, nur_ki_geschmack, nur_bildbezug, skript_gruende, rang

# GEMELDET: „Das Ziel ist immer 10/10, nicht bis 8/10." Verbessert wird bis
# 10 oder bis das Zeitbudget erreicht ist; unter 7 bleibt das Video gesperrt.
ZIEL = 10
# Repo seit 08.10.2026 oeffentlich -> GitHub-Minuten unbegrenzt (vorher 2.000/Monat = ~33 Min. je Kanal).
# GEMESSEN 08.10.: ein Bau braucht ~35-40 Min; 45 Min liessen keinen Platz fuer eine Korrektur
# oder Gemini-Ueberlast. Nutzerentscheidung 08.10.: 90 Min je Kanal und Tag.
BUDGET_S = 90 * 60
# Einmaliges Zusatzbudget je (Kanal, UTC-Datum) - nur mit ausdruecklicher Nutzerfreigabe.
# Nutzer 14.10.2026 ca. 18:45 Berlin, auf direkte Rueckfrage: "Ja, 30 Min. extra" nur heute,
# nur Business (13/18 Motive + Ton im Cache, 5220/5400 s verbraucht). Gates unveraendert.
# Zweite Rueckfrage 14.10. ca. 19:30 Berlin: "Ja, 40 Min. extra" (insgesamt 70 Min. extra heute).
ZUSATZ_S = {('business-origin-stories', '2026-10-14'): 70 * 60}
# Nutzer 17.10.2026 ca. 18:00 Berlin, nachdem das Langvideo heute scheiterte: "Koennen wir heute noch
# Shorts fuer jeweils Kanal erstellen?" -> NUR heute je ein Short mehr als das Tagesziel. Zeitbudget und
# alle Pruefungen unveraendert (video.yml liest das in tagesziel()).
# Nutzer 18.10.2026 ca. 17:40 Berlin: "wie sieht's aus eine Video Shorts jeweils Kanal?" - Tagesshorts
# (Janas, Ford) waren schon geliefert; heute noch je einer, erster Test von Spannungsbogen/Zoom (49588a0).
# Nutzer 19.10.2026: "Es waere besser fuer weiter ki Short heute Abend" - nur KI, erster Lauf mit
# Zuschauer-Trendthema und neuer Stimme Puck.
EXTRA_VIDEOS = {('ai-tools-explained', '2026-10-17'): 1, ('business-origin-stories', '2026-10-17'): 1,
                ('ai-tools-explained', '2026-10-18'): 1, ('business-origin-stories', '2026-10-18'): 1,
                ('ai-tools-explained', '2026-10-19'): 2}
# 19.10.: zweites Extra auf Nutzerwunsch - der erste Extra-Short traf wegen eines Recherchefehlers
# (89b13d5) nicht das Trendthema; dieser Lauf soll alle Aenderungen des Tages belegen.


def extra_videos(kanal, datum):
    return EXTRA_VIDEOS.get((kanal, str(datum)), 0)
# Langvideo (8-10 Min., ~70-80 Bilder statt 25) - erster Pilot 08.10.2026, Bauzeit noch nicht
# gemessen; hochgerechnet aus ~35-40 Min. je Short. GitHub-Jobs enden spaetestens nach 6 h.
BUDGET_LANG_S = 200 * 60
VERSUCH_S = 25 * 60     # gemessen: ~12 Min. Bau + bis zu 15 Min. Skript mit Story-Pruefung
VERSUCHE_MAX = 5
PLAN_NEU_BIS = 5  # nur so frueh haengende Bauten bekommen einen neuen Bildplan
WEITER_MAX = 20  # zusaetzliche Bauversuche, wenn jeder weiter kommt (Zeitbudget begrenzt ohnehin)


def einstellung_nr(baufehler):
    """'Phase 33, Einstellung 53: kein passendes Hauptbild' -> 53; ohne Angabe -1."""
    import re
    m = re.search(r'Einstellung (\d+):', baufehler or '')
    return int(m.group(1)) if m else -1
KORREKTUREN_MAX = 2
KORREKTUR_S = 4 * 60   # Mindestreserve fuer Plan, Teilbau und erneute Pruefung
SENDEN_S = 180  # Zeit fuer Kopie und Telegram innerhalb des Budgets lassen
NEUBAU_MIN_S = 600  # Kleine Restfenster nicht mit einem neuen Skript verbrauchen.
PY = sys.executable


def gesendet_heute(kanal):
    """Heute zugestellte Shorts dieses Kanals (auch Wiederholungen - auch sie haben Zeit verbraucht)."""
    try:
        v = json.loads(Path(f'verlauf/{kanal}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 0
    return sum(1 for e in v if isinstance(e, dict) and e.get('datum') == str(budget.heute())
               and e.get('status') == 'gesendet'
               and (e.get('einstellungen') or {}).get('videoformat') != 'lang')


def tagesgrenze(kanal, grenze):
    # Nutzerwunsch 21.10.2026: weitere Videos per Handstart, solange das kostenlose Kontingent reicht.
    # Jedes zugestellte Video gibt ein neues Zeitfenster frei; Fehlversuche nicht - ein haengender Fehler
    # verbraucht so hoechstens ein Fenster. Automatische Starts begrenzt weiter das Tagesziel (video.yml).
    # GEMESSEN 21.10.2026: ohne diese Bedingung bekamen auch die Zeitplan-Ersatztermine ein neues Fenster -
    # Business lief nach dem (wiederholten) Ford-Video viermal (4134 s), jedes Mal ohne Video.
    fenster = 1 + gesendet_heute(kanal) if os.environ.get('CF_HANDSTART') == '1' else 1
    return grenze * fenster + ZUSATZ_S.get((kanal, budget.heute()), 0)


def start_moeglich(kanal, thema=''):
    """Knappe Restfenster nur fuer einen gueltigen vorhandenen Teilbau nutzen."""
    frei = budget.rest(kanal, tagesgrenze(kanal, BUDGET_S))
    if frei >= NEUBAU_MIN_S:
        return True
    if frei <= SENDEN_S:
        return False
    import entwurf_cache, themen
    return entwurf_cache.laden(kanal, f'kanaele/{kanal}.json', thema or themen.nehmen(kanal)) is not None


def bildplan_verwerfen(ordner):
    """Gespeicherten Bildplan im Teilbau loeschen, damit der naechste Bau neu plant; Ton bleibt."""
    pfad = Path(ordner) / 'bauzustand.json'
    try:
        d = json.loads(pfad.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    if not d.pop('bildplan', None):
        return False
    pfad.write_text(json.dumps(d), encoding='utf-8')
    print('Gleicher Bildfehler zweimal - Bildplan wird neu erstellt (Stimme bleibt)')
    return True


def aus_fehlern_lernen(kanal, runden, deadline):
    """Auch ein Lauf OHNE Video lehrt etwas (Nutzerauftrag 09.10.2026: „selber daraus lernen, was
    er falsch gemacht hat"). Vorher lernte nur ein fertig gebautes und bewertetes Video; die meisten
    Fehlschlaege (Faktenpruefung, Story-Note, Skriptqualitaet) gingen spurlos verloren.
    Baufehler sind Technik, keine Schreibregel - die bleiben im Verlauf (grund), nicht im Regelbuch."""
    probleme = []
    for r in runden:
        probleme += [{'zeit': '-', 'art': 'fakten', 'text': str(x)[:300]} for x in r.get('skript_probleme') or []]
        probleme += [{'zeit': '-', 'art': 'story', 'text': str(x)[:300]} for x in r.get('story_schwaechen') or []]
        # Nur Sperrgruende des Skripts: nach dem Videobau sind es Pruef-/Technikmeldungen
        # („Video-Note fehlt", „unter 61 s") - daraus wurden 10.10.2026 Unsinnsregeln gelernt.
        if r.get('status') in ('skriptfehler', 'skriptqualitaet'):
            probleme += [{'zeit': '-', 'art': 'skript', 'text': str(x)[:300]} for x in r.get('sperrgruende') or []]
    probleme = list({p['text']: p for p in probleme}.values())[:15]
    if not probleme:
        return False
    try:
        lp = Path('ausgabe-lernen') / f'{kanal}.json'
        lp.parent.mkdir(exist_ok=True)
        lp.write_text(json.dumps({'probleme': probleme, 'kategorien': {}}, ensure_ascii=False), encoding='utf-8')
        if schritt(['fabrik/lernen.py', kanal, str(lp)], deadline):
            print('Lernen aus Fehlschlaegen fehlgeschlagen')
            return False
        return True
    except Exception as e:  # Lernen darf nie den Lauf kippen
        print('Lernen aus Fehlschlaegen nicht moeglich:', type(e).__name__)
        return False


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


PRUEF_WIEDERHOLUNG_S = (120, 300)  # Wartezeiten vor erneuter Pruefung nach Dienstausfall
PRUEF_RESERVE_S = 420              # danach muss noch Zeit fuer Pruefung und Versand bleiben


ANBIETER_WARTEN_MAX_S = 360  # laengere Sperren (Tageskontingent) nicht abwarten
ANBIETER_REST_S = 900        # danach muss noch Zeit fuer Bau, Pruefung und Versand bleiben


def kurze_anbieterpause(jetzt=None):
    """Sekunden, bis die erste kurze Gemini-Sperre (Ueberlast/Zeitlimit) ablaeuft; None ohne kurze Sperre."""
    import ki_speicher
    jetzt = time.time() if jetzt is None else jetzt
    konto = ki_speicher.konto(os.environ.get('GEMINI_API_KEY', '')) + ':'
    bis = [e['bis'] for k, e in (ki_speicher.lesen_json(ki_speicher.KONTINGENT).get('modelle') or {}).items()
           if k.startswith(konto) and isinstance(e, dict) and isinstance(e.get('bis'), (int, float))
           and jetzt < e['bis'] <= jetzt + ANBIETER_WARTEN_MAX_S
           and not re.search(r'kontingent|nicht verfuegbar', str(e.get('grund')), re.I)]
    return min(bis) - jetzt + 15 if bis else None


def pruefung_ausgefallen(code, pfad):
    """Pruefung brach ab, ohne zu urteilen (Absturz/503/Zeitlimit des Dienstes) - kein Qualitaetsurteil."""
    if code != 0 or not Path(pfad).exists():
        return True
    try:
        k = json.loads(Path(pfad).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return True
    befunde = (k.get('bildbezug') or {}).get('befunde') or []
    return any('nicht vollstaendig moeglich' in str(b) for b in befunde)


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


def verlauf_eintragen(kanal, skript, status, note, abschnitte=None, messung=None, grund=None):
    p = Path('verlauf') / f'{kanal}.json'
    p.parent.mkdir(exist_ok=True)
    v = json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
    # Wird ein zuerst verworfener Versuch doch gesendet: nur EIN Eintrag je Thema und Tag
    heute = budget.heute()
    # Short und Langvideo zum selben Thema sind zwei Videos - nur dasselbe Format ersetzen (16.10.2026).
    format_neu = skript.get('videoformat', 'short')
    v = [e for e in v if not (e.get('datum') == heute and e.get('thema') == skript['thema']
                              and (e.get('einstellungen') or {}).get('videoformat', 'short') == format_neu)]
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
              'quellen': skript.get('quellen', []),
              'einstellungen': {'stimme': skript.get('stimme'), 'winkel': skript.get('winkel'),
                                'format': skript.get('format'), 'hook_art': art, 'teile': len(teile),
                                'videoformat': skript.get('videoformat', 'short'),
                                'laenge': 'kurz' if worte < 190 else 'mittel' if worte < 240 else 'lang',
                                'story_note': story.get('note')},
              'gliederung': [' '.join(t['text'].split()[:7]) for t in teile],
              'abschnitte_s': abschnitte})
    if grund:  # Warum ein Versuch scheiterte - sonst nur im vergaenglichen GitHub-Log
        v[-1]['grund'] = str(grund)[:300]
    v[-1]['einstellungen'].update(
        tempo=(messung or {}).get('tempo', skript.get('tempo', 1.05)),
        untertitel_profil=skript.get('untertitel_profil', 'standard'),
        musik_pegel=skript.get('musik_pegel', 0.1), effekt_pegel=skript.get('effekt_pegel', 1.0))
    p.write_text(json.dumps(v, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def budget_fuer(profil):
    return BUDGET_LANG_S if profil.get('videoformat') == 'lang' else BUDGET_S


def main(kanal_pfad, thema='', entwurf=''):
    import themen
    kanal = Path(kanal_pfad).stem
    budgetkanal = f'pilot-{kanal}' if os.environ.get('CF_PILOT') == '1' else kanal
    if not Path(kanal_pfad).is_file():
        raise ValueError(f'Kanal-Datei fehlt: {kanal_pfad}')
    import kanalstandard
    if kanalstandard.laden(kanal_pfad).get('videoformat') == 'lang' and budgetkanal == kanal:
        # 16.10.2026: woechentliches Langvideo. Mit gemeinsamem Tagesbudget haette es die Business-Shorts
        # desselben Tages blockiert (90 Min.) - eigenes Budget, eigene Abrechnung.
        budgetkanal = f'lang-{kanal}'
    gesamt = tagesgrenze(budgetkanal, budget_fuer(kanalstandard.laden(kanal_pfad)))
    if budget.rest(budgetkanal, gesamt) <= SENDEN_S:
        print(f'{kanal}: Tagesbudget verbraucht - keine neue Produktion')
        return 0
    reservierung = budget.reservieren(budgetkanal, gesamt)
    start = time.monotonic()
    # GEMESSEN 28.10.2026 (Lauf 40691009317, Rolls-Royce): Handstart mit drei freien Fenstern (270 Min.) -
    # der Lauf plante mit 2 Stunden Restzeit, GitHub brach den Job nach timeout-minutes 110 ab, kein Video,
    # kein Entwurf. Ein Lauf arbeitet hoechstens ein Fenster lang (passend zu timeout-minutes der Workflows).
    frei = min(reservierung[0], budget_fuer(kanalstandard.laden(kanal_pfad)))
    try:
        return produzieren(kanal_pfad, kanal, thema, start, frei, themen,
                           **({'entwurf': entwurf} if entwurf else {}))
    finally:
        budget.abschliessen(budgetkanal, reservierung, time.monotonic() - start)


def produzieren(kanal_pfad, kanal, thema, start, frei, themen, entwurf=''):
    import lernen
    import entwurf_cache
    import illustration
    illustration.KONTINGENT_LEER.unlink(missing_ok=True)  # Merker gilt nur fuer diesen Lauf
    import fortschritt
    fortschritt.starten(kanal)  # Steuerungsbot "Status": echte Prozentzahl statt Uhr-Schaetzung (25.10.2026)
    import kanalstandard
    # Langvideo: ~1.200 Woerter plus Fakten-/Storypruefung brauchen mehr als die 8 Min. eines Shorts.
    # GEMESSEN 17.10.2026 (Run 39032531951, Coca-Cola): 20 Min. reichten nicht - Autor, 6 Faktenkorrekturen,
    # Chronik- und Laengenkorrektur, dann "Skript-Zeitlimit erreicht". Bei 200 Min. Budget bleiben mit 45 Min.
    # Skript noch 155 Min. fuer Bilder, Bau und Pruefung (Gesamtbudget unveraendert).
    # GEMESSEN 29.10.2026: 480 s reichten bei langsamem Gemini nicht (lokale MCP-Probe 665 s, zwei KI-Laeufe mit
    # Story 6/10 im Zeitlimit). 900 s, weiter hoechstens 40 % der Restarbeit; das Gesamtbudget bleibt gleich.
    skriptfrist = 45 * 60 if kanalstandard.laden(kanal_pfad).get('videoformat') == 'lang' else 900
    # GEMESSEN 17.10.2026: Short und Langvideo teilten verlauf/entwuerfe/<kanal>.json - ein Business-Short
    # konnte das gepruefte Langvideo-Skript (samt Teilbau) ueberschreiben. Langvideo hat einen eigenen Platz.
    cache_kanal = entwurf_cache.cache_name(kanal, kanal_pfad)
    os.environ['CF_BILDSPEICHER_BASIS'] = str(entwurf_cache.bildspeicher(cache_kanal).resolve())
    try:  # Aufraeumen darf den Lauf nie kippen
        for name in entwurf_cache.bilder_aufraeumen(cache_kanal):
            print('Gepruefte Bilder geloescht (Thema per TikTok-Knopf freigegeben oder aelter als 30 Tage):', name)
    except OSError as e:
        print('Bilderspeicher nicht aufgeraeumt:', e)
    # GEMELDET 16.10.2026: Airbnb kam zwei Tage hintereinander (Entwurf vom 15.10. per Handversand
    # zugestellt, Thema blieb stehen). Vor jeder Themenwahl schon gelieferte Themen austragen.
    try:  # Aufraeumen darf den Lauf nie kippen
        for x in [x for x in themen.laden() if isinstance(x, dict) and x.get('kanal') == kanal]:
            if themen.schon_geliefert(kanal, x['thema']) is True:
                themen.erledigen(kanal, x['thema'])
                print('Thema schon geliefert - aus der Warteschlange entfernt:', x['thema'])
    except (TypeError, OSError, ValueError, KeyError) as e:
        print('Warteschlange nicht bereinigt:', type(e).__name__)
    # Thema aus Telegram hat Vorrang (GEMELDET: eigene Themen einbringen)
    aus_warteschlange = not thema
    trend = None
    vorrat_thema = None
    if not thema and not entwurf:
        import vorrat
        vorrat_thema = vorrat.bereit(kanal_pfad)
        if vorrat_thema:
            # Ein fertig geprueftes Skript schlaegt einen neuen, ungeprueften Versuch (15.10.2026).
            print(f'Geprueftes Vorrat-Skript bereit ({vorrat_thema}) - Trend-Check uebersprungen')
            thema = vorrat_thema
        elif vorrat_thema == '':
            # Nutzer 21.10.2026: „Harness Engineering 101 interessiert niemanden" - ein frei gewaehltes
            # Vorratsskript (GitHub-Neuheit/klassische Marke) nur, wenn es keinen offenen YouTube-/Google-Trend
            # gibt; sonst das naechste noch nicht gelieferte Trendthema des Tages (alle Kanaele).
            import trendcheck
            gewaehlt, trend = trendcheck.waehlen(kanal, themen=themen)
            offen_trend = trendcheck.trend_themen(kanal)
            if offen_trend:
                thema = offen_trend[0]
                print(f'Trendthema statt frei gewaehltem Vorrat-Skript: {thema}')
                if trend:
                    os.environ['CF_TRENDGRUND'] = trend['grund'][:300]
            elif themen.nehmen(kanal):
                # Entscheidung A (30.10.2026): Nutzerthema vor frei gewaehltem Vorrat; der Vorrat bleibt erhalten.
                ersatz = themen.nehmen(kanal)
                print(f'Kein offener Trend - Thema aus der Warteschlange statt freiem Vorrat-Skript: {ersatz}')
                thema = ersatz
            else:
                print('Kein offener YouTube-/Google-Trend - geprueftes frei gewaehltes Vorrat-Skript')
            vorrat_thema = None if offen_trend or thema else ''
    if not thema and vorrat_thema is None and not trend:
        # GEMELDET 09.10.2026: Themen muessen aus Google Trends/YouTube-Viralem kommen.
        # Der Trend-Check waehlt unter Warteschlange + Trendfirmen; '' = freie Trendwahl.
        import trendcheck
        thema, trend = trendcheck.waehlen(kanal, themen=themen)
        if thema == '':
            # Nutzer 30.10.2026 (Entscheidung A): ohne echtes Trendsignal zuerst das eigene Thema der Warteschlange -
            # Nintendo/Adidas kamen frei gewaehlt, obwohl "Kongo Gumi" (1,0 Punkte < 1,5) wartete.
            ersatz = themen.nehmen(kanal)
            if ersatz:
                print(f'Kein Trendsignal - Thema aus der Warteschlange: {ersatz}')
                thema, trend = ersatz, None
        if thema and trendcheck.heute_gescheitert(kanal, thema) >= 2:
            # GEMESSEN 29.10.2026 (KI 40885084229, 40890125955): derselbe Trend ("Sell PDFs Made With Claude") lief
            # zweimal ins Skript-Zeitlimit - die Quellen trugen ihn nicht. Dann die Nutzerthemen der Warteschlange.
            ersatz = themen.nehmen(kanal)
            print(f'Trendthema {thema} heute schon zweimal gescheitert - '
                  + (f'Thema aus der Warteschlange: {ersatz}' if ersatz else 'freie Wahl'))
            thema, trend = ersatz, None
        if thema and themen.schon_geliefert(kanal, thema) is True:
            # Zusatzvideo am selben Tag: der Bericht des Tages nennt das schon gesendete Thema - naechster Trend.
            offen_trend = trendcheck.trend_themen(kanal)
            if not offen_trend and trendcheck.bericht_veraltet(kanal):
                # GEMESSEN 23.10.2026: Der Morgenbericht kannte nur ein Thema -> Zusatzvideo bekam eine freie
                # GitHub-Neuheit. Erst neu nach YouTube-/Google-Trends suchen, dann frei waehlen.
                neu_thema, neu_trend = trendcheck.waehlen(kanal, themen=themen, neu=True)
                if neu_thema and themen.schon_geliefert(kanal, neu_thema) is not True:
                    offen_trend, trend = [neu_thema], neu_trend
                else:
                    offen_trend = trendcheck.trend_themen(kanal)
            # GEMESSEN 30.10.2026 (Business 41037368167): nach Intel kam freie Wahl (Nintendo), obwohl "Kongo Gumi"
            # in der Warteschlange des Nutzers stand. Ohne weiteren Trend zuerst das naechste Nutzerthema.
            ersatz = None if offen_trend else themen.nehmen(kanal)
            if ersatz and themen.schon_geliefert(kanal, ersatz) is True:
                ersatz = None
            print(f'Trendthema {thema} heute schon geliefert - '
                  + (f'naechstes: {offen_trend[0]}' if offen_trend else
                     f'kein weiterer Trend, Thema aus der Warteschlange: {ersatz}' if ersatz else
                     'kein weiterer Trend, freie Wahl'))
            thema = offen_trend[0] if offen_trend else (ersatz or '')
            if ersatz:
                trend = None
        if thema:
            print(f'Thema nach Trend-Check: {thema}')
        if trend and thema:
            # Telegram zeigt dem Nutzer, WARUM heute dieses Thema (freigabe.py liest es).
            os.environ['CF_TRENDGRUND'] = trend['grund'][:300]
    festes_thema = thema
    bester = None  # nur Kandidaten mit bestandenen Pruefungen
    entwurf_kandidat = None  # nur KI-Geschmack unter 7/10, Pflichtpruefungen bestanden
    entwurf_rang = None  # (1, Note) fuer KI-Geschmack vor (0, -abgelehnte Bilder) fuer Bildbezug
    arbeit_ende = start + frei - SENDEN_S
    heute_schwaechen, heute_pfad = [], Path('ausgabe-lernen') / f'heute-{kanal}.json'
    heute_pfad.parent.mkdir(exist_ok=True)
    os.environ.pop('CF_HEUTE_SCHWAECHEN', None)
    letzter_grund = 'Kein Versuch abgeschlossen'
    trend_fehlschlaege = 0
    versuch = 0
    korrekturen = 0
    letzter_baufehler = ''
    # GEMESSEN 17.10.2026 (Langvideo Coca-Cola, Run 39034546019): 84 Einstellungen; jeder Bauversuch kam
    # weiter (28 -> 42 -> 49 -> 51 -> 53, das Bild bestand jeweils im naechsten Anlauf), nach Versuch 5
    # war Schluss - mit ueber 2 Std. Restbudget. Ein Bauversuch, der WEITER kam, zaehlt nicht mit.
    weiter_gekommen = 0
    anbieter_gewartet = False
    basis = None  # bereits gebautes Video, das weiter verbessert/geprueft wird
    bau_basis = None  # noch unvollstaendiger Bau; geprueftes Skript bleibt erhalten
    # GEMELDET 09.10.2026: „hoffentlich faengt nicht immer alles von vorne an". Auch Probelaeufe
    # setzen ein geprueftes Skript samt Stimme/Bildern fort (eigener Cache in pilot.yml, 6 h).
    if not entwurf:
        bau_basis = entwurf_cache.laden(cache_kanal, kanal_pfad, festes_thema)
        if bau_basis:
            print('Geprueften Entwurf aus vorherigem Lauf fortsetzen; keine neue Skriptanfrage')
        else:
            # Vorab geschriebenes, geprueftes Skript (vorrat.py, nachts) - spart die Skriptphase.
            import vorrat
            bau_basis = vorrat.nehmen(kanal_pfad, festes_thema)
    ausstehende_korrektur = None  # auch nach einem Ausfall der Video-Pruefung
    bericht = {'id': os.environ.get('GITHUB_RUN_ID') or uuid.uuid4().hex,
               'kanal': kanal, 'datum': budget.heute(), 'runden': [], 'status': 'offen'}
    if trend:
        bericht['trendcheck'] = trend['grund']
    def protokoll(status):
        bericht['status'] = status
        bericht['grund'] = letzter_grund if status not in ('gesendet', 'pilot_bestanden') else ''
        bericht['sekunden'] = round(time.monotonic() - start, 1)
        aus = Path('ausgabe')
        aus.mkdir(exist_ok=True)
        try:
            import texte
            bericht['upload_titel'] = texte.upload_titel(
                json.loads((aus / 'skript.json').read_text(encoding='utf-8')),
                datetime.date.fromisoformat(bericht['datum']))
        except (OSError, ValueError, KeyError):
            pass
        (aus / 'bericht.json').write_text(json.dumps(bericht, indent=2, ensure_ascii=False), encoding='utf-8')
        pfad = Path('verlauf/messungen') / f'{kanal}.json'
        pfad.parent.mkdir(parents=True, exist_ok=True)
        liste = json.loads(pfad.read_text(encoding='utf-8')) if pfad.exists() else []
        liste = [e for e in liste if e.get('id') != bericht['id']]
        pfad.write_text(json.dumps((liste + [bericht])[-60:], indent=2, ensure_ascii=False), encoding='utf-8')
    # Neuer Versuch nur, wenn er noch sicher ins Zeitbudget passt
    while versuch < VERSUCHE_MAX + weiter_gekommen and (versuch == 0 or time.monotonic()
            + (KORREKTUR_S if basis or bau_basis else VERSUCH_S) <= arbeit_ende):
        versuch += 1
        ordner = Path(f'versuch{versuch}')
        shutil.rmtree(ordner, ignore_errors=True)
        rundenstart = time.monotonic()
        plan = None
        runde = {'runde': versuch, 'art': 'korrektur' if basis else 'produktion'}
        bericht['runden'].append(runde)
        phase = 'Skript'
        fortschritt.setzen(ordner=ordner, phase=phase, versuch=versuch, basis=bau_basis)
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
                                  + min(skriptfrist, max(0, arbeit_ende - time.monotonic()) * .4))
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
                                'Skriptqualitaet unter Freigabe' if r == 3 else
                                'Textanbieter voruebergehend gesperrt' if r == 4 else
                                'KI-Auftrag zu gross' if r == 5 else f'Skript fehlgeschlagen (Code {r})')
                if r in (1, 4, 5) and (ordner / 'skriptfehler.json').exists():
                    letzter_grund = json.loads((ordner / 'skriptfehler.json').read_text(encoding='utf-8')).get(
                        'grund', letzter_grund)
                if r == 4:
                    # Nutzerwunsch 21.10.2026: „Wenn kostenloses Kontingent fehlt, soll es das auch sagen."
                    # Der Rohgrund (z. B. HTTP 429 / Sperrfrist) allein war fuer ihn nicht als Kontingent lesbar.
                    letzter_grund = 'Kostenloses KI-Kontingent aufgebraucht (Anbieter gesperrt): ' + letzter_grund
                    if os.environ.get('CF_RESERVE_AUS') == '1':
                        letzter_grund += ' - kostenpflichtig weiter mit „start ki bezahlt" bzw. „start business bezahlt"'
                print(f'Versuch {versuch}: {letzter_grund}')
                runde['status'] = 'skriptfehler'
                runde.update(exitcode=r, grund=letzter_grund)
                if basis:
                    break
                if (ordner / 'skript.json').exists():
                    abgelehnt = json.loads((ordner / 'skript.json').read_text(encoding='utf-8'))
                    runde.update(sperrgruende=skript_gruende(abgelehnt),
                                 story_note=(abgelehnt.get('story') or {}).get('note'),
                                 story_schwaechen=[str(w)[:300] for w in
                                                   ((abgelehnt.get('story') or {}).get('schwaechen') or [])[:5]],
                                 skript_probleme=abgelehnt.get('pruefung', {}).get('probleme', []))
                    # Naechster Durchgang dieses Laufs kennt die Schwaechen (kein KI-Aufruf noetig).
                    heute_schwaechen.extend(runde['sperrgruende'][:2] + runde['story_schwaechen'][:3])
                    heute_pfad.write_text(json.dumps(heute_schwaechen[-8:], ensure_ascii=False), encoding='utf-8')
                    os.environ['CF_HEUTE_SCHWAECHEN'] = str(heute_pfad.resolve())
                    verlauf_eintragen(kanal, abgelehnt,
                                      'faktenpruefung' if r == 2 else 'skriptqualitaet' if r == 3 else 'skriptfehler', None,
                                      grund='; '.join((runde['sperrgruende'] or [])[:2] + runde['skript_probleme'][:2]))
                if r in (4, 5):
                    runde['status'] = 'anbieterpause' if r == 4 else 'auftragsfehler'
                    # GEMESSEN 22.10.2026 (Lauf 39810452976): Gemini 503 + Zeitlimit, der Groq-Ersatz war zu klein
                    # (Code 5) -> KI ohne Video nach 30 s. Eine kurze Gemini-Sperre einmal abwarten, wie im Bau.
                    warte = kurze_anbieterpause() if not anbieter_gewartet else None
                    if warte and arbeit_ende - time.monotonic() > warte + ANBIETER_REST_S:
                        anbieter_gewartet = True
                        print(f'Gemini kurz ueberlastet - Skript in {round(warte)} s erneut', flush=True)
                        time.sleep(warte)
                        continue
                    break  # Eine bekannte Kontingentsperre nicht durch neue Entwuerfe wiederholen.
                if entwurf:
                    break  # Eine gesperrte feste Vorlage nicht unveraendert erneut pruefen.
                if r in (2, 3) and trend and aus_warteschlange and thema:
                    trend_fehlschlaege += 1
                    if trend_fehlschlaege >= 2:
                        # GEMESSEN 29.10.2026 (Business 40953284925, DoorDash): Trend wegen eines Vergleichs in den
                        # News, die Wikipedia-Geschichte eine Chronik aus Kaeufen und Klagen - fuenf Versuche Story
                        # 4-7/10, kein Video. Nach zwei Sperren das naechste Nutzerthema bzw. freie Wahl.
                        ersatz = themen.nehmen(kanal)
                        print(f'Trendthema {thema} zweimal gesperrt - '
                              + (f'Thema aus der Warteschlange: {ersatz}' if ersatz else 'freie Wahl'), flush=True)
                        thema = festes_thema = ersatz or ''
                        trend = None
                        os.environ.pop('CF_TRENDGRUND', None)  # bericht['trendcheck'] bleibt: zaehlt fuer heute_gescheitert
                continue
            skript = json.loads((ordner / 'skript.json').read_text(encoding='utf-8'))
            skriptfehler = skript_gruende(skript)
            # GEMESSEN 21.10.2026: frei gewaehlt schrieb Claude "Ford Motor Company", geliefert schon am 18.10.
            # (Telegram 702) - die Liste frueherer Themen im Auftrag ist nur eine Bitte. Harte Sperre hier.
            # 21.10.2026 Nutzer: nach 60 Tagen mit neuem Blickwinkel wieder erlaubt (themen.wiederholung_gesperrt).
            gesperrt = not festes_thema and themen.wiederholung_gesperrt(kanal, skript.get('thema'), skript.get('titel'))
            if isinstance(gesperrt, str):
                skriptfehler = skriptfehler + [f'Thema schon geliefert: {skript.get("thema")} ({gesperrt}) - '
                                               'anderes Thema waehlen']
            if skriptfehler:
                letzter_grund = '; '.join(skriptfehler)
                runde.update(status='skriptqualitaet', sperrgruende=skriptfehler)
                verlauf_eintragen(kanal, skript, 'skriptqualitaet', None, grund=letzter_grund)
                if basis:
                    break
                continue
            runde['skript_s'] = round(time.monotonic() - rundenstart, 1)
            phase = 'Videobau'
            fortschritt.setzen(phase=phase, basis=bau_basis)
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
                try:
                    detail = (ordner / 'baufehler.txt').read_text(encoding='utf-8').strip()
                    (ordner / 'baufehler.txt').unlink()
                except OSError:
                    detail = ''
                if detail and not kontingent_leer:
                    letzter_grund = f'Videobau fehlgeschlagen ({detail[:160]})'
                print(f'Versuch {versuch}: {letzter_grund}')
                runde['baufehler'] = detail or letzter_grund
                verlauf_eintragen(kanal, skript, 'baufehler', None, grund=detail or letzter_grund)
                runde['status'] = 'baufehler'
                if b in (4, 5):
                    runde['status'] = 'anbieterpause' if b == 4 else 'auftragsfehler'
                    warte = kurze_anbieterpause() if b == 4 and not anbieter_gewartet else None
                    if warte and arbeit_ende - time.monotonic() > warte + ANBIETER_REST_S:
                        # GEMESSEN 22.10.2026: Gemini 503/Zeitlimit (Sperren 1-5 Min.) beendete beide Kanaele
                        # fuer Stunden. Eine kurze Ueberlast abwarten, dann mit demselben Teilbau weiter.
                        anbieter_gewartet = True
                        print(f'Gemini kurz ueberlastet - Bau in {round(warte)} s fortsetzen', flush=True)
                        time.sleep(warte)
                        bau_basis = ordner
                        continue
                    break  # Bekannte Anbietersperre gilt auch fuer die Bildplanung.
                if basis or kontingent_leer:
                    break
                # GEMESSEN 17.10.2026 (Langvideo Coca-Cola, Run 39040006644): Einstellung 58 scheiterte zweimal
                # -> ganzer Bildplan verworfen -> 57 fertige Bilder weg, Neubau ab 0, Budget aufgebraucht.
                # Neu planen nur, wenn es frueh haengt (wie gemessen bei Einstellung 1) - sonst Fortschritt behalten.
                if detail and detail == letzter_baufehler and einstellung_nr(detail) < PLAN_NEU_BIS:
                    # GEMESSEN 10.10.2026 (Tageslauf 38037738527): 5x „Einstellung 1: kein passendes
                    # Hauptbild" - der zwischengespeicherte Bildplan schickte jedes Mal dieselbe
                    # aussichtslose Szene. Gleicher Fehler zweimal -> Bildplan neu (Stimme bleibt).
                    bildplan_verwerfen(ordner)
                if einstellung_nr(detail) > einstellung_nr(letzter_baufehler) >= 0 \
                        and weiter_gekommen < WEITER_MAX:
                    weiter_gekommen += 1
                letzter_baufehler = detail
                bau_basis = ordner
                continue
            bau_basis = None
            (ordner / 'kritik.json').unlink(missing_ok=True)
            phase = 'Video-Pruefung'
            fortschritt.setzen(phase=phase)
            pruef_start = time.monotonic()
            def kritik_lauf():
                (ordner / 'kritik.json').unlink(missing_ok=True)
                return schritt(['fabrik/kritik.py', str(ordner / 'short.mp4'), str(ordner / 'skript.json'),
                                str(ordner / 'kritik.json')], arbeit_ende)
            k = kritik_lauf()
            # GEMESSEN 16.10.2026 (Lauf 38873412464, KI): Video fertig gebaut, dann meldeten alle Gemini-
            # Modelle 503 (Google ueberlastet) -> keine einzige Note, das Video wurde verworfen. Ein kurzer
            # Ausfall ist kein Qualitaetsurteil: dasselbe Video spaeter erneut pruefen. Schon gepruefte
            # Einzelbilder kommen aus dem Cache; Gates und Schwellen bleiben unveraendert.
            for warte in PRUEF_WIEDERHOLUNG_S:
                if not pruefung_ausgefallen(k, ordner / 'kritik.json') \
                        or arbeit_ende - time.monotonic() < warte + PRUEF_RESERVE_S:
                    break
                print(f'Pruefdienst ausgefallen - dasselbe Video in {warte} s erneut pruefen')
                import stoerung
                stoerung.melden('videopruefung', 'Die Videopruefung fiel aus (Dienst antwortet nicht).',
                                f'Das fertige Video wird in {warte // 60} Min. erneut geprueft, nicht neu gebaut.')
                time.sleep(warte)
                k = kritik_lauf()
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
            if phase == 'Skript' and not basis and not entwurf:
                # GEMESSEN 29.10.2026: nach dem Skript-Zeitlimit endete der Lauf mit ueber 60 Min. Restbudget.
                # Der naechste Versuch setzt die gesicherte Fassung fort (skript_entwurf); die Schleife prueft die Zeit.
                continue
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
            if (ordner / 'skript.json').exists():
                try:
                    entwurf_cache.sichern(cache_kanal, kanal_pfad, festes_thema, ordner)
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
        # Nutzerentscheidung 15.10.2026: auch ein NUR an der Bildpruefung gescheitertes Video geht als
        # markierter Entwurf zum Nutzer (heute von Hand fuer Airbnb/Fincept; beide fand er "ok").
        kandidat_rang = ((1, note or 0) if gruende and nur_ki_geschmack(gruende) and (note or 0) >= ENTWURF_MIN
                         else (0, -sum(1 for g in gruende if str(g).startswith('Einstellung ')))
                         if gruende and nur_bildbezug(gruende) else None)
        if kandidat_rang is not None and (entwurf_rang is None or kandidat_rang > entwurf_rang):
            entwurf_rang = kandidat_rang
            # Fertig gebaut, nur an KI-Geschmack gescheitert: als markierter Entwurf merken.
            entwurf_versand = Path('entwurf-kandidat')
            shutil.rmtree(entwurf_versand, ignore_errors=True)
            shutil.copytree(ordner, entwurf_versand)
            entwurf_kandidat = (note, entwurf_versand, kritik)
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
            # Technik-Messwerte (Dauer, Lautheit, Codec) sind keine Redaktionsregeln.
            # GEMESSEN 10.10.2026 (Pilot 38058541190): aus „unter 61 s" lernte das Regelbuch
            # „Shorts mindestens 61 s" - gegen die Nutzerentscheidung 35-45 s.
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

    entwurf = False
    if bester is None and entwurf_kandidat is not None and os.environ.get('CF_PILOT') != '1':
        # Nutzer entscheidet (08.10.2026): fertig gebautes Video mit KI-Note >= 5 als Entwurf.
        bester, entwurf = entwurf_kandidat, True
        print('Kein freigegebenes Video - markierter Entwurf geht zur Nutzerentscheidung '
              + (f'(KI-Note {bester[0]}/10)' if entwurf_rang[0] else f'({-entwurf_rang[1]} Bilder beanstandet)'))
    if bester is None:
        # Den letzten Versuch fuer die Fehlersuche als Artefakt behalten.
        if versuch:
            if not (ordner / 'short.mp4').exists():
                # Eine erfolglose Korrektur legt einen leeren Ordner an; das echte fehlerhafte
                # MP4/ASR/Pruefprotokoll aus dem vorherigen Versuch muss erhalten bleiben.
                ordner = next((Path(f'versuch{i}') for i in range(versuch-1,0,-1)
                               if Path(f'versuch{i}/short.mp4').exists()),ordner)
            if ordner.exists():
                aus = Path('ausgabe')
                shutil.rmtree(aus, ignore_errors=True)
                shutil.copytree(ordner, aus)
        aus_fehlern_lernen(kanal, bericht['runden'], min(start + frei, time.monotonic() + 90))
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
    if skript.get('videoformat') == 'lang':
        # Langvideo braucht ein Vorschaubild (Nutzerauftrag 09.10.2026); best effort, hoechstens 6 Min.
        try:
            schritt(['fabrik/vorschaubild.py', str(aus / 'skript.json'), str(aus / 'thumbnail.jpg')],
                    min(start + frei, time.monotonic() + 360))
        except (subprocess.TimeoutExpired, OSError):
            print('Vorschaubild nicht erstellt - Video wird trotzdem zugestellt')
    if os.environ.get('CF_PILOT') == '1':
        verlauf_eintragen(kanal, skript, 'pilot', note, messung.get('abschnitte_s'), messung)
        protokoll('pilot_bestanden')
        return 0
    try:
        if entwurf:
            os.environ['CF_ENTWURF'] = '1'
        code = schritt(['fabrik/freigabe.py', str(aus / 'skript.json'), str(aus / 'short.mp4')], start + frei)
    except (subprocess.TimeoutExpired, OSError):
        protokoll('zustellfehler')
        raise
    if code:
        protokoll('zustellfehler')
        raise RuntimeError(f'Telegram-Zustellung fehlgeschlagen (Code {code})')
    verlauf_eintragen(kanal, skript, 'gesendet', note, messung.get('abschnitte_s'),
                      dict(messung, entwurf=True) if entwurf else messung)
    entwurf_cache.erledigen(cache_kanal)
    import vorrat
    vorrat.erledigen(kanal, skript)
    if aus_warteschlange and festes_thema:
        themen.erledigen(kanal, festes_thema)
    protokoll('gesendet')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '',
                  sys.argv[3] if len(sys.argv) > 3 else ''))
