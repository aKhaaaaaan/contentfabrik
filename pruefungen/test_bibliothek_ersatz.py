"""Notfall-Ersatz aus der sichtgeprueften Bibliothek (10.10.2026).

Alter Stand, den diese Tests erkennen: Scheiterte Einstellung 1 eines Shorts, gab es keinen
erlaubten Ersatz (davor nur das Figurbild) - Tageslauf 38037738527 brach 5x ab, kein Video.
"""
import unittest
from pathlib import Path

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import bauen
import bibliothek
import bildplan

WURZEL = Path(__file__).resolve().parents[1]


class BibliothekErsatz(unittest.TestCase):
    def test_liefert_kanaleigene_ungenutzte_bilder_ohne_wiederholung(self):
        benutzt, gesehen, vorherige = set(), [], None
        for _ in range(3):
            pfad = bauen.bibliothek_ersatz('AI Tools Explained', vorherige, benutzt)
            self.assertIsNotNone(pfad)
            eintrag = next(b for b in bibliothek.katalog() if b['datei'] == pfad.name)
            self.assertEqual(eintrag['kanal'], 'AI Tools Explained')
            self.assertNotIn(pfad.name, gesehen)
            gesehen.append(pfad.name)
            vorherige = bildplan.material_id(pfad)

    def test_erschoepft_liefert_none(self):
        alle = {b['id'] for b in bibliothek.katalog()}
        self.assertIsNone(bauen.bibliothek_ersatz('AI Tools Explained', None, alle))

    def test_nur_im_short_und_vor_dem_abbruch(self):
        quelle = (WURZEL / 'fabrik/bauen.py').read_text(encoding='utf-8')
        i = quelle.index('if not material and B < H:')
        self.assertLess(i, quelle.index("raise ValueError(f'Phase {shot[\"phase\"]}, Einstellung {i}: kein passendes Hauptbild"))


if __name__ == '__main__':
    unittest.main()
