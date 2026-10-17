"""Woechentliches Business-Langvideo (8-10 Min.): faellig? welches Thema?

Nutzerauftrag 16.10.2026: Langvideos zahlen bei Business/Finanzen etwa hundertmal mehr je Aufruf als Shorts
(Shorts ~0.03-0.25 $, lang ~10-25 $ je 1.000 laut vidIQ/Outlierkit) und nur Langvideos zaehlen fuer die
4.000 Wiedergabestunden des Partnerprogramms. Einmal pro Woche, Qualitaet vor Menge.
Thema: die GANZE Geschichte einer Firma, deren Short in den letzten Tagen lief - der Short wird so zur
Entdeckung fuer das Langvideo (Verweis setzt der Nutzer in YouTube Studio). Kein Thema -> freie Wahl.

Aufruf: python fabrik/langvideo.py vorpruefung   (schreibt faellig/thema nach GITHUB_OUTPUT)
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


def thema(verlauf, geliefert, heute):
    """Juengster Business-Short der letzten Tage (nicht von heute), dessen Thema noch kein Langvideo hatte."""
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
        if g.get('kanal') == NAME and g.get('video_sha256'):
            zustellungen.setdefault(_norm(g.get('thema')), []).append(lernen.abgelehnt(g['video_sha256']))
    kandidaten = [e for e in kandidaten if not all(zustellungen.get(_norm(e.get('thema')), [False]))]
    if not kandidaten:
        return ''
    return max(enumerate(kandidaten), key=lambda x: (x[1]['datum'], x[0]))[1]['thema']


def vorpruefung(heute=None, eingabe=''):
    heute = heute or datetime.date.today()
    p = Path('verlauf') / f'{KANAL}.json'
    verlauf = json.loads(p.read_text(encoding='utf-8')) if p.exists() else []
    g = Path('verlauf/telegram-videos.json')
    geliefert = json.loads(g.read_text(encoding='utf-8')) if g.exists() else []
    if eingabe:
        return True, eingabe
    if not faellig(verlauf, heute):
        return False, ''
    # GEMESSEN 17.10.2026: der Sonntag haette Enron (neuester Short) gewaehlt, obwohl ein gepruefter
    # Coca-Cola-Entwurf samt Stimme bereitlag. Erst fertig bauen, was schon bezahlt/geprueft ist.
    offen = offener_entwurf()
    return True, offen or thema(verlauf, geliefert, heute)


def offener_entwurf():
    """Thema eines noch gueltigen, geprueften Langvideo-Entwurfs ('' wenn keiner)."""
    import time
    import entwurf_cache
    meta, _ = entwurf_cache.pfade(f'{KANAL}-lang')
    try:
        d = json.loads(meta.read_text(encoding='utf-8'))
        if 0 <= time.time() - d['erstellt'] <= entwurf_cache.TTL_LANG and d.get('thema_eingabe'):
            return str(d['thema_eingabe'])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return ''


if __name__ == '__main__' and sys.argv[1:] == ['vorpruefung']:
    ja, t = vorpruefung(eingabe=os.environ.get('EINGABE', '').strip())
    print('Langvideo faellig:', ja, '| Thema:', t or '(freie Wahl)')
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
        f.write(f'faellig={"ja" if ja else "nein"}\n')
        f.write(f'thema={t.replace(chr(10), " ")}\n')
