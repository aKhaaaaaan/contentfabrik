"""Gemini-TTS-Antworten auswerten (ohne Netz). Format laut offizieller Doku 07.10.2026."""
import base64
import io
import json
import os
import sys
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
import stimme_gemini  # noqa: E402


def antwort(d):
    return io.BytesIO(json.dumps(d).encode())


class StimmeGeminiTest(unittest.TestCase):
    PCM = b'\x00\x01' * 2400

    def test_interactions_audio_wird_wav(self):
        d = {'steps': [{'type': 'model_output', 'content': [
            {'type': 'audio', 'data': base64.b64encode(self.PCM).decode()}]}]}
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'x'}), \
                patch('urllib.request.urlopen', return_value=antwort(d)) as up:
            wav, modell = stimme_gemini.sprechen('Hello <short pause> world.', 'Charon', 'calm suspense')
        body = json.loads(up.call_args.args[0].data)
        self.assertEqual(body['input'][0]['content'][0]['annotations'][0]['style'], 'calm suspense')
        self.assertEqual(body['input'][0]['content'][0]['text'], 'Hello <short pause> world.')
        self.assertEqual(modell, 'gemini-3.8-flash-tts')
        with wave.open(io.BytesIO(wav)) as w:
            self.assertEqual((w.getframerate(), w.getnchannels(), w.getnframes()), (24000, 1, 2400))

    def test_ausweg_alter_weg_mit_inlinedata(self):
        alt = {'candidates': [{'content': {'parts': [{'inlineData': {
            'mimeType': 'audio/L16;rate=24000', 'data': base64.b64encode(self.PCM).decode()}}]}}]}
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'x'}), \
                patch('urllib.request.urlopen', side_effect=[antwort({'steps': []}), antwort(alt)]):
            wav, modell = stimme_gemini.sprechen('Hi.', 'Charon')
        self.assertEqual(modell, 'gemini-2.5-flash-preview-tts')
        self.assertEqual(wav[:4], b'RIFF')

    def test_beide_wege_leer_ist_fehler(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'x'}), \
                patch('urllib.request.urlopen', side_effect=[antwort({}), antwort({})]):
            with self.assertRaises(RuntimeError):
                stimme_gemini.sprechen('Hi.')
