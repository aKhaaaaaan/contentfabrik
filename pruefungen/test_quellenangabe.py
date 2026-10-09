"""Quellenangabe nur fuer wirklich verwendetes Material (09.10.2026).

Alter Stand, den diese Tests erkennen: skript.py haengte „Clips: Pixabay" an JEDE Beschreibung.
Das Netflix-Langvideo (94 gemalte Illustrationen, kein Clip) trug die falsche Angabe auf YouTube.
"""
import json
import os
from pathlib import Path
from unittest.mock import patch

import test_betrieb
from test_betrieb import KRITIK, SKRIPT, TEST_SHA, TempTest, audio_fixture
import freigabe

WURZEL = Path(__file__).resolve().parents[1]


class Quellenangabe(TempTest):
    def texte(self, quellen):
        Path('skript.json').write_text(json.dumps(dict(SKRIPT, beschreibung='Two facts.')), encoding='utf-8')
        Path('kritik.json').write_text(json.dumps(dict(KRITIK, audio_pruefung=audio_fixture(TEST_SHA, 'short'))),
                                       encoding='utf-8')
        Path('quellen.json').write_text(json.dumps(quellen), encoding='utf-8')
        Path('video.mp4').write_bytes(b'gepruefter-testfilm')
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': 'test', 'CF_ORIGINAL_URL': ''}), \
                patch('freigabe.telegram', return_value={'ok': True}) as tg:
            freigabe.senden('skript.json', 'video.mp4')
        return ' '.join(str(c.args[1].get('text', '')) for c in tg.call_args_list)

    def test_ohne_clip_keine_pixabay_angabe(self):
        self.assertNotIn('Pixabay', self.texte([{'quelle': 'Illustration', 'seite': 'KI-generiert'}]))

    def test_mit_clip_steht_die_angabe(self):
        self.assertIn('Clips: Pixabay', self.texte([{'quelle': 'Pixabay', 'id': 3, 'seite': 'x'}]))

    def test_skript_setzt_die_angabe_nicht_mehr_pauschal(self):
        quelle = (WURZEL / 'fabrik/skript.py').read_text(encoding='utf-8')
        self.assertNotIn("entwurf['beschreibung'] + '\\nClips: Pixabay'", quelle)
