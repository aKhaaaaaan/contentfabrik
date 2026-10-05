"""Quellenqualitaet und vergleichbare Ranglisten ohne Netzwerk."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
import trends
import skript


class QuellenTest(unittest.TestCase):
    def test_beschreibung_ist_beleg_code_und_tabellen_nicht(self):
        q = {'quelle': 'Hugging Face', 'name': 'owner/model', 'text': '500 likes', 'zahl': 500}
        roh = '---\nlicense: custom\n---\n' + 'A tool for editing images with reference photos. ' * 12
        roh += '\n```python\nsecret looking code\n```\n| score | 99 |\n'
        with patch('trends._hole', return_value=roh.encode()):
            neu = trends.beschreibung(q)
        self.assertTrue(neu['belegt'])
        self.assertIn('reference photos', neu['text'])
        self.assertNotIn('secret looking code', neu['text'])
        self.assertNotIn('| score', neu['text'])
        self.assertNotIn('belegt', q)

    def test_abrufausfall_und_duenne_beschreibung_bleiben_unbelegt(self):
        q = {'quelle': 'GitHub', 'name': 'owner/repo', 'text': '1000 stars'}
        with patch('trends._hole', side_effect=TimeoutError):
            self.assertNotIn('belegt', trends.beschreibung(q))
        with patch('trends._hole', return_value=b'# empty repo'):
            self.assertNotIn('belegt', trends.beschreibung(q))

    def test_rangliste_mischt_niemals_sterne_und_likes(self):
        hf = [{'quelle': 'Hugging Face', 'zahl': n, 'belegt': True} for n in (40, 120, 80)]
        gh = [{'quelle': 'GitHub', 'zahl': 9000, 'belegt': True}]
        duenn = {'quelle': 'Hugging Face', 'zahl': 10000}
        liste = skript.rangliste(hf + gh + [duenn], {'plaetze': [3, 5]})
        self.assertEqual([q['zahl'] for q in liste], [120, 80, 40])
        self.assertEqual(skript.rangliste([duenn], {}), [])


if __name__ == '__main__':
    unittest.main()
