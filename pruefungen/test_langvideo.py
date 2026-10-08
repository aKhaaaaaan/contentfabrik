"""Erstes Langvideo (Nutzerwunsch 08.10.2026: „lange Videos, mit Shorts verdient man nichts").

Alter Stand, den diese Tests erkennen:
- Stimme in EINEM Gemini-Aufruf (120 s Zeitlimit) -> 9 Min. Ton scheitern sicher oder still.
- Langvideo-Wortgrenze fest 2.35-2.65 W/s (Kokoro) -> mit Orus ~13 statt 10 Minuten.
- Pilot-Job 45 Min. und Budget 90 Min. -> ein Langvideo (70-80 Bilder) kann nie fertig werden.
- Pilot ohne Claude-Token -> anderer Autor als im Tageslauf.
"""
import json
import re
import unittest
from pathlib import Path

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import bauen
import dramaturgie
import lauf
import skript

PROFIL = json.loads(Path('formate/business-origin-stories.json').read_text(encoding='utf-8'))


class Sprechbloecke(unittest.TestCase):
    def test_short_bleibt_ein_aufruf(self):
        teile = ['word ' * 40] * 5  # 200 Woerter
        self.assertEqual(len(bauen.sprechbloecke(teile)), 1)

    def test_langvideo_in_abschnitten_ohne_textverlust(self):
        teile = [f'satz{i} ' + 'word ' * 59 for i in range(20)]  # 1200 Woerter
        bloecke = bauen.sprechbloecke(teile)
        self.assertGreaterEqual(len(bloecke), 3)
        self.assertTrue(all(len(b.split()) <= bauen.SPRECHBLOCK_WOERTER for b in bloecke))
        self.assertEqual(' '.join(bloecke).split(), ' '.join(teile).split())


class Wortgrenze(unittest.TestCase):
    def test_langvideo_8_bis_10_minuten_mit_orus(self):
        self.assertEqual(dramaturgie.videoformat(PROFIL), 'lang')
        lmin, lmax = dramaturgie.laengen(PROFIL)
        self.assertEqual((lmin, lmax), (480, 600))
        von, bis = map(int, self._woerter().split('-'))
        rate = skript.wortrate(PROFIL) * 1.08  # gesprochen mit Grundtempo
        self.assertGreaterEqual(von / rate, 480, 'kuerzer als 8 Min. -> keine Mid-Roll-Werbung')
        self.assertLessEqual(bis / rate, 600)

    def _woerter(self):
        from unittest.mock import patch
        with patch('prompts.skript', side_effect=lambda k, t, f, b, w: w):
            return skript.anweisung(PROFIL, 'WeWork', [])


class Zeit(unittest.TestCase):
    def test_budget_reicht_fuer_langvideo(self):
        self.assertEqual(lauf.budget_fuer(PROFIL), lauf.BUDGET_LANG_S)
        self.assertGreaterEqual(lauf.BUDGET_LANG_S, 180 * 60)
        self.assertEqual(lauf.budget_fuer({'videoformat': 'short'}), lauf.BUDGET_S)

    def test_pilot_job_und_autor(self):
        yml = Path('.github/workflows/pilot.yml').read_text(encoding='utf-8')
        jobs = [int(m) for m in re.findall(r'timeout-minutes:\s*(\d+)', yml)]
        self.assertGreaterEqual(max(jobs), lauf.BUDGET_LANG_S / 60 + 15)
        self.assertLess(max(jobs), 360, 'GitHub beendet Jobs nach 6 h')
        self.assertIn('CLAUDE_CODE_OAUTH_TOKEN', yml)
        self.assertIn('@anthropic-ai/claude-code', yml)


if __name__ == '__main__':
    unittest.main()
