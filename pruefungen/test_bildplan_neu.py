"""Gleicher Bildfehler zweimal -> neuer Bildplan (10.10.2026).

Alter Stand, den diese Tests erkennen: Der Bildplan lag im Teilbau-Cache und wurde bei jedem
Neuversuch wiederverwendet - Tageslauf 38037738527 scheiterte 5x an derselben Einstellung 1.
"""
import json
import tempfile
import unittest
from pathlib import Path

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import lauf
import rendercache

WURZEL = Path(__file__).resolve().parents[1]


class BildplanNeu(unittest.TestCase):
    def test_bildplan_weg_stimme_bleibt(self):
        with tempfile.TemporaryDirectory() as t:
            rendercache.speichern(t, {'audio': {'key': 'a'}, 'bildplan': {'key': 'b', 'einstellungen': []},
                                      'stuecke': {}})
            self.assertTrue(lauf.bildplan_verwerfen(t))
            d = rendercache.laden(t)
            self.assertNotIn('bildplan', d)
            self.assertEqual(d['audio'], {'key': 'a'})
            self.assertFalse(lauf.bildplan_verwerfen(t))  # nichts mehr zu verwerfen

    def test_ohne_bauzustand_kein_absturz(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(lauf.bildplan_verwerfen(t))

    def test_lauf_verwirft_nur_bei_gleichem_fehler(self):
        quelle = (WURZEL / 'fabrik/lauf.py').read_text(encoding='utf-8')
        self.assertIn('if detail and detail == letzter_baufehler:', quelle)
        self.assertIn('bildplan_verwerfen(ordner)', quelle)
        self.assertIn("letzter_baufehler = ''", quelle)


if __name__ == '__main__':
    unittest.main()
