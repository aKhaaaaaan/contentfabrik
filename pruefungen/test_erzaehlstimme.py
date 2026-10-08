"""Gemini-Erzaehlstimme im Videobau (Nutzerwahl 07.10.2026: Stimme 4 = Orus)."""
import io
import json
import shutil
import sys
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
import bauen  # noqa: E402

WURZEL = Path(__file__).resolve().parents[1]


def wav(sekunden, rate=24000):
    puffer = io.BytesIO()
    with wave.open(puffer, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        t = np.arange(int(sekunden * rate)) / rate
        w.writeframes((np.sin(2 * np.pi * 220 * t) * 8000).astype(np.int16).tobytes())
    return puffer.getvalue()


SKRIPT = {'kanal': 'Business Origin Stories', 'teile': [
    {'text': 'In 2019 one office company was worth billions.'},
    {'text': 'Then everything changed.', 'beat': 'wendung'}]}


class FigurNurEinmalTest(unittest.TestCase):
    """Lauf 37760482364: 7 teure Einsetzversuche der Figur, Bau im Zeitlimit."""

    def setUp(self):
        bauen.FIGUR_EINSETZEN['moeglich'] = True

    tearDown = setUp

    def test_nach_erstem_fehlschlag_kein_einsetzversuch_mehr(self):
        import illustration
        aufrufe = []
        def bild(szene, ziel, kanal, figur=False, videoformat='short'):
            aufrufe.append(figur)
            return None if figur else Path('szene.jpg')
        with patch.object(illustration, 'bild', side_effect=bild):
            for _ in range(5):
                bauen.illustration_mit_ausweg('x', 'x.jpg', 'k', True, False, 'short')
        self.assertEqual(aufrufe.count(True), 1)
        self.assertEqual(aufrufe.count(False), 5)


class ErzaehlstimmeTest(unittest.TestCase):
    def test_beide_kanaele_haben_orus(self):
        # Vor dem Einbau sprach immer Kokoro (keine Regie moeglich).
        for k in ('business-origin-stories', 'ai-tools-explained'):
            d = json.loads((WURZEL / f'kanaele/{k}.json').read_text(encoding='utf-8'))
            self.assertEqual((d['erzaehlstimme']['anbieter'], d['erzaehlstimme']['stimme']), ('gemini', 'Orus'))

    def test_ein_aufruf_mit_pause_vor_wendung(self):
        with patch('stimme_gemini.sprechen', return_value=(wav(5), 'gemini-3.8-flash-tts')) as sp:
            ton, rate = bauen.gemini_ton(SKRIPT, {'stimme': 'Orus', 'stil': 'dramatic'}, [62, 90])
        self.assertEqual(sp.call_count, 1)
        self.assertEqual(sp.call_args.args[0], 'In 2019 one office company was worth billions. '
                                               '<short pause> Then everything changed.')
        self.assertEqual((rate, round(len(ton) / rate)), (24000, 5))

    def test_ausfall_faellt_auf_kokoro_zurueck(self):
        with patch('stimme_gemini.sprechen', side_effect=RuntimeError('429 quota')):
            self.assertIsNone(bauen.gemini_ton(SKRIPT, {'stimme': 'Orus'}, [62, 90]))

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg fehlt lokal')
    def test_zu_lang_wird_hoechstens_um_15_prozent_gestrafft(self):
        with patch('stimme_gemini.sprechen', return_value=(wav(100), 'gemini-3.8-flash-tts')):
            ton, rate = bauen.gemini_ton(SKRIPT, {'stimme': 'Orus'}, [62, 90])
        self.assertAlmostEqual(len(ton) / rate, 100 / 1.111, delta=0.5)
        with patch('stimme_gemini.sprechen', return_value=(wav(120), 'gemini-3.8-flash-tts')):
            ton, rate = bauen.gemini_ton(SKRIPT, {'stimme': 'Orus'}, [62, 90])
        self.assertAlmostEqual(len(ton) / rate, 120 / 1.15, delta=0.5)

    def test_abschnitte_aus_wortzeiten(self):
        teile = [{'text': 'a b c'}, {'text': 'd e'}, {'text': 'f'}]
        woerter = [{'w': w, 's': s, 'e': s + .3} for w, s in zip('abcdef', [0, .4, .8, 2.0, 2.4, 3.5])]
        self.assertEqual(bauen.laengen_aus_woertern(woerter, teile, 5.0), [2.0, 1.5, 1.5])
