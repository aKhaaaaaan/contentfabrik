"""Pflicht-Aufruf Like/Teilen/Speichern darf die Faktenpruefung nicht kippen (Lauf 37757439013)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
import prompts  # noqa: E402
import skript  # noqa: E402


class CtaFaktenTest(unittest.TestCase):
    def test_nur_cta_einwand_wird_bestanden(self):
        p = {'ok': False, 'probleme': ['Offending clause: "Be sure to like, share and save this video.", Source mismatch']}
        self.assertEqual(skript.ohne_cta_einwand(p), {'ok': True, 'probleme': []})

    def test_echter_fehler_bleibt(self):
        echt = "Offending clause: 'a free Convex account', Source mismatch: The source says a paid plan"
        p = {'ok': False, 'probleme': [echt, "Offending clause: 'Be sure to like, share and save this video.'"]}
        neu = skript.ohne_cta_einwand(p)
        self.assertEqual(neu['probleme'], [echt])
        self.assertFalse(neu['ok'])

    def test_ohne_cta_unveraendert(self):
        p = {'ok': False, 'probleme': ['Offending clause: founded in 2009 - source says 2010']}
        self.assertIs(skript.ohne_cta_einwand(p), p)

    def test_pruefauftrag_nennt_cta_als_keine_behauptung(self):
        self.assertIn('like, share and save the video is mandated', prompts.fakten('q', 't'))


if __name__ == '__main__':
    unittest.main()
