"""Befristete Gemini-Sperren und explizite Wiederverwendung identischer Pruefungen.

Keine Schluessel, Rohfehler oder kreativen Entwuerfe speichern. Cache ist opt-in.
"""
import datetime
import hashlib
import json
import math
import time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSION = 1
KONTINGENT = Path('verlauf/gemini-kontingent.json')
CACHE = Path('ki-cache')
TTL = 6 * 3600
SPERRE_MAX = 26 * 3600  # Pazifik-Tag hat bei Rueckstellung bis zu 25 Stunden.


def hashwert(daten):
    return hashlib.sha256(json.dumps(daten, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def konto(schluessel):
    return hashlib.sha256(schluessel.encode()).hexdigest()[:24]


def lesen_json(pfad):
    try:
        d = json.loads(Path(pfad).read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def speichern(pfad, daten):
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix('.tmp')
    tmp.write_text(json.dumps(daten, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    tmp.replace(pfad)


def tagesreset(jetzt=None):
    jetzt = time.time() if jetzt is None else jetzt
    try:
        pazifik = ZoneInfo('America/Los_Angeles')
    except ZoneInfoNotFoundError:
        # Ohne Zeitzonendaten konservativ sperren; Linux hat sie, Windows: tzdata.
        return jetzt + 86400
    tag = datetime.datetime.fromtimestamp(jetzt, pazifik).date() + datetime.timedelta(days=1)
    return datetime.datetime.combine(tag, datetime.time(), pazifik).timestamp()


def sperre(schluessel, modell, jetzt=None):
    jetzt = time.time() if jetzt is None else jetzt
    d = lesen_json(KONTINGENT)
    modelle = d.get('modelle', {})
    e = modelle.get(konto(schluessel) + ':' + modell, {}) \
        if d.get('version') == VERSION and isinstance(modelle, dict) else {}
    if isinstance(e, dict) and isinstance(e.get('bis'), (int, float)) and jetzt < e['bis'] <= jetzt + SPERRE_MAX:
        return e.get('grund', 'voruebergehend gesperrt')
    return None


def sperren(schluessel, modell, grund, sekunden=None):
    jetzt = time.time()
    alt = lesen_json(KONTINGENT)
    eintraege = alt.get('modelle', {}) if alt.get('version') == VERSION else {}
    if not isinstance(eintraege, dict):
        eintraege = {}
    eintraege = {k: e for k, e in eintraege.items() if isinstance(e, dict)
                 and isinstance(e.get('bis'), (int, float)) and jetzt < e['bis'] <= jetzt + SPERRE_MAX}
    eintraege[konto(schluessel) + ':' + modell] = {
        'grund': grund, 'bis': tagesreset(jetzt) if sekunden is None else jetzt + sekunden}
    speichern(KONTINGENT, {'version': VERSION, 'modelle': eintraege})


def schema_ok(wert, schema):
    """Pruefresultate vor Speicherung UND Wiederverwendung rekursiv validieren."""
    art = schema.get('type', '').upper()
    if art == 'OBJECT':
        if not isinstance(wert, dict) or any(k not in wert for k in schema.get('required', [])):
            return False
        return all(schema_ok(wert[k], s) for k, s in schema.get('properties', {}).items() if k in wert)
    if art == 'ARRAY':
        return isinstance(wert, list) and all(schema_ok(x, schema.get('items', {})) for x in wert)
    if art == 'STRING' and not isinstance(wert, str):
        return False
    if art == 'BOOLEAN' and not isinstance(wert, bool):
        return False
    if art in ('INTEGER', 'NUMBER') and (isinstance(wert, bool) or not isinstance(wert, (int, float))
            or not math.isfinite(wert) or (art == 'INTEGER' and not isinstance(wert, int))):
        return False
    return 'enum' not in schema or wert in schema['enum']


def bereinigen(wert, schema, pfad='', entfernt=None):
    """Optionale Felder mit falschem Typ/Wert entfernen (rekursiv), Pflichtfelder nie.
    GEMESSEN 09.10.2026 (Langvideo-Pilot 37945779063): Claudes ganzes Skript fiel durch die
    Schemapruefung und Claude wurde fuer den Lauf gesperrt - wegen eines Nebenfelds.
    Gibt (bereinigter_wert, [entfernte Pfade]) zurueck; der Aufrufer prueft danach schema_ok."""
    entfernt = [] if entfernt is None else entfernt
    art = schema.get('type', '').upper()
    if art == 'OBJECT' and isinstance(wert, dict):
        pflicht = set(schema.get('required', []))
        aus = {}
        for k, v in wert.items():
            s = schema.get('properties', {}).get(k)
            if s is None:
                aus[k] = v
                continue
            v, _ = bereinigen(v, s, f'{pfad}.{k}', entfernt)
            if k in pflicht or schema_ok(v, s):
                aus[k] = v
            else:
                entfernt.append(f'{pfad}.{k}={str(v)[:30]}')
        return aus, entfernt
    if art == 'ARRAY' and isinstance(wert, list):
        return [bereinigen(x, schema.get('items', {}), f'{pfad}[{i}]', entfernt)[0]
                for i, x in enumerate(wert)], entfernt
    return wert, entfernt


def cache_key(prompt, schema, modelle, temperatur, zweck, medien=None):
    return hashwert({'version': VERSION, 'prompt': prompt, 'schema': schema,
                    'modelle': modelle, 'temperatur': temperatur, 'zweck': zweck, 'medien': medien})


def cache_lesen(key, schema, modelle):
    d = lesen_json(CACHE / (key + '.json'))
    zeit = d.get('zeit')
    if d.get('version') == VERSION and d.get('key') == key and d.get('modell') in modelle \
            and isinstance(zeit, (int, float)) and 0 <= time.time() - zeit < TTL \
            and schema_ok(d.get('ergebnis'), schema):
        return d['ergebnis'], d['modell']
    return None


def cache_schreiben(key, ergebnis, modell, schema):
    if not schema_ok(ergebnis, schema):
        raise ValueError('KI-Pruefung entspricht nicht dem erforderlichen Schema')
    # Begrenzen: auch negative Fakten-/Storyurteile sparen unveraenderte Anfragen.
    for p in CACHE.glob('*.json'):
        if time.time() - p.stat().st_mtime > TTL:
            p.unlink(missing_ok=True)
    speichern(CACHE / (key + '.json'), {'version': VERSION, 'key': key, 'zeit': time.time(),
                                     'modell': modell, 'ergebnis': ergebnis})
