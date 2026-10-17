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
    if any(not isinstance(x, list) for x in (base, remote, lokal)):
        raise Konflikt('Themenliste ist keine Liste')
    alle = base + remote + lokal
    id_key = 'message_id' if alle and all(isinstance(x, dict) and 'message_id' in x for x in alle) else 'id'
    def mapping(liste):
        if not isinstance(liste, list) or any(not isinstance(x, dict) or not x.get(id_key) for x in liste):
            raise Konflikt('Themenliste ohne eindeutige IDs')
        d = {x[id_key]: x for x in liste}
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
    gemeinsam = [x[id_key] for x in base if x[id_key] in aus]
    lokal_alt = [x[id_key] for x in lokal if x[id_key] in b and x[id_key] in aus]
    reihenfolge = lokal + remote if lokal_alt != gemeinsam else remote + lokal
    ids = list(dict.fromkeys(x[id_key] for x in reihenfolge if x[id_key] in aus))
    return [aus[key] for key in ids]


def kontingent(base, remote, lokal):
    """verlauf/gemini-kontingent.json: Sperren beider Seiten behalten, je Modell die spaetere Frist.

    GEMESSEN 16.10.2026 (Lauf 38878792792): Video- und Themenlaeufe schrieben gleichzeitig Sperren;
    der Rebase-Konflikt verhinderte das Sichern von Verlauf, Budget und Versandprotokoll des Laufs.
    Eine laengere Sperre ist die vorsichtigere - so wird kein erschoepftes Modell erneut angefragt."""
    aus = dict(remote, **{k: v for k, v in lokal.items() if k != 'modelle'})
    modelle = {}
    for teil in (remote.get('modelle') or {}, lokal.get('modelle') or {}):
        for k, v in teil.items():
            alt = modelle.get(k)
            if alt is None or (v.get('bis') or 0) > (alt.get('bis') or 0):
                modelle[k] = v
    aus['modelle'] = modelle
    # 17.10.2026: Zeitlimit-Zeitpunkte je Modell (ki_speicher.sperren, Steigerung 1/3/9 Min.) beider Seiten.
    zl = {}
    for teil in (remote.get('zeitlimits') or {}, lokal.get('zeitlimits') or {}):
        for k, v in teil.items():
            zl[k] = sorted(set(zl.get(k, [])) | set(v if isinstance(v, list) else []))
    if zl:
        aus['zeitlimits'] = zl
    return aus


if __name__ == '__main__':
    try:
        base, remote, lokal = [json.loads(Path(p).read_text(encoding='utf-8')) for p in sys.argv[1:4]]
        if all(isinstance(x, dict) and isinstance(x.get('modelle'), dict) for x in (remote, lokal)):
            d = kontingent(base, remote, lokal)
        else:
            d = feld(base, remote, lokal)
        Path(sys.argv[2]).write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    except (ValueError, OSError, KeyError, TypeError):
        print('Themenkonflikt nicht sicher aufloesbar; keine Liste ueberschrieben', file=sys.stderr)
        sys.exit(1)
