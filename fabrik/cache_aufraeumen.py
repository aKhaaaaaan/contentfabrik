"""Veraltete Actions-Caches loeschen: je Gruppe nur der neueste bleibt.

GEMESSEN 18.10.2026: 10,73 GB von 10 GB belegt. Jeder Shorts-Lauf legt je Kanal einen neuen Clip-Cache
(1,7 GB) mit der Lauf-Nummer im Schluessel an; wiederhergestellt wird ueber restore-keys aber immer nur
der NEUESTE passende. Die alten waren tot und verdraengten nach GitHubs LRU-Regel die Langvideo-
Zwischenstaende (Stimme, Bilder), die nur einmal pro Woche benutzt werden.
Gruppe = Schluessel ohne Lauf-Nummer/Versuch; Schluessel ohne Lauf-Nummer (kokoro, pip) bleiben unberuehrt.
"""
import json
import os
import re
import sys
import urllib.request

LAUF_NR = re.compile(r'-\d{9,}(?:-\d+)?(?=-|$)')


def gruppe(key):
    """Schluessel ohne Lauf-Nummer; None, wenn der Schluessel keine Lauf-Nummer enthaelt."""
    g = LAUF_NR.sub('', key)
    return g if g != key else None


def veraltet(caches):
    """Alle Caches, die in ihrer Gruppe nicht der neueste sind (nach Erstellzeit)."""
    neueste = {}
    for c in caches:
        g = gruppe(c['key'])
        if g and (g not in neueste or c['created_at'] > neueste[g]['created_at']):
            neueste[g] = c
    return [c for c in caches if gruppe(c['key']) and neueste[gruppe(c['key'])]['id'] != c['id']]


def _api(methode, pfad):
    anfrage = urllib.request.Request(
        'https://api.github.com/repos/' + os.environ['GITHUB_REPOSITORY'] + pfad, method=methode,
        headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
                 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(anfrage, timeout=30) as r:
        daten = r.read()
    return json.loads(daten) if daten else {}


def main():
    caches, seite = [], 1
    while True:
        d = _api('GET', f'/actions/caches?per_page=100&page={seite}')
        caches += d.get('actions_caches', [])
        if len(d.get('actions_caches', [])) < 100:
            break
        seite += 1
    weg = veraltet(caches)
    gesamt = sum(c['size_in_bytes'] for c in caches)
    frei = 0
    for c in weg:
        try:
            _api('DELETE', f"/actions/caches/{c['id']}")
            frei += c['size_in_bytes']
            print(f"geloescht: {c['key']} ({c['size_in_bytes'] / 1e6:.0f} MB)")
        except Exception as e:  # ein einzelner Fehlschlag (z. B. schon verdraengt) stoppt den Rest nicht
            print(f"nicht geloescht: {c['key']}: {type(e).__name__} {e}")
    print(f'Caches vorher {gesamt / 1e9:.2f} GB, freigegeben {frei / 1e9:.2f} GB, '
          f'jetzt {(gesamt - frei) / 1e9:.2f} GB ({len(caches) - len(weg)} Eintraege)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
