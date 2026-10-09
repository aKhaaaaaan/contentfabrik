"""Zweitpruefer-Auszug fuer lange Skripte (Langvideo-Pilot 09.10.2026, Run 37945779063).

Alter Stand, den diese Tests erkennen: zweit.auszug waehlte ganze Absaetze nach ihrer
Gesamtueberschneidung mit dem 7.000-Zeichen-Skript. Bei einem langen Text passt jeder Absatz
ein bisschen; der Absatz mit „Breaking Bad", „Scotts Valley", „$8 billion" und dem Starttermin
von House of Cards fiel heraus. Der Pruefer meldete woertlich belegte Saetze als erfunden und
sperrte das Langvideo in allen vier Versuchen.
Daten: echter Wikipedia-Artikel (CC BY-SA 4.0) und echtes Skript aus dem Lauf.
"""
import json
import unittest
from pathlib import Path

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import zweit

DATEN = json.loads((Path(__file__).parent / 'daten' / 'zweit-netflix-langvideo.json').read_text(encoding='utf-8'))


class AuszugLangvideo(unittest.TestCase):
    def setUp(self):
        self.quelle, self.skript = DATEN['quelle'], DATEN['skript']
        self.grenze = min(zweit.GRENZE_ZEICHEN, 24000 - len(self.skript))
        self.auszug = zweit.auszug(self.quelle, self.skript, self.grenze)

    def test_belegte_aussagen_des_skripts_bleiben_im_auszug(self):
        # Jeder Begriff steht in Skript UND Quelle; der alte Auszug verlor die ersten vier.
        for begriff in ('Breaking Bad', 'Scotts Valley', '$8 billion', 'February 1, 2013',
                        'Qwikster', 'Latin America'):
            with self.subTest(begriff=begriff):
                self.assertIn(begriff, self.skript)
                self.assertIn(begriff, self.quelle)
                self.assertIn(begriff, self.auszug)

    def test_der_ganze_belegsatz_nicht_nur_das_stichwort(self):
        self.assertIn("In 2010, Netflix acquired the rights to Breaking Bad, produced by Sony Pictures "
                      "Television, after the show's third season", self.auszug)

    def test_grenze_fuer_groq_eingehalten(self):
        self.assertLessEqual(len(self.auszug), self.grenze)

    def test_unbelegtes_wird_nicht_herbeigezaubert(self):
        # „30 percent" steht im Skript, aber nicht in der Quelle - muss weiter auffallen.
        self.assertIn('30 percent', self.skript)
        self.assertNotIn('30 percent', self.auszug)

    def test_kurze_quelle_bleibt_unveraendert(self):
        self.assertEqual(zweit.auszug('Kurz. Quelle.', self.skript, 100), 'Kurz. Quelle.')


if __name__ == '__main__':
    unittest.main()
