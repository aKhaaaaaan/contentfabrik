"""Shorts 35-45 s (Nutzerentscheidung 10.10.2026 nach YouTube-Studio-Messung).

Alter Stand, den dieser Test erkennt: Shorts waren 62-90 s lang (gebaut ~1:30), gesehen wurden im
Schnitt nur 21-24 s (VW 23,6 %, Nintendo 27,4 %). Erinnerung: ab ~8.000 TikTok-Followern eine
zusaetzliche TikTok-Fassung > 60 s (Creator Rewards) - siehe UEBERGABE-CLAUDE.md / CLAUDE.md.
"""
import json
import unittest
from pathlib import Path

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import dramaturgie
import kanalstandard

WURZEL = Path(__file__).resolve().parents[1]


class ShortLaenge(unittest.TestCase):
    def test_standard_und_kanaele_35_bis_45(self):
        self.assertEqual(kanalstandard.STANDARD['laenge_s'], [35, 45])
        for k in ('ai-tools-explained', 'business-origin-stories'):
            with self.subTest(k=k):
                self.assertEqual(kanalstandard.laden(f'kanaele/{k}.json')['laenge_s'], [35, 45])
        self.assertEqual(dramaturgie.laengen({}), [35, 45])

    def test_langvideo_unveraendert(self):
        self.assertEqual(dramaturgie.laengen({'videoformat': 'lang'}), [360, 600])


if __name__ == '__main__':
    unittest.main()
