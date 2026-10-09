"""Ersatzstimme sichtbar machen (09.10.2026, bezahlte Orus-Stimme mit 5-EUR-Limit).

Alter Stand, den diese Tests erkennen: Fiel Gemini-Orus aus (Kontingent, Limit, Netz), sprach
Kokoro das Video - messung.json und Telegram verschwiegen es. Der Nutzer haette ein Video mit
der flachen Ersatzstimme hochgeladen, ohne es zu wissen.
"""
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import test_betrieb
from test_betrieb import KRITIK, SKRIPT, TEST_SHA, TempTest, audio_fixture
import freigabe

WURZEL = Path(__file__).resolve().parents[1]


class Ersatzstimme(TempTest):
    def caption(self, messung):
        Path('skript.json').write_text(json.dumps(SKRIPT), encoding='utf-8')
        Path('kritik.json').write_text(json.dumps(dict(KRITIK, audio_pruefung=audio_fixture(TEST_SHA, 'short'))),
                                       encoding='utf-8')
        Path('video.mp4').write_bytes(b'gepruefter-testfilm')
        if messung is not None:
            Path('messung.json').write_text(json.dumps(messung), encoding='utf-8')
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': 'test', 'CF_ORIGINAL_URL': ''}), \
                patch('freigabe.telegram', return_value={'ok': True}) as tg:
            freigabe.senden('skript.json', 'video.mp4')
        return next(c.args[1]['caption'] for c in tg.call_args_list if 'caption' in c.args[1])

    def test_ersatzstimme_wird_im_video_angezeigt(self):
        self.assertIn('ERSATZSTIMME Kokoro', self.caption({'stimme_ersatz': True, 'erzaehlstimme': 'kokoro:bm_george'}))

    def test_orus_ohne_warnung(self):
        self.assertNotIn('ERSATZSTIMME', self.caption({'stimme_ersatz': False, 'erzaehlstimme': 'gemini:Orus'}))

    def test_ohne_messung_keine_falsche_warnung(self):
        self.assertNotIn('ERSATZSTIMME', self.caption(None))


class Messung(unittest.TestCase):
    def test_bauen_haelt_die_echte_stimme_fest(self):
        quelle = (WURZEL / 'fabrik/bauen.py').read_text(encoding='utf-8')
        self.assertIn("zeiten['erzaehlstimme'] = f\"gemini:", quelle)
        self.assertIn("zeiten['erzaehlstimme'] = f\"kokoro:", quelle)
        self.assertIn("zeiten['stimme_ersatz'] = bool(", quelle)
        self.assertIn("'erzaehlstimme': zeiten.get('erzaehlstimme', '?')", quelle)  # auch bei Ton aus dem Cache


if __name__ == '__main__':
    unittest.main()
