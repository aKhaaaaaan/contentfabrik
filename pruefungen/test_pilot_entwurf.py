"""Ein redaktioneller Entwurf darf keine alte oder erfundene Freigabe uebernehmen."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
from test_betrieb import TempTest, SKRIPT
import pilot_entwurf
import prompts


class PilotEntwurfTest(TempTest):
    def setUp(self):
        super().setUp()
        self.s = copy.deepcopy(SKRIPT)
        self.s['teile'] = [{'text': 'One supported claim. ' * 60}]
        Path('vorlage.json').write_text(json.dumps(self.s), encoding='utf-8')
        Path('profil.json').write_text(json.dumps({'name': 'Test', 'videoformat': 'short'}), encoding='utf-8')

    def pruefen(self, note=9):
        def check(s):
            self.assertIsNone(s.get('story'))
            self.assertIs(s['pruefung']['ok'], False)
            s['pruefung'] = {'ok': True}
            s['story'] = dict(self.s['story'], note=note)
        with patch('pilot_entwurf.nachbessern.faktencheck', side_effect=check) as fakten:
            code = pilot_entwurf.main('vorlage.json', 'profil.json', 'ausgabe/skript.json')
        fakten.assert_called_once()
        return code

    def test_auch_vorgepruefter_entwurf_braucht_neue_fakten_und_story(self):
        self.assertEqual(self.pruefen(), 0)
        s = json.loads(Path('ausgabe/skript.json').read_text())
        self.assertEqual(s['prompt_version'], prompts.VERSION)

    def test_story_acht_sperrt_den_redaktionellen_entwurf(self):
        self.assertEqual(self.pruefen(8), 3)

    def test_faktenfehler_speichert_sperre_statt_urspruenglicher_freigabe(self):
        with patch('pilot_entwurf.nachbessern.faktencheck', side_effect=ValueError('Falsche Zahl')):
            self.assertEqual(pilot_entwurf.main('vorlage.json', 'profil.json', 'ausgabe/skript.json'), 2)
        self.assertFalse(json.loads(Path('ausgabe/skript.json').read_text())['pruefung']['ok'])

    def test_falscher_kanal_wird_vor_ki_abgelehnt(self):
        Path('profil.json').write_text(json.dumps({'name': 'Anderer Kanal'}), encoding='utf-8')
        with patch('pilot_entwurf.nachbessern.faktencheck') as fakten, self.assertRaises(ValueError):
            pilot_entwurf.main('vorlage.json', 'profil.json', 'ausgabe/skript.json')
        fakten.assert_not_called()

    def test_faktencheck_behaelt_titel_und_sprache_aber_keine_illustrative_regie(self):
        p = prompts.fakten('SOURCED_EVIDENCE', {'titel': ['FACTUAL_TITLE'],
                           'beschreibung': 'FACTUAL_DESCRIPTION', 'teile': [{
                           'text': 'SPOKEN_CLAIM', 'szene': 'UNSOURCED_SCENE_ONLY', 'suche': 'STOCK_SEARCH_ONLY'}]})
        self.assertIn('FACTUAL_TITLE', p)
        self.assertIn('FACTUAL_DESCRIPTION', p)
        self.assertIn('SPOKEN_CLAIM', p)
        self.assertNotIn('UNSOURCED_SCENE_ONLY', p)
        self.assertNotIn('STOCK_SEARCH_ONLY', p)
