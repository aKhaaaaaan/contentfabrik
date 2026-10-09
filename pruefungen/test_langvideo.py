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



class Pilot37826232160(unittest.TestCase):
    """Echte Fehler des ersten vollstaendigen Langvideo-Laufs (5 Versuche, kein Video)."""
    def test_null_dauer_folge_bricht_nicht_ab(self):
        import tempfile
        w = [{'w': 'The', 's': 10.0, 'e': 10.3}, {'w': 'company', 's': 10.3, 'e': 10.8}]
        w += [{'w': x, 's': 10.8, 'e': 10.8} for x in ('had', 'no', 'money', 'left')]
        w += [{'w': 'Then', 's': 12.4, 'e': 12.7}, {'w': 'everything', 's': 12.7, 'e': 13.2}]
        with tempfile.TemporaryDirectory() as d:
            ziel = Path(d) / 'u.ass'
            bauen.untertitel(w, ziel)
            text = ziel.read_text(encoding='utf-8').upper()
        for wort in ('MONEY', 'LEFT', 'THEN'):
            self.assertIn(wort, text)
        verteilt = bauen.verteilen(w[2:6], 12.4)
        self.assertEqual((verteilt[0]['s'], verteilt[-1]['e']), (10.8, 12.4))
        self.assertTrue(all(a['e'] <= b['s'] + 1e-9 and a['s'] < a['e'] for a, b in zip(verteilt, verteilt[1:])))

    def test_null_dauer_am_ende(self):
        import tempfile
        w = [{'w': 'Save', 's': 1.0, 'e': 1.4}] + [{'w': x, 's': 2.5, 'e': 2.5} for x in ('this', 'video')]
        with tempfile.TemporaryDirectory() as d:
            bauen.untertitel(w, Path(d) / 'u.ass')

    def test_bildplan_in_etappen_mit_wiederholung(self):
        import bildplan
        zeitplan = [{'index': i} for i in range(85)]
        teile = bildplan.etappen(zeitplan)
        self.assertEqual([len(t) for t in teile], [30, 30, 25])
        self.assertEqual(len(bildplan.etappen(zeitplan[:24])), 1, 'Short bleibt ein Auftrag')
        antworten = [({'einstellungen': [{'index': 0}]}, 'lite'),            # zu kurz (wie gemessen)
                     ({'einstellungen': [{'index': 0}, {'index': 1}]}, 'lite')]
        gemini = lambda *a, **k: antworten.pop(0)
        self.assertEqual(len(bildplan._planen(gemini, [], 'x', [0, 1])), 2)



class Pilot37831023275(unittest.TestCase):
    """Dritter Langvideo-Lauf: Skript 8/10 bestanden, Bau scheiterte an Ersatzbildern;
    die Telegram-Meldung klang, als sei 8/10 durchgefallen."""
    def test_ersatzbilder_wachsen_mit_der_laenge(self):
        self.assertEqual(bauen.ersatz_grenze(24), 2)
        self.assertGreaterEqual(bauen.ersatz_grenze(85), 5)

    def test_kanalfigur_als_letzter_ausweg(self):
        self.assertTrue(bauen.illustration_figur('business-origin-stories'))
        self.assertIsNone(bauen.illustration_figur('gibt-es-nicht'))

    def test_bestandene_note_klingt_bestanden(self):
        import tempfile
        import statusmeldung
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'bericht.json').write_text(json.dumps({'grund': 'Videobau fehlgeschlagen'}), encoding='utf-8')
            Path(d, 'skript.json').write_text(json.dumps({'pruefung': {'ok': True, 'probleme': []},
                                                          'story': {'note': 8}}), encoding='utf-8')
            text = statusmeldung.fehlergrund(d)
        self.assertIn('Skript bestanden', text)
        self.assertNotIn('erforderlich mindestens', text)



class Pilot37840254844(unittest.TestCase):
    """Startmeldung brach ab: verschachteltes Feld als Python-Text statt JSON an Telegram."""
    def test_verschachtelte_felder_als_json(self):
        import os
        from unittest.mock import patch, MagicMock
        import freigabe
        gesendet = {}

        def urlopen(req, timeout=0):
            gesendet['body'] = req.data.decode()
            antwort = MagicMock()
            antwort.__enter__.return_value.read.return_value = b'{"ok": true}'
            return antwort
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 't'}), patch('urllib.request.urlopen', urlopen),                 patch('json.load', lambda r: {'ok': True}):
            freigabe.telegram('sendMessage', {'chat_id': '1', 'text': 'x',
                                              'link_preview_options': {'is_disabled': True}})
        self.assertIn('{"is_disabled": true}', gesendet['body'])
        self.assertNotIn("{'is_disabled': True}", gesendet['body'])


if __name__ == '__main__':
    unittest.main()
