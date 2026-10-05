import json
import unittest
from pathlib import Path
from unittest.mock import patch
import bibliothek
import bildplan
import pilot_bildregie


class BibliothekTest(unittest.TestCase):
    def test_nur_unveraenderte_sichtkontrollierte_kanalbilder(self):
        for b in bibliothek.katalog():
            self.assertTrue(bibliothek.bild(b['id'], b['kanal']).is_file())
            falsch = 'Business Origin Stories' if b['kanal'] == 'AI Tools Explained' else 'AI Tools Explained'
            with self.assertRaises(ValueError):
                bibliothek.bild(b['id'], falsch)
        with self.assertRaises(ValueError):
            bibliothek.bild('../../figuren/ai-tools-explained.jpg', 'AI Tools Explained')

    def test_dateiaenderung_uebernimmt_keine_fruehere_sichtkontrolle(self):
        b = dict(bibliothek.katalog()[0], sha256='unapproved')
        with patch('bibliothek.katalog', return_value=[b]), self.assertRaises(ValueError):
            bibliothek.bild(b['id'], b['kanal'])

    def test_ai_regie_deckt_gemessene_stimme_ohne_bild_api_ab(self):
        s = json.loads((Path(__file__).resolve().parents[1]/'piloten/qwen-bildworkflow.json').read_text(encoding='utf8'))
        laengen = [8.98,9.25,11.22,12.32,10.53,11.68,9.19,9.02]
        with patch('skript.gemini') as ki:
            shots, _ = bildplan.vorbereiten(s, laengen, [])
        ki.assert_not_called()
        self.assertEqual(len(shots), 23)
        self.assertNotIn('illustration', {shot['teil']['bildmodus'] for shot in shots})
        self.assertEqual(shots[0]['teil']['asset'], 'ai-presenter-workflow')
        demos = [x['teil']['demo_url'] for x in shots if x['teil']['bildmodus'] == 'demo']
        self.assertEqual(len(demos), len(set(demos)))
        self.assertAlmostEqual(sum(x['dauer_s'] for x in shots), sum(laengen))

    def test_zu_kurze_regie_stoppt_statt_unpassende_bilder_nachzufuellen(self):
        s = {'kanal': 'AI Tools Explained', 'teile': [{'text': 'Long narration',
             'bildfolge': [pilot_bildregie.asset('ai-layers', 'Layers')]}]}
        with patch('skript.gemini') as ki, self.assertRaises(ValueError):
            bildplan.vorbereiten(s, [20], [])
        ki.assert_not_called()
