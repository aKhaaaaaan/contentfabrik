"""Pilot-/Betriebsbericht fuer GitHub Step Summary, ohne API-Aufrufe."""
import json
import os
from pathlib import Path
import sys


def markdown(d):
    def sauber(x):
        return str(x).replace('|', '/').replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;')
    zeilen = [f"## Contentfabrik: {sauber(d['kanal'])}", '',
              f"Status: **{sauber(d['status'])}** · Laufzeit: {d.get('sekunden', 0):.1f} s", '',
              '| Runde | Arbeit | Note | Neu / wiederverwendet | Zeit |',
              '|---|---|---|---|---|']
    for r in d.get('runden', []):
        m = r.get('messung') or {}
        zeilen.append(f"| {r['runde']} | {sauber(r['art'])} | {r.get('note') or 'offen'} | "
                      f"{m.get('stuecke_neu', '-')} / {m.get('stuecke_wiederverwendet', '-')} | "
                      f"{r.get('sekunden', 0):.1f} s |")
    zeilen += ['', 'Die Noten stammen aus der KI-Pruefung, nicht aus Zuschauerzahlen.']
    for r in d.get('runden', []):
        if r.get('sperrgruende'):
            zeilen += ['', f"Runde {r['runde']} gesperrt: " + '; '.join(sauber(x) for x in r['sperrgruende'])]
        if r.get('lernergebnis'):
            e = r['lernergebnis']
            zeilen += ['', f"Korrektur {r['runde']}: {e.get('vorher')} → {e.get('nachher')}; "
                       + ('nicht auswertbar: Pruefung fehlt' if not e.get('auswertbar', True) else
                          'verbessert' if e.get('verbessert') else 'keine gemessene Verbesserung')]
    return '\n'.join(zeilen) + '\n'


if __name__ == '__main__':
    p = Path(sys.argv[1] if len(sys.argv) > 1 else 'ausgabe/bericht.json')
    text = markdown(json.loads(p.read_text(encoding='utf-8'))) if p.exists() else \
        '## Contentfabrik\n\nKein Bericht: Der Lauf endete vor einer auswertbaren Video-Pruefung.\n'
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(text)
    print(text)
