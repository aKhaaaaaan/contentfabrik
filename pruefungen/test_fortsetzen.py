"""Fortsetzen statt neu anfangen (Nutzerauftrag 09.10.2026, bezahlte Gemini-Stimme).

Alter Stand, den diese Tests erkennen:
- Fiel ein Stimmblock eines Langvideos aus, waren die schon bezahlten Bloecke verloren
  (kein Speicher je Block) und Kokoro sprach das ganze Video.
- Der Ton-Schluessel hing am ganzen bauen.py - jede Bild-Aenderung machte die Stimme ungueltig.
- Probelaeufe (CF_PILOT=1) setzten nie fort: weder Skript noch Teilbau noch Stimme.
"""
import io
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import bauen
import stimme_gemini

WURZEL = Path(__file__).resolve().parents[1]


def wav(sekunden=0.2, rate=24000):
    puffer = io.BytesIO()
    with wave.open(puffer, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(np.zeros(int(sekunden * rate), dtype=np.int16).tobytes())
    return puffer.getvalue()


class Stimmbloecke(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.speicher = patch.object(bauen, 'STIMM_SPEICHER', Path(self.tmp.name))
        self.speicher.start()
        # Vier Bloecke erzwingen: je Teil ein Block
        self.bloecke = patch.object(bauen, 'sprechbloecke', side_effect=lambda teile: list(teile))
        self.bloecke.start()
        self.s = {'teile': [{'text': f'Teil {i} erzaehlt etwas.'} for i in range(4)]}
        self.wahl = {'stimme': 'Orus', 'stil': 'warm', 'tempo': 1.0}

    def tearDown(self):
        self.bloecke.stop(); self.speicher.stop(); self.tmp.cleanup()

    def test_ausfall_in_block_3_kostet_beim_naechsten_versuch_nur_den_rest(self):
        aufrufe = []

        def erster(text, *a, **k):
            aufrufe.append(text)
            if len(aufrufe) == 3:
                raise RuntimeError('429 Kontingent')
            return wav(), 'gemini-3.8-flash-tts'
        with patch.object(stimme_gemini, 'sprechen', side_effect=erster):
            self.assertIsNone(bauen.gemini_ton(self.s, self.wahl, [1, 999]))
        zweite = []

        def zweiter(text, *a, **k):
            zweite.append(text)
            return wav(), 'gemini-3.8-flash-tts'
        with patch.object(stimme_gemini, 'sprechen', side_effect=zweiter):
            ton, rate = bauen.gemini_ton(self.s, self.wahl, [1, 999])
        self.assertEqual(zweite, ['Teil 2 erzaehlt etwas.', 'Teil 3 erzaehlt etwas.'])
        self.assertAlmostEqual(len(ton) / rate, 0.8, places=2)

    def test_vollstaendig_gespeichert_kostet_nichts(self):
        with patch.object(stimme_gemini, 'sprechen', return_value=(wav(), 'm')):
            bauen.gemini_ton(self.s, self.wahl, [1, 999])
        with patch.object(stimme_gemini, 'sprechen', side_effect=AssertionError('bezahlter Abruf')):
            self.assertIsNotNone(bauen.gemini_ton(self.s, self.wahl, [1, 999]))

    def test_andere_stimme_nutzt_den_speicher_nicht(self):
        with patch.object(stimme_gemini, 'sprechen', return_value=(wav(), 'm')):
            bauen.gemini_ton(self.s, self.wahl, [1, 999])
        with patch.object(stimme_gemini, 'sprechen', return_value=(wav(), 'm')) as neu:
            bauen.gemini_ton(self.s, dict(self.wahl, stimme='Charon'), [1, 999])
        self.assertEqual(neu.call_count, 4)


class TonSchluessel(unittest.TestCase):
    def test_stimmwahl_aendert_den_tonschluessel(self):
        self.assertNotEqual(bauen.stimm_code_key({'stimme': 'Orus', 'stil': 'a'}),
                            bauen.stimm_code_key({'stimme': 'Orus', 'stil': 'b'}))

    def test_bauen_nutzt_den_schmalen_schluessel(self):
        quelle = (WURZEL / 'fabrik/bauen.py').read_text(encoding='utf-8')
        self.assertNotIn('rendercache.audio_key(s, code_key)', quelle)
        self.assertIn('ton_key = stimm_code_key(wahl)', quelle)


class Probelauf(unittest.TestCase):
    def test_probelauf_setzt_fort(self):
        quelle = (WURZEL / 'fabrik/lauf.py').read_text(encoding='utf-8')
        self.assertNotIn("if not entwurf and os.environ.get('CF_PILOT') != '1':", quelle)
        self.assertNotIn("if os.environ.get('CF_PILOT') != '1' and (ordner / 'skript.json').exists():", quelle)

    def test_pilot_workflow_bewahrt_teilbau_und_stimme(self):
        yml = (WURZEL / '.github/workflows/pilot.yml').read_text(encoding='utf-8')
        self.assertEqual(yml.count('teilbau-pilot-v1-'), 3)  # restore key, restore-keys, save key
        self.assertEqual(yml.count('stimm-cache'), 2)
        self.assertIn('stimm-cache', (WURZEL / '.github/workflows/video.yml').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
