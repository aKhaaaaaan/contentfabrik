"""Bauzustand fuer gezielte Korrekturen; unpassende/fehlende Daten nie wiederverwenden."""
import hashlib
import json
from pathlib import Path


def signatur(daten):
    return hashlib.sha256(json.dumps(daten, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def laden(ordner):
    try:
        d = json.loads((Path(ordner) / 'bauzustand.json').read_text(encoding='utf-8'))
        return d if d.get('version') == 1 else {}
    except (OSError, ValueError, AttributeError):
        return {}


def dateien_ok(ordner, namen):
    return bool(namen) and all(isinstance(n, str) and Path(n).name == n
        and not any(z in n for z in "'\r\n") and (Path(ordner) / n).is_file()
        and (Path(ordner) / n).stat().st_size > 0 for n in namen)


def audio_key(skript, code):
    return signatur({'code': code, 'text': [t['text'] for t in skript['teile']],
                     'stimme': skript.get('stimme', 'af_heart'), 'tempo': skript.get('tempo', 1.05),
                     'laenge_s': skript.get('laenge_s', [62, 90])})


def stueck_key(skript, index, dauer, code):
    return signatur({'code': code, 'teil': skript['teile'][index], 'index': index, 'dauer': dauer,
                     'titel': skript['titel'], 'teile': len(skript['teile']),
                     'plaetze': [t.get('platz') for t in skript['teile']],
                     'bilder': skript.get('bilder', []), 'regeln': skript.get('regeln', []),
                     'videoformat': skript.get('videoformat', 'short'),
                     'titel_farbe': skript.get('titel_farbe', '#20D2BE'),
                     'hintergrund': skript.get('hintergrund_suche')})


def speichern(ordner, daten):
    (Path(ordner) / 'bauzustand.json').write_text(json.dumps(
        dict(daten, version=1), indent=2, ensure_ascii=False), encoding='utf-8')
