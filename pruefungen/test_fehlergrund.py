"""Fehlergruende im Verlauf (09.10.2026).

Alter Stand, den diese Tests erkennen: 8 Baufehler (06.-08.10.) standen im Verlauf ohne
jeden Grund - er stand nur im GitHub-Log, das nach wenigen Tagen verschwindet. Damit
liess sich weder lernen noch nachpruefen, ob ein Fehler wirklich behoben ist.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import lauf

WURZEL = Path(__file__).resolve().parents[1]
SKRIPT = {'thema': 'T', 'titel': ['A', 'B'], 'teile': [{'text': 'Hallo Welt.'}]}


class Fehlergrund(unittest.TestCase):
    def test_bauen_schreibt_den_grund_bei_absturz(self):
        with tempfile.TemporaryDirectory() as t:
            r = subprocess.run([sys.executable, str(WURZEL / 'fabrik/bauen.py'), str(Path(t) / 'fehlt.json'), t],
                               capture_output=True, text=True, cwd=WURZEL)
            self.assertNotEqual(r.returncode, 0)
            grund = (Path(t) / 'baufehler.txt').read_text(encoding='utf-8')
        self.assertTrue(grund.startswith('FileNotFoundError'), grund)

    def test_verlauf_speichert_den_grund(self):
        with tempfile.TemporaryDirectory() as t:
            alt = Path.cwd()
            import os
            os.chdir(t)
            try:
                lauf.verlauf_eintragen('test', SKRIPT, 'baufehler', None, grund='ValueError: kein Bild')
                lauf.verlauf_eintragen('test', dict(SKRIPT, thema='U'), 'gesendet', 8)
                v = json.loads(Path('verlauf/test.json').read_text(encoding='utf-8'))
            finally:
                os.chdir(alt)
        self.assertEqual(v[0]['grund'], 'ValueError: kein Bild')
        self.assertNotIn('grund', v[1])

    def test_lauf_reicht_baufehler_und_sperrgruende_weiter(self):
        quelle = (WURZEL / 'fabrik/lauf.py').read_text(encoding='utf-8')
        self.assertIn("grund=detail or letzter_grund", quelle)
        self.assertIn("verlauf_eintragen(kanal, skript, 'skriptqualitaet', None, grund=letzter_grund)", quelle)
        self.assertIn("grund='; '.join((runde['sperrgruende'] or [])[:2]", quelle)


if __name__ == '__main__':
    unittest.main()
