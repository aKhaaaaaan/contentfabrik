"""Bilder zeigen, was gesagt wird (Nutzer 09.10.2026, Aurelio 6/10: "Bilder haengen nicht mit dem Text zusammen").

Alter Stand, den diese Tests erkennen: Der Szenen-Auftrag verlangte fuer Software IMMER physische
Metaphern; 21 von 21 Einstellungen wurden Sinnbilder (Sparschwein, Muenzen, Schluessel). Die
Video-Bewertung fragte nur allgemein, ob Bilder "passen".
"""
import unittest

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import kritik
import prompts


class Bildbezug(unittest.TestCase):
    def test_szenen_zeigen_das_genannte_statt_sinnbild(self):
        self.assertNotIn('Show software ideas through physical metaphors', prompts.SZENEN)
        self.assertIn('show THAT', prompts.SZENEN)
        self.assertIn('never a generic symbol', prompts.SZENEN)

    def test_keine_generierten_bildschirme_bleibt(self):
        self.assertIn('Never make a screen', prompts.SZENEN)

    def test_bewertung_erkennt_sinnbilder(self):
        self.assertIn('generic symbol', kritik.KATEGORIEN['bild_passt'])

    def test_skriptauftrag_nutzt_die_regel(self):
        text = prompts.skript({'name': 'AI Tools Explained', 'format': 'erklaerung'}, 'Aurelio', '', '', '150-190')
        self.assertIn('never a generic symbol', text)


if __name__ == '__main__':
    unittest.main()
