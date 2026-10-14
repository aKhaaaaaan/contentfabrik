"""Gemeinsames Tagesbudget aller Zeitfenster eines Kanals (UTC).

Vor Arbeitsbeginn reservieren; bei normalem Ende ungenutzte Zeit erstatten.
Ein abgebrochener Prozess behaelt seine Reservierung, statt im naechsten
Zeitfenster erneut das volle Budget zu erhalten. Workflows laufen seriell.
"""
import datetime
import json
import math
import os
import re
import sys
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
    run = os.environ.get('GITHUB_RUN_ID','')
    if run.isdigit():
        p = reservierungsdatei(kanal)
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps({'run':run,'datum':d['datum'],'vorher':vorher,'frei':frei,
                                'laeufe':d['laeufe'],
                                'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+'\n')
    return frei, vorher, d


def abschliessen(kanal, reservierung, verbrauch):
    frei, vorher, d = reservierung
    # Auch beim UTC-Tageswechsel wird der Tag der Reservierung abgerechnet.
    d['sekunden'] = round(vorher + min(frei, max(0, verbrauch)), 3)
    speichern(kanal, d)
    reservierungsdatei(kanal).unlink(missing_ok=True)


def reservierungsdatei(kanal):
    if not re.fullmatch(r'[a-z0-9-]+',kanal):
        raise ValueError('Ungueltiger Budgetkanal')
    return ORDNER/'reservierungen'/f'{kanal}.json'


def abbruch_abrechnen(kanal):
    """Nur die eigene bestaetigt abgebrochene CI-Reservierung zeitbasiert abschliessen."""
    p=reservierungsdatei(kanal)
    if os.environ.get('CF_PRODUKTION_OUTCOME')!='cancelled' or not p.is_file():
        return False
    r=json.loads(p.read_text());d=laden(kanal)
    if r.get('run')!=os.environ.get('GITHUB_RUN_ID') or r.get('datum')!=d['datum'] \
            or r.get('laeufe')!=d['laeufe'] or d['sekunden']!=r['vorher']+r['frei']:
        raise ValueError('Abbruch gehoert nicht zur aktuellen Budgetreservierung')
    zeit=datetime.datetime.fromisoformat(r['start_utc'])
    sekunden=math.ceil((datetime.datetime.now(datetime.timezone.utc)-zeit).total_seconds())
    if sekunden<0:
        raise ValueError('Abbruchzeit liegt vor der Reservierung')
    abschliessen(kanal,(r['frei'],r['vorher'],d),sekunden)
    print(f'Abgebrochenen Lauf abgerechnet: {min(r["frei"],sekunden)} Sekunden; Tagesgrenze unveraendert')
    return True


if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='abbruch':
        raise SystemExit('Aufruf: budget.py abbruch kanal')
    abbruch_abrechnen(sys.argv[2])
