"""Bild-zu-Wort-Bezug vor dem Malen (Nutzer 10.10.2026: „Die Motive passen wenig zu den Woertern").

Alter Stand, den diese Tests erkennen: Flash-Lite plante allein; "streams overtook DVD shipments"
bekam einen DVD-Umschlag, nichts pruefte den Bezug vor der Bilderzeugung.
"""
import unittest
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import bildplan

TEIL = [{'index': 0, 'text': 'By 2009, streams overtook DVD shipments.'},
        {'index': 1, 'text': 'Reed Hastings founded Netflix.'}]
DATEN = [{'index': 0, 'bildmodus': 'illustration', 'motiv': 'opening red envelope', 'szene': 'a hand opens a DVD envelope', 'suche': 'envelope'},
         {'index': 1, 'bildmodus': 'figur', 'motiv': 'presenter', 'szene': 'presenter', 'suche': 'host'}]


class Bezug(unittest.TestCase):
    def test_schwaches_motiv_wird_ersetzt_starke_modelle_zuerst(self):
        antwort = {'pruefung': [{'index': 0, 'note': 3, 'motiv': 'family streaming on TV',
                                 'szene': 'a family on a sofa watching a glowing movie stream, a dusty stack of mailers forgotten',
                                 'suche': 'family tv'}]}
        with patch('skript.gemini', return_value=(antwort, 'm')) as g:
            daten, ersetzt = bildplan.bezug_pruefen(__import__('skript').gemini, TEIL, [dict(d) for d in DATEN])
        self.assertEqual(ersetzt, 1)
        self.assertEqual(daten[0]['motiv'], 'family streaming on TV')
        self.assertEqual(daten[1]['motiv'], 'presenter')  # Figur-Einstellung unangetastet
        self.assertEqual(g.call_args.kwargs['modelle'][0], 'gemini-3.8-flash')
        self.assertIn('By 2009, streams overtook', g.call_args.args[0])

    def test_gute_note_bleibt(self):
        antwort = {'pruefung': [{'index': 0, 'note': 8, 'motiv': 'x', 'szene': 'y', 'suche': 'z'}]}
        with patch('skript.gemini', return_value=(antwort, 'm')):
            daten, ersetzt = bildplan.bezug_pruefen(__import__('skript').gemini, TEIL, [dict(d) for d in DATEN])
        self.assertEqual(ersetzt, 0)
        self.assertEqual(daten[0]['motiv'], 'opening red envelope')

    def test_ausfall_laesst_plan_stehen(self):
        with patch('skript.gemini', side_effect=RuntimeError('503')):
            daten, ersetzt = bildplan.bezug_pruefen(__import__('skript').gemini, TEIL, [dict(d) for d in DATEN])
        self.assertEqual((ersetzt, daten[0]['motiv']), (0, 'opening red envelope'))

    def test_planer_nutzt_starke_modelle_zuerst(self):
        self.assertEqual(bildplan.PLANEN[0], 'gemini-3.8-flash')
        self.assertNotIn('lite', bildplan.PLANEN[0])


if __name__ == '__main__':
    unittest.main()
