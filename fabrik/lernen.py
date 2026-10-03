"""Lern-Gedaechtnis je Kanal: Aus jeder KI-Pruefung werden ALLGEMEINE Regeln.

GEMELDET: „nach Feedback soll das Tool daraus lernen und besser werden".
Nach jeder Pruefung fasst Gemini die Probleme zu Regeln zusammen (keine
Einzelfaelle), fuehrt Doppelte zusammen und haelt hoechstens 12 - die
wichtigsten zuerst. Skript-Schreiben und Bildwahl bekommen sie mit.

Datei: lernen/<kanal>.json (im Projekt, wird nach jedem Lauf gesichert).
"""
import json, datetime
from pathlib import Path

ORDNER = Path('lernen')
HOECHSTENS = 12


def regeln(kanal):
    p = ORDNER / f'{kanal}.json'
    return json.loads(p.read_text(encoding='utf-8')).get('regeln', []) if p.exists() else []


def aktualisieren(kanal, kritik):
    """kritik: Ergebnis von kritik.py. Gibt die neuen Regeln zurueck."""
    from skript import gemini
    alt = regeln(kanal)
    probleme = [f"[{p['art']}] {p['text']}" for p in kritik.get('probleme', [])]
    schwach = [k for k, v in (kritik.get('kategorien') or {}).items() if v < 8]
    if not probleme and not schwach:
        return alt
    neu, _ = gemini(
        'You maintain a short rulebook for an automated faceless YouTube Shorts channel. Below are the current '
        'rules and the problems a quality review just found in the latest video. Return the UPDATED rulebook: '
        f'at most {HOECHSTENS} short, GENERAL, actionable rules for future videos (never about this specific '
        'topic), merge duplicates, most important first. Keep existing rules unless a new one replaces them. '
        'Rules must be things a script writer or a clip picker can follow. English.\n\n'
        'Current rules:\n' + ('\n'.join(f'- {r}' for r in alt) or '(none)')
        + '\n\nWeak categories (score < 8): ' + (', '.join(schwach) or 'none')
        + '\nProblems found:\n' + '\n'.join(f'- {p}' for p in probleme),
        {'type': 'OBJECT', 'properties': {'regeln': {'type': 'ARRAY', 'items': {'type': 'STRING'}}},
         'required': ['regeln']}, temperatur=0.2)
    liste = [r.strip() for r in neu['regeln'] if r.strip()][:HOECHSTENS]
    ORDNER.mkdir(exist_ok=True)
    (ORDNER / f'{kanal}.json').write_text(json.dumps(
        {'stand': datetime.date.today().isoformat(), 'regeln': liste}, indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8')
    print(f'Gelernt ({kanal}): {len(alt)} -> {len(liste)} Regeln')
    for r in liste:
        print('  -', r)
    return liste
