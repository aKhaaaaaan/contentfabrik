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

import kanalstandard
import vorrat

PROFIL = kanalstandard.laden('formate/business-origin-stories.json')


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



class ErbtShortEinstellungen(unittest.TestCase):
    """Alter Stand: formate/-Profil stand allein -> echte Fotos statt gemalt, Short-Skript aus dem Vorrat."""
    def test_alles_vom_kanal_ausser_format_und_laenge(self):
        kanal = kanalstandard.laden('kanaele/business-origin-stories.json')
        self.assertEqual(PROFIL['bildstil'], 'illustration')
        self.assertFalse(PROFIL['stockclips'])
        for feld in ('bildstil', 'hintergrund_suche', 'trend_suche', 'erzaehlstimme', 'youtube_kanal_id', 'name'):
            self.assertEqual(PROFIL[feld], kanal[feld], feld)
        self.assertEqual((PROFIL['videoformat'], kanal['videoformat']), ('lang', 'short'))

    def test_vorrat_gibt_kein_short_skript_fuer_langvideo(self):
        import datetime
        kurz = kanalstandard.laden('kanaele/business-origin-stories.json')
        echte = [json.loads(p.read_text(encoding='utf-8'))
                 for p in Path('vorrat/business-origin-stories').glob('*.json')]
        self.assertTrue(echte, 'Vorrat leer - Test braucht ein echtes Short-Skript')
        e = echte[0]
        # Die echten Eintraege sind fuer Orus etwas zu lang (207-211 > 180 Woerter) - auf
        # Short-Laenge kuerzen, damit die Kontrolle einen fuer Shorts GUELTIGEN Eintrag hat.
        woerter = ' '.join(t['text'] for t in e['skript']['teile']).split()[:170]
        e['skript']['teile'] = [dict(e['skript']['teile'][0], text=' '.join(woerter))]
        jetzt = datetime.datetime.fromisoformat(e['erstellt_utc']) + datetime.timedelta(hours=1)
        self.assertTrue(vorrat.gueltig(e, kurz, jetzt), 'Kontrolle: fuer den Short gueltig')
        self.assertFalse(vorrat.gueltig(e, PROFIL, jetzt))


if __name__ == '__main__':
    unittest.main()
