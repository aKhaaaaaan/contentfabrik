"""Arbeits-Vorbild der Kanalfigur (10.10.2026).

Alter Stand, den diese Tests erkennen: Die Bild-KI bekam das Original-Portraet (Stadtkulisse,
Ziffern in der Brille, beschriftetes Zifferblatt) und kopierte es - Figur einsetzen scheiterte
12 von 12 Mal.
"""
import unittest
from pathlib import Path

from PIL import Image

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import illustration

KANAELE = ('ai-tools-explained', 'business-origin-stories')


class Referenz(unittest.TestCase):
    def test_bild_ki_bekommt_das_arbeits_vorbild(self):
        for k in KANAELE:
            with self.subTest(k=k):
                self.assertEqual(illustration.referenz(k).name, f'{k}_referenz.jpg')

    def test_original_bleibt_unveraendert_vorhanden(self):
        for k in KANAELE:
            self.assertTrue((illustration.FIGUREN / f'{k}.jpg').is_file())

    def test_hintergrund_ist_neutral(self):
        # Ecken des Arbeits-Vorbilds: gleichmaessiges Grau statt Stadtkulisse.
        for k in KANAELE:
            with Image.open(illustration.referenz(k)) as im:
                im = im.convert('RGB')
                for x, y in ((5, 5), (im.width - 6, 5), (5, 300)):
                    r, g, b = im.getpixel((x, y))
                    with self.subTest(k=k, ecke=(x, y)):
                        self.assertLess(max(r, g, b) - min(r, g, b), 12)
                        self.assertTrue(110 <= r <= 145)

    def test_ohne_arbeits_vorbild_das_original(self):
        self.assertEqual(illustration.referenz('gibt-es-nicht').name, 'gibt-es-nicht.jpg')


if __name__ == '__main__':
    unittest.main()
