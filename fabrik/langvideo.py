"""Woechentliches Business-Langvideo (8-10 Min.): faellig? welches Thema?

Nutzerauftrag 16.10.2026: Langvideos zahlen bei Business/Finanzen etwa hundertmal mehr je Aufruf als Shorts
(Shorts ~0.03-0.25 $, lang ~10-25 $ je 1.000 laut vidIQ/Outlierkit) und nur Langvideos zaehlen fuer die
4.000 Wiedergabestunden des Partnerprogramms. Einmal pro Woche, Qualitaet vor Menge.
Thema: die GANZE Geschichte einer Firma, deren Short in den letzten Tagen lief - der Short wird so zur
Entdeckung fuer das Langvideo (Verweis setzt der Nutzer in YouTube Studio). Kein Thema -> freie Wahl.

Nutzer 22.10.2026: Langvideos fuer JEDEN Kanal (zuerst Business + KI), an verschiedenen Tagen gebaut, damit das
kostenlose Kontingent fuer Shorts und Langvideo reicht; beide liegen spaetestens Sonntag bereit (Hochladen nur YouTube).
Welche Kanaele, an welchen Tagen: formate/<kanal>.json, Feld lang_tage (z. B. ["fr", "sa"] - erster Tag Bau,
weitere Ersatz). Ein neuer Kanal braucht nur seine Format-Datei.

Aufruf: python fabrik/langvideo.py vorpruefung   (schreibt faellig/liste nach GITHUB_OUTPUT)
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

KANAL = 'business-origin-stories'
NAME = 'Business Origin Stories'
ABSTAND_TAGE = 3       # Nutzer 13.11.2026: 3 statt 6 Tage (nachgeholtes So-Langvideo sperrte den naechsten Fr)
SUCHFENSTER_TAGE = 8   # Shorts der letzten gut eine Woche als Themenquelle


def _norm(t):
    return re.sub(r'\W+', ' ', str(t)).strip().lower()


def ist_lang(eintrag):
    return (eintrag.get('einstellungen') or {}).get('videoformat') == 'lang'


def faellig(verlauf, heute, kanal=None):
    """Kein gesendetes Langvideo in den letzten ABSTAND_TAGE Tagen - und (mit kanal) keins seit dem ersten
    lang_tag dieser Planungswoche: mit 3 statt 6 Tagen haette ein Freitags-Langvideo sonst am Nachhol-Montag ein
    zweites ausgeloest (doppeltes Budget)."""
    grenze = (heute - datetime.timedelta(days=ABSTAND_TAGE)).isoformat()
    tage = formate().get(kanal) if kanal else None
    start = (heute - datetime.timedelta(days=(heute.weekday() - TAGE[tage[0]]) % 7)).isoformat() if tage else '9'
    return not any(ist_lang(e) and e.get('status') == 'gesendet'
                   and (str(e.get('datum', '')) > grenze or str(e.get('datum', ''))[:10] >= start)
                   for e in verlauf)


LANG_MIN_ZEICHEN = 12000  # dieselbe Grenze wie skript.py ("12000 if lang"), Test haelt beide gleich


def quelle_reicht(t, kanal=KANAL):
    """Traegt die Wikipedia-Geschichte ein Langvideo? None vom Abruf (429/Netz) zaehlt als ja - der Lauf
    versucht es dann selbst; verworfen wird nur ein nachweislich zu kurzer Artikel."""
    import themen
    import trends
    q = trends.wikipedia(themen.details(kanal, t).get('wikipedia') or t, grenze=30000)
    # GEMESSEN 06.11.2026 (Lauf 42219418311): "Rivian Origin Story" gibt es nicht als Artikel -> None -> "reicht";
    # skript.py fand dann "Rivian" mit 11.575 Zeichen, zu kurz, und fiel auf freie Wahl. Firmennamen nachschlagen.
    name = artikelname(t)
    if q is None and name != t:
        q = trends.wikipedia(name, grenze=30000)
    return q is None or len(q['text']) >= LANG_MIN_ZEICHEN


def artikelname(t):
    """Short-Thema -> Firmenname: "Rivian Origin Story" -> "Rivian", "Tesla: How ..." -> "Tesla"."""
    return re.sub(r'\s+origin\s+story$', '', _begriff(t), flags=re.I).strip() or str(t)


def quellen_da(t):
    """KI-Kanal (nur_quellen): findet die Themenrecherche Belege? skript.py schreibt ohne sie nichts.
    GEMESSEN 31.10.2026 (Lauf 41202120654): Langvideo „Claude Projects for client work" - der Short war frei
    gewaehlt und hatte seine Quellen aus dem Kanal-Schwerpunkt; mit festem Thema 0 Quellen, fuenfmal Abbruch."""
    import trends
    return bool(trends.thema_recherche(t))


def thema(verlauf, geliefert, heute, name=NAME, reicht=None, rangfolge=None):
    """Short der letzten Tage (nicht von heute), dessen Thema noch kein Langvideo hatte.
    reicht(thema): optionale Quellenpruefung; ungeeignete Themen werden uebersprungen.
    rangfolge(themen): optionale Trendbewertung; ohne sie oder ohne Trend gewinnt der juengste."""
    geeignet = kandidaten(verlauf, geliefert, heute, name, reicht)
    return _rangfolge_waehlen(geeignet, rangfolge) if geeignet else ''


def kandidaten(verlauf, geliefert, heute, name=NAME, reicht=None):
    """Geeignete Short-Themen fuer ein Langvideo, juengster zuerst (hoechstens TREND_KANDIDATEN)."""
    # GEMESSEN 17.10.2026: nur GELIEFERTE Langvideos zaehlen - zwei gescheiterte Coca-Cola-Versuche
    # (Skriptfrist, Bauversuche) liessen den Neustart Airbnb waehlen; der fast fertige Teilbau
    # (Skript, Stimme, 53/84 Bilder) waere verloren gewesen.
    schon_lang = {_norm(e.get('thema')) for e in verlauf if ist_lang(e) and e.get('status') == 'gesendet'}
    ab = (heute - datetime.timedelta(days=SUCHFENSTER_TAGE)).isoformat()
    kandidaten = [e for e in verlauf
                  if e.get('status') == 'gesendet' and not ist_lang(e)
                  and ab <= str(e.get('datum', '')) < heute.isoformat()
                  and _norm(e.get('thema')) not in schon_lang]
    # Vom Nutzer abgelehnte Themen nicht ausbauen - aber nur, wenn ALLE Zustellungen abgelehnt sind
    # (16.10.2026: das doppelte Airbnb-Video abzulehnen heisst nicht, dass Airbnb schlecht ankam).
    import lernen
    zustellungen = {}
    for g in geliefert:
        if g.get('kanal') == name and g.get('video_sha256'):
            zustellungen.setdefault(_norm(g.get('thema')), []).append(lernen.abgelehnt(g['video_sha256']))
    kandidaten = [e for e in kandidaten if not all(zustellungen.get(_norm(e.get('thema')), [False]))]
    # GEMESSEN 24.10.2026 (Lauf 40094873316): Moderna hat nur 7.650 Zeichen Geschichte, skript.py verlangt
    # fuer lang 12.000 - das feste Thema scheiterte fuenfmal identisch in 2 Minuten, kein Langvideo.
    # Dann den naechstjuengeren Short nehmen, notfalls freie Wahl.
    geeignet, gesehen = [], set()
    for _, e in sorted(enumerate(kandidaten), key=lambda x: (x[1]['datum'], x[0]), reverse=True):
        if _norm(e['thema']) in gesehen or len(geeignet) >= TREND_KANDIDATEN:
            continue
        gesehen.add(_norm(e['thema']))
        if reicht is None or reicht(e['thema']):
            geeignet.append(e['thema'])
        else:
            print('Langvideo: Quelle zu kurz fuer', e['thema'], '- naechster Short')
    return geeignet


def _rangfolge_waehlen(geeignet, rangfolge):
    # Nutzer 24.10.2026: "die Themen muessen auch fuer Langvideos heiss sein" - Moderna war am Tag seines
    # Shorts ein Trend, am Langvideo-Tag fuehrte Tesla (YouTube 622x, Google News). Unter den geeigneten
    # Shorts gewinnt der heute staerkste YouTube-/Google-Trend (gleiche Regel wie trendcheck.entscheiden);
    # ohne Trendsignal bleibt der juengste.
    if rangfolge and len(geeignet) > 1:
        try:
            bewertet = rangfolge(geeignet)
        except Exception as e:  # Trendquellen weg darf das Langvideo nicht verhindern
            print('Langvideo: Trend-Check nicht verfuegbar -', str(e)[:120])
            bewertet = []
        heiss = [k for k in bewertet if k['punkte'] >= SCHWELLE and k['stufe'] <= 1]
        if heiss:
            print(f"Langvideo nach Trend: {heiss[0]['thema']} ({heiss[0]['punkte']} Punkte)")
            return heiss[0]['thema']
        print('Langvideo: kein Short mit heutigem Trend - juengster')
    return geeignet[0]


TREND_KANDIDATEN = 5  # je YouTube-Suche 100 Einheiten Kontingent
SCHWELLE = 1.5        # = trendcheck.SCHWELLE (Test haelt beide gleich)


def _begriff(t):
    """Suchbegriff eines Short-Themas: "Tesla: How Funding Decisions..." -> "Tesla"."""
    return re.split(r':| - | – ', str(t))[0].strip() or str(t)


def trend_rangfolge(themen_liste, kanal=KANAL):
    """[{thema, punkte, stufe}] nach heutigem Trend, staerkster zuerst (trendcheck.bewerten)."""
    import themen
    import trendcheck
    wiki = _profil(kanal).get('quelle') == 'wikipedia'
    liste = [{'thema': t, 'begriff': _begriff(t), 'eigen': False,
              'wikipedia': themen.details(kanal, t).get('wikipedia') or (_begriff(t) if wiki else None)}
             for t in themen_liste]
    google = trendcheck.google_heute('US', news=wiki)
    return trendcheck.bewerten(liste, google, kanal=kanal)


def vorpruefung(heute=None, eingabe='', kanal=KANAL):
    """(faellig, thema) fuer EINEN Kanal - ohne Wochentagspruefung (die macht plan())."""
    heute = heute or datetime.date.today()
    p = Path('verlauf') / f'{kanal}.json'
    verlauf = json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
    g = Path('verlauf/telegram-videos.json')
    geliefert = json.loads(g.read_text(encoding='utf-8')) if g.exists() else []
    if eingabe:
        return True, eingabe
    if not faellig(verlauf, heute, kanal):
        return False, ''
    # GEMESSEN 17.10.2026: der Sonntag haette Enron (neuester Short) gewaehlt, obwohl ein gepruefter
    # Coca-Cola-Entwurf samt Stimme bereitlag. Erst fertig bauen, was schon bezahlt/geprueft ist.
    # 06.11.2026 Nutzer ("nimm ein anderes Thema als Ford"): ein ausdrueckliches Langvideo-Thema aus der
    # Warteschlange (format 'lang') geht sogar dem offenen Entwurf und dem Vorrat-Skript vor.
    import themen
    eigen = themen.lang_nehmen(kanal)
    if eigen:
        return True, eigen
    offen = offener_entwurf(kanal)
    if offen:
        return True, offen
    # 04.11.2026: ein unabhaengig geprueftes Ersatzskript (Codex-Bruecke nach Claude-/Groq-Ausfall) hat Vorrang,
    # sonst waehlte der Ersatztermin ein anderes Thema und das fertige Skript bliebe liegen.
    import vorrat
    ersatz = vorrat.lang_thema(Path('formate') / f'{kanal}.json')
    if ersatz:
        return True, ersatz
    reicht = (lambda t: quelle_reicht(t, kanal)) if _profil(kanal).get('quelle') == 'wikipedia' else \
        (lambda t: quellen_da(t)) if _profil(kanal).get('nur_quellen') else None
    return True, thema(verlauf, geliefert, heute, _name(kanal), reicht, lambda l: trend_rangfolge(l, kanal))


def offener_entwurf(kanal=KANAL):
    """Thema eines noch gueltigen, geprueften Langvideo-Entwurfs ('' wenn keiner)."""
    import time
    import entwurf_cache
    meta, _ = entwurf_cache.pfade(f'{kanal}-lang')
    try:
        d = json.loads(meta.read_text(encoding='utf-8'))
        if 0 <= time.time() - d['erstellt'] <= entwurf_cache.TTL_LANG and d.get('thema_eingabe'):
            return str(d['thema_eingabe'])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return ''


TAGE = {'mo': 0, 'di': 1, 'mi': 2, 'do': 3, 'fr': 4, 'sa': 5, 'so': 6}


def _profil(kanal):
    try:
        return json.loads((Path('kanaele') / f'{kanal}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def _name(kanal):
    return _profil(kanal).get('name') or kanal


def formate(ordner=Path('formate')):
    """{kanal: lang_tage} aller Langvideo-Formate (Dateien mit '_' ausgenommen)."""
    aus = {}
    for p in sorted(Path(ordner).glob('*.json')):
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not p.name.startswith('_') and d.get('videoformat') == 'lang':
            aus[p.stem] = [t for t in d.get('lang_tage') or [] if t in TAGE]
    return aus


def plan(heute=None, eingabe='', kanal=''):
    """[{kanal, thema}] fuer heute. Zeitplan: nur Kanaele, deren lang_tage heute enthalten und die faellig sind
    (ein am ersten Tag geliefertes Langvideo sperrt den Ersatztag ueber ABSTAND_TAGE).
    Handstart (kanal gesetzt): genau dieser Kanal, ohne Wochentagspruefung."""
    heute = heute or datetime.date.today()
    if kanal:
        # Der Kanal landet ueber die Matrix in Shell-Befehlen und Dateipfaden des Workflows - nur bekannte
        # Langvideo-Formate zulassen (Tippfehler oder eingeschleuste Zeichen beim Handstart).
        if kanal not in formate():
            print('Unbekannter Langvideo-Kanal - nichts gestartet')
            return []
        ja, t = vorpruefung(heute, eingabe, kanal)
        return [{'kanal': kanal, 'thema': t}] if ja else []
    # Nutzer 06.11.2026: "nie beide Langvideos an einem Tag" - Business Fr, KI Sa, dazwischen Shorts. Business
    # scheiterte am Freitag, der Ersatz-Samstag waere mit dem KI-Langvideo zusammengefallen. Jetzt hoechstens EIN
    # Langvideo je Tag: der regulaere Kanal des Tages zuerst, ein verpasster holt am naechsten freien Tag nach.
    for k in anwaerter(heute):
        if not budget_frei(k, heute):
            print(f'Langvideo {k}: Tagesbudget verbraucht - naechster freier Tag')
            continue
        ja, t = vorpruefung(heute, '', k)
        if ja:
            return [{'kanal': k, 'thema': t}]
    return []


NACHHOLEN_TAGE = 3  # so viele Tage nach dem ersten lang_tag darf ein verpasstes Langvideo nachgeholt werden


def anwaerter(tag):
    """Kanaele, die an diesem Tag ein Langvideo bauen duerfen, Vorrang zuerst: der Kanal, dessen ERSTER lang_tag
    heute ist; danach der am laengsten ueberfaellige (Ersatztag oder Nachholen bis NACHHOLEN_TAGE)."""
    liste = []
    for k, tage in formate().items():
        nummern = [TAGE[t] for t in tage]
        if not nummern:
            continue
        seit = (tag.weekday() - nummern[0]) % 7
        if seit == 0:
            liste.append((0, k))
        elif tag.weekday() in nummern or seit <= NACHHOLEN_TAGE:
            liste.append((10 - seit, k))
    return [k for _, k in sorted(liste)]


def zuteilung(heute, tage=14):
    """{datum: kanal} - welcher Kanal an welchem Tag sein Langvideo baut (je Tag hoechstens einer), unter der
    Annahme, dass jeder Termin liefert. Grundlage fuer die Vorschau des Themen-Befehls."""
    verlaeufe = {}
    for k in formate():
        p = Path('verlauf') / f'{k}.json'
        verlaeufe[k] = json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
    aus, fertig = {}, set()
    for i in range(tage):
        d = heute + datetime.timedelta(days=i)
        for k in anwaerter(d):
            if k in fertig or not faellig(verlaeufe[k], d, k) or (d == heute and not budget_frei(k, d)):
                continue
            aus[d] = k
            fertig.add(k)
            break
    return aus


VORSCHAU = Path('verlauf/themenplan')


def vorschau(kanal, heute=None, reicht=None):
    """Was der Telegram-Befehl "Themen" zum Langvideo zeigt: naechster Termin, Ersatztag, fertiges Thema oder
    Kandidaten. Nutzer 06.11.2026: "Themen-Befehl praeziser, zum Beispiel Shorts und Long Themen".
    Ohne Trend-Check (100 YouTube-Einheiten je Thema) - den macht der Lauf am Termin."""
    heute = heute or datetime.date.today()
    p = Path('verlauf') / f'{kanal}.json'
    verlauf = json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
    g = Path('verlauf/telegram-videos.json')
    geliefert = json.loads(g.read_text(encoding='utf-8')) if g.exists() else []
    # Gleiche Regel wie plan(): je Tag hoechstens ein Langvideo (Nutzer 06.11.2026). Verbrauchtes Budget heute
    # schiebt auf den naechsten freien Tag (GEMESSEN 06.11. abends: Vorschau zeigte "Termin: heute").
    plan_tage = zuteilung(heute)
    termin = next((d for d, k in sorted(plan_tage.items()) if k == kanal), None)
    # Ersatztag = naechster Tag danach, an dem der Kanal darf und kein anderes Langvideo eingeplant ist
    ersatz = next((d for d in (termin + datetime.timedelta(days=i) for i in range(1, NACHHOLEN_TAGE + 1))
                   if kanal in anwaerter(d) and plan_tage.get(d) in (None, kanal)), None) if termin else None
    letzte = max((str(e.get('datum', '')) for e in verlauf if ist_lang(e) and e.get('status') == 'gesendet'),
                 default='')
    aus = {'kanal': kanal, 'erstellt': heute.isoformat(), 'termin': termin.isoformat() if termin else '',
           'ersatz': ersatz.isoformat() if ersatz else '', 'letztes_langvideo': letzte,
           'laenge_s': _lang_profil(kanal).get('laenge_s') or [], 'fest': '', 'fest_grund': '', 'kandidaten': [],
           'quellen_geprueft': reicht is not None}
    import themen
    import vorrat
    eigen = themen.lang_nehmen(kanal)
    offen = '' if eigen else offener_entwurf(kanal)
    ersatz_skript = '' if offen or eigen else vorrat.lang_thema(Path('formate') / f'{kanal}.json')
    if offen or eigen or ersatz_skript:
        aus.update(fest=eigen or offen or ersatz_skript,
                   fest_grund='dein Thema' if eigen else 'gepruefter Entwurf' if offen else 'fertiges Skript')
    elif termin:
        aus['kandidaten'] = kandidaten(verlauf, geliefert, termin, _name(kanal), reicht)
    return aus


def _lang_profil(kanal):
    try:
        return json.loads((Path('formate') / f'{kanal}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def budget_frei(kanal, heute):
    """Reicht das heutige Langvideo-Budget noch fuer einen Lauf? (gleiche Rechnung wie lauf.main)"""
    try:
        import budget
        import lauf
        if heute.isoformat() != budget.heute():
            return True
        grenze = lauf.tagesgrenze(f'lang-{kanal}', lauf.BUDGET_LANG_S)
        return budget.rest(f'lang-{kanal}', grenze) > lauf.SENDEN_S
    except Exception:
        return True


def vorschau_schreiben(heute=None):
    VORSCHAU.mkdir(parents=True, exist_ok=True)
    for kanal in formate():
        try:
            reicht = (lambda t, k=kanal: quelle_reicht(t, k)) if _profil(kanal).get('quelle') == 'wikipedia' else None
            v = vorschau(kanal, heute, reicht)
        except Exception as e:  # die Vorschau darf keinen Lauf stoeren
            print('Langvideo-Vorschau fehlgeschlagen:', kanal, str(e)[:160])
            continue
        (VORSCHAU / f'lang-{kanal}.json').write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding='utf-8')
        print('Langvideo-Vorschau:', kanal, v['termin'], v['fest'] or v['kandidaten'])


if __name__ == '__main__' and sys.argv[1:] == ['vorschau']:
    vorschau_schreiben()

if __name__ == '__main__' and sys.argv[1:] == ['vorpruefung']:
    liste = plan(eingabe=os.environ.get('EINGABE', '').strip(), kanal=os.environ.get('LANG_KANAL', '').strip())
    for x in liste:
        print('Langvideo faellig:', x['kanal'], '| Thema:', x['thema'] or '(freie Wahl)')
    if not liste:
        print('Heute kein Langvideo faellig')
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
        f.write(f'faellig={"ja" if liste else "nein"}\n')
        f.write(f'liste={json.dumps(liste, ensure_ascii=True)}\n')
