"""TikTok-Erinnerung ab 8.000 Followern (Nutzerwunsch 10.10.2026: „irgendwo dokumentieren, dass wir
umstellen muessen, wenn wir die Zahlen bei TikTok erreichen - Erinnerung").

Alter Stand, den diese Tests erkennen: es gab keinen Waechter und keine Erinnerung.
"""
import json
from pathlib import Path
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
from test_betrieb import TempTest
import tiktok_schwelle

WURZEL = Path(__file__).resolve().parents[1]


class Schwelle(TempTest):
    def test_meldet_genau_einmal_ab_schwelle(self):
        gesendet = []
        with patch.object(tiktok_schwelle, 'follower', return_value=8123):
            erst = tiktok_schwelle.pruefen({'business-origin-stories': 'b'}, senden=lambda t: gesendet.append(t) or True)
            zweit = tiktok_schwelle.pruefen({'business-origin-stories': 'b'}, senden=lambda t: gesendet.append(t) or True)
        self.assertEqual((erst, zweit), (['business-origin-stories'], []))
        self.assertEqual(len(gesendet), 1)
        self.assertIn('ueber 1 Minute', gesendet[0])

    def test_unter_schwelle_nur_verlauf(self):
        with patch.object(tiktok_schwelle, 'follower', return_value=21):
            self.assertEqual(tiktok_schwelle.pruefen({'ai-tools-explained': 'a'}, senden=lambda t: 1 / 0), [])
        verlauf = json.loads(tiktok_schwelle.DATEI.read_text(encoding='utf-8'))['verlauf']
        self.assertEqual(verlauf[-1]['follower'], 21)

    def test_abrufausfall_schadet_nicht(self):
        with patch.object(tiktok_schwelle, 'follower', return_value=None):
            self.assertEqual(tiktok_schwelle.pruefen({'x': 'y'}, senden=lambda t: 1 / 0), [])

    def test_kanaele_und_workflow_eingetragen(self):
        Path('kanaele').mkdir(exist_ok=True)
        for k in ('ai-tools-explained', 'business-origin-stories'):
            profil = json.loads((WURZEL / f'kanaele/{k}.json').read_text(encoding='utf-8'))
            self.assertTrue(profil.get('tiktok_name'), k)
        self.assertIn('python3 fabrik/tiktok_schwelle.py', (WURZEL / '.github/workflows/themen.yml').read_text(encoding='utf-8'))
