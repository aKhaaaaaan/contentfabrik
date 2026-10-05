"""Gemeinsames Tagesbudget aller Zeitfenster eines Kanals (UTC).

Vor Arbeitsbeginn reservieren; bei normalem Ende ungenutzte Zeit erstatten.
Ein abgebrochener Prozess behaelt seine Reservierung, statt im naechsten
Zeitfenster erneut das volle Budget zu erhalten. Workflows laufen seriell.
"""
import datetime
import json
import math
from pathlib import Path

ORDNER = Path('verlauf/budget')


def heute():
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def laden(kanal):
    p = ORDNER / f'{kanal}.json'
    d = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    if d.get('datum') != heute():
        return {'datum': heute(), 'sekunden': 0, 'laeufe': 0}
    sekunden = d.get('sekunden')
    if isinstance(sekunden, bool) or not isinstance(sekunden, (int, float)) \
            or not math.isfinite(sekunden) or sekunden < 0:
        raise ValueError('Gespeichertes Tagesbudget ist ungueltig')
    return d


def speichern(kanal, d):
    ORDNER.mkdir(parents=True, exist_ok=True)
    p = ORDNER / f'{kanal}.json'
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(d, indent=2) + '\n', encoding='utf-8')
    tmp.replace(p)


def rest(kanal, grenze):
    return max(0, grenze - laden(kanal)['sekunden'])


def reservieren(kanal, grenze):
    d = laden(kanal)
    frei = max(0, grenze - d['sekunden'])
    vorher = d['sekunden']
    d.update(sekunden=vorher + frei, laeufe=d.get('laeufe', 0) + 1)
    speichern(kanal, d)
    return frei, vorher, d


def abschliessen(kanal, reservierung, verbrauch):
    frei, vorher, d = reservierung
    # Auch beim UTC-Tageswechsel wird der Tag der Reservierung abgerechnet.
    d['sekunden'] = round(vorher + min(frei, max(0, verbrauch)), 3)
    speichern(kanal, d)
