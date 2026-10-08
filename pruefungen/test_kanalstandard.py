"""Kanal-Grundeinstellungen (Nutzerwunsch 08.10.2026): Tempo und Bewaehrtes gelten fuer ALLE
Kanaele, auch zukuenftige - ein neuer Kanal braucht nur ein kurzes Profil, keine Codeaenderung.

Alter Stand, den diese Tests erkennen: Ein neuer Kanal ohne 'erzaehlstimme' bekam die alte
Kokoro-Stimme statt Orus/Tempo 1.08, Wortrate 2.4 statt ~2.1, Stockclips, keine YouTube-Kategorie
und war per Telegram nicht ansprechbar (Kanalliste fest im Code).
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import bauen
import hochladen
import kanalstandard
import skript
import themen

NEU = {'name': 'Sports Legends', 'format': 'geschichte', 'telegram_kuerzel': ['sport'],
       'beschreibung_kurz': 'sports history'}


class NeuerKanal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = Path(self.tmp.name)
        for p in Path('kanaele').glob('*.json'):
            (self.ordner / p.name).write_text(p.read_text(encoding='utf-8'), encoding='utf-8')
        (self.ordner / 'sports-legends.json').write_text(json.dumps(NEU), encoding='utf-8')
        self.p = patch.object(kanalstandard, 'ORDNER', self.ordner)
        self.p.start()
        # Standardargument wurde beim Import gebunden -> nach_name/alle ebenfalls umlenken
        self.alle = kanalstandard.alle
        self.p2 = patch.object(kanalstandard, 'alle', lambda ordner=None: self.alle(self.ordner))
        self.p2.start()

    def tearDown(self):
        self.p2.stop()
        self.p.stop()
        self.tmp.cleanup()

    def test_erbt_orus_und_tempo(self):
        st = bauen.erzaehlstimme({'kanal': 'Sports Legends'})
        self.assertEqual((st['anbieter'], st['stimme'], st['tempo']), ('gemini', 'Orus', 1.08))

    def test_keine_stockclips(self):
        self.assertFalse(bauen.stockclips_erlaubt({'kanal': 'Sports Legends'}))

    def test_wortrate_passt_zu_orus(self):
        self.assertEqual(skript.wortrate(kanalstandard.profil(NEU)), 2.1)
        self.assertEqual(skript.wortrate({}), 2.1)

    def test_youtube_kategorie(self):
        self.assertEqual(hochladen.kategorie('Sports Legends'), '27')
        self.assertEqual(hochladen.kategorie('AI Tools Explained'), '28')

    def test_telegram_kennt_neuen_kanal(self):
        self.assertIn('sports-legends', themen._kanaele())
        self.assertEqual(themen._kanaele()['sports-legends'], ('sport',))

    def test_profil_hat_vorrang(self):
        d = kanalstandard.profil({'erzaehlstimme': {'stimme': 'Charon'}})
        self.assertEqual((d['erzaehlstimme']['stimme'], d['erzaehlstimme']['tempo']), ('Charon', 1.08))


class BestehendeKanaele(unittest.TestCase):
    def test_tempo_ueberall(self):
        for slug, d in kanalstandard.alle().items():
            self.assertEqual(d['erzaehlstimme']['tempo'], 1.08, slug)

    def test_telegram_kuerzel_wie_bisher(self):
        k = themen._kanaele()
        self.assertIn('ki', k['ai-tools-explained'])
        self.assertIn('business', k['business-origin-stories'])

    def test_unbekannter_kanal_ohne_profil(self):
        self.assertIsNone(bauen.erzaehlstimme({'kanal': 'Gibt es nicht'}))



class Zeitbudget(unittest.TestCase):
    """Nutzerentscheidung 08.10.: Repo oeffentlich -> 90 Min je Kanal. Alter Stand 45 Min / Job 60 Min."""
    def test_budget_90_und_job_passt(self):
        import re
        import lauf
        self.assertEqual(lauf.BUDGET_S, 90 * 60)
        yml = Path('.github/workflows/video.yml').read_text(encoding='utf-8')
        jobs = [int(m) for m in re.findall(r'timeout-minutes:\s*(\d+)', yml)]
        self.assertTrue(any(m >= lauf.BUDGET_S / 60 + 15 for m in jobs), jobs)


if __name__ == '__main__':
    unittest.main()
