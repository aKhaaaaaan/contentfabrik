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


def thema(verlauf, geliefert, heute, name=NAME):
    """Juengster Short der letzten Tage (nicht von heute), dessen Thema noch kein Langvideo hatte."""
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
    if not kandidaten:
        return ''
    return max(enumerate(kandidaten), key=lambda x: (x[1]['datum'], x[0]))[1]['thema']


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
    return True, offen or thema(verlauf, geliefert, heute, _name(kanal))


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


def _name(kanal):
    try:
        return json.loads((Path('kanaele') / f'{kanal}.json').read_text(encoding='utf-8')).get('name') or kanal
    except (OSError, ValueError):
        return kanal


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
