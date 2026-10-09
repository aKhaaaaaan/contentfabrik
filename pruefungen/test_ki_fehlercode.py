"""Gemini-Fehler mit HTTP-Code im Log (09.10.2026: 20x nur „HTTPError" im Langvideo-Pilot).

Alter Stand, den dieser Test erkennt: Kontingent (429), Ueberlast (503) und abgelehnte
Anfrage (400) sahen im Log gleich aus.
"""
import io
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import skript


class Fehlercode(unittest.TestCase):
    def test_http_code_steht_im_log(self):
        fehler = urllib.error.HTTPError('https://x', 503, 'busy', {}, io.BytesIO(b'{}'))
        aus = io.StringIO()
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'k'}), \
                patch('urllib.request.urlopen', side_effect=fehler), \
                patch('ki_speicher.sperre', return_value=None), patch('ki_speicher.sperren'), \
                redirect_stdout(aus), self.assertRaises(RuntimeError):
            skript._gemini('p', {'type': 'OBJECT'}, modelle=['gemini-test'], anfrage_s=5)
        self.assertIn('gemini-test; HTTPError 503', aus.getvalue())
        self.assertNotIn('key=k', aus.getvalue())


if __name__ == '__main__':
    unittest.main()
