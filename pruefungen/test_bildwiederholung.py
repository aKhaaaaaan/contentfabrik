"""Weniger Bildwiederholungen (Aurelio 09.10.2026: 6 doppelte Bilder in 21 Einstellungen, Nutzer 6/10).

Alter Stand, den diese Tests erkennen:
- Jeder Neuversuch des Baus zaehlte Ersatzbilder ab 0; aus dem Cache uebernommene Ersatzbilder
  zaehlten nicht -> weit mehr Wiederholungen als die Grenze (Short: 2) erlaubt.
- Der Schrift-Schutz galt nur fuer Bildschirme; ein Messgeraet mit Ziffern wurde zweimal
  abgelehnt (ill_18), danach Ersatzbild.
"""
import unittest
from pathlib import Path

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import prompts

WURZEL = Path(__file__).resolve().parents[1]


class Schrifttraeger(unittest.TestCase):
    def test_ziffernblatt_und_karte_bekommen_leere_flaechen(self):
        for szene in ('an analog meter dial measuring token input costs on a workbench',
                      'a woman at a cafe table holds a card', 'stacks of banknotes and a receipt'):
            with self.subTest(szene=szene):
                self.assertIn('no printed letters, digits', prompts.szene_ohne_schrift(szene))

    def test_szene_ohne_schrifttraeger_bleibt_unveraendert(self):
        self.assertEqual(prompts.szene_ohne_schrift('a calm harbor at dusk'), 'a calm harbor at dusk')


class Ersatzzaehlung(unittest.TestCase):
    def test_ersatzbilder_aus_dem_cache_zaehlen_mit(self):
        quelle = (WURZEL / 'fabrik/bauen.py').read_text(encoding='utf-8')
        self.assertIn("bild_ersatz += 1 if alt.get('ersatz') else 0", quelle)
        self.assertIn("'ersatz': bild_ersatz > ersatz0}", quelle)
        self.assertIn('ersatz0 = bild_ersatz', quelle)


if __name__ == '__main__':
    unittest.main()
