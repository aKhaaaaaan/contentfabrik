"""Git-Merge der Themenliste: neue Ideen erhalten, erledigte/entfernte nicht wieder einreihen."""
import json
from pathlib import Path
import sys


class Konflikt(ValueError):
    pass


def feld(base, remote, lokal):
    if remote == lokal:
        return remote
    if remote == base:
        return lokal
    if lokal == base:
        return remote
    if all(isinstance(x, list) for x in (base, remote, lokal)):
        if all(isinstance(v, str) for liste in (base, remote, lokal) for v in liste):
            entfernt = (set(base) - set(remote)) | (set(base) - set(lokal))
            return list(dict.fromkeys(v for v in remote + lokal if v not in entfernt))
        return warteschlange(base, remote, lokal)
    if all(isinstance(x, dict) for x in (base, remote, lokal)):
        aus = {}
        fehlt = object()
        for key in remote.keys() | lokal.keys():
            b, r, l = base.get(key, fehlt), remote.get(key, fehlt), lokal.get(key, fehlt)
            if r is fehlt or l is fehlt:
                if key not in base:
                    aus[key] = l if r is fehlt else r
                elif (l if r is fehlt else r) != b:
                    raise Konflikt('Gleichzeitiges Entfernen und Aendern eines Themenfelds')
            else:
                aus[key] = feld(b, r, l)
        return aus
    raise Konflikt('Dasselbe Themenfeld wurde unterschiedlich geaendert')


def warteschlange(base, remote, lokal):
    def mapping(liste):
        if not isinstance(liste, list) or any(not isinstance(x, dict) or not x.get('id') for x in liste):
            raise Konflikt('Themenliste ohne eindeutige IDs')
        d = {x['id']: x for x in liste}
        if len(d) != len(liste):
            raise Konflikt('Doppelte Themen-IDs')
        return d
    b, r, l = map(mapping, (base, remote, lokal))
    aus = {}
    for key in r.keys() | l.keys():
        if key in b and (key not in r or key not in l):
            continue  # Entfernen in einer der beiden Listen ist verbindlich.
        if key not in r or key not in l:
            aus[key] = r.get(key, l.get(key))
        else:
            aus[key] = feld(b.get(key, {}), r[key], l[key])
    # Bei ausdruecklichem lokalen Umordnen dessen Reihenfolge erhalten. Sonst aktuelle Hauptliste.
    gemeinsam = [x['id'] for x in base if x['id'] in aus]
    lokal_alt = [x['id'] for x in lokal if x['id'] in b and x['id'] in aus]
    reihenfolge = lokal + remote if lokal_alt != gemeinsam else remote + lokal
    ids = list(dict.fromkeys(x['id'] for x in reihenfolge if x['id'] in aus))
    return [aus[key] for key in ids]


if __name__ == '__main__':
    try:
        base, remote, lokal = [json.loads(Path(p).read_text(encoding='utf-8')) for p in sys.argv[1:4]]
        d = feld(base, remote, lokal)
        Path(sys.argv[2]).write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    except (ValueError, OSError, KeyError, TypeError):
        print('Themenkonflikt nicht sicher aufloesbar; keine Liste ueberschrieben', file=sys.stderr)
        sys.exit(1)
