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
ABSTAND_TAGE = 6       # hoechstens ein Langvideo je Woche
SUCHFENSTER_TAGE = 8   # Shorts der letzten gut eine Woche als Themenquelle


def _norm(t):
    return re.sub(r'\W+', ' ', str(t)).strip().lower()


def ist_lang(eintrag):
    return (eintrag.get('einstellungen') or {}).get('videoformat') == 'lang'


def faellig(verlauf, heute):
    """Kein gesendetes Langvideo in den letzten ABSTAND_TAGE Tagen."""
    grenze = (heute - datetime.timedelta(days=ABSTAND_TAGE)).isoformat()
    return not any(ist_lang(e) and e.get('status') == 'gesendet' and str(e.get('datum', '')) > grenze
                   for e in verlauf)


LANG_MIN_ZEICHEN = 12000  # dieselbe Grenze wie skript.py ("12000 if lang"), Test haelt beide gleich


def quelle_reicht(t, kanal=KANAL):
    """Traegt die Wikipedia-Geschichte ein Langvideo? None vom Abruf (429/Netz) zaehlt als ja - der Lauf
    versucht es dann selbst; verworfen wird nur ein nachweislich zu kurzer Artikel."""
    import themen
    import trends
    q = trends.wikipedia(themen.details(kanal, t).get('wikipedia') or t, grenze=30000)
    return q is None or len(q['text']) >= LANG_MIN_ZEICHEN


def thema(verlauf, geliefert, heute, name=NAME, reicht=None, rangfolge=None):
    """Short der letzten Tage (nicht von heute), dessen Thema noch kein Langvideo hatte.
    reicht(thema): optionale Quellenpruefung; ungeeignete Themen werden uebersprungen.
    rangfolge(themen): optionale Trendbewertung; ohne sie oder ohne Trend gewinnt der juengste."""
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
    if not geeignet:
        return ''
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
    if not faellig(verlauf, heute):
        return False, ''
    # GEMESSEN 17.10.2026: der Sonntag haette Enron (neuester Short) gewaehlt, obwohl ein gepruefter
    # Coca-Cola-Entwurf samt Stimme bereitlag. Erst fertig bauen, was schon bezahlt/geprueft ist.
    offen = offener_entwurf(kanal)
    if offen:
        return True, offen
    reicht = (lambda t: quelle_reicht(t, kanal)) if _profil(kanal).get('quelle') == 'wikipedia' else None
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
    aus = []
    for k, tage in formate().items():
        if heute.weekday() in {TAGE[t] for t in tage}:
            ja, t = vorpruefung(heute, '', k)
            if ja:
                aus.append({'kanal': k, 'thema': t})
    return aus


if __name__ == '__main__' and sys.argv[1:] == ['vorpruefung']:
    liste = plan(eingabe=os.environ.get('EINGABE', '').strip(), kanal=os.environ.get('LANG_KANAL', '').strip())
    for x in liste:
        print('Langvideo faellig:', x['kanal'], '| Thema:', x['thema'] or '(freie Wahl)')
    if not liste:
        print('Heute kein Langvideo faellig')
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
        f.write(f'faellig={"ja" if liste else "nein"}\n')
        f.write(f'liste={json.dumps(liste, ensure_ascii=True)}\n')
