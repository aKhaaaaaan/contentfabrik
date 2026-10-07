"""Die beiden Abbrueche aus dem echten Lauf 37649294220 (07.10.2026)."""
import io
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
import autorenvergleich as av  # noqa: E402

STORY = {'type': 'OBJECT', 'properties': {
    'note': {'type': 'INTEGER'},
    'schwaechen': {'type': 'ARRAY', 'items': {'type': 'STRING'}}},
    'required': ['note', 'schwaechen']}


def groq_400(antwort):
    body = json.dumps({'error': {'message': "Generated JSON does not match the expected schema. "
                                 "jsonschema: '/schwaechen/0' ... got object",
                                 'failed_generation': json.dumps(antwort)}}).encode()
    return urllib.error.HTTPError('https://api.groq.com', 400, 'Bad Request', {}, io.BytesIO(body))


class GroqObjektStattText(unittest.TestCase):
    def setUp(self):
        av.GROQ_VERBRAUCH.clear()

    @patch.dict(os.environ, {'GROQ_API_KEY': 'x'})
    def test_story_pruefung_mit_objekt_schwaechen_wird_genutzt(self):
        # Vor dem Fix: RuntimeError 'Groq HTTP 400' -> Skript Code 1, kein Video.
        roh = {'note': 7, 'schwaechen': [{'kategorie': 'tempo', 'text': 'Mitte zieht sich'}]}
        with patch.object(av.urllib.request, 'urlopen', side_effect=groq_400(roh)):
            d, modell, _ = av.groq('p', STORY, ausgabe_tokens=100)
        self.assertEqual(d['schwaechen'], ['tempo - Mitte zieht sich'])
        self.assertEqual(d['note'], 7)

    @patch.dict(os.environ, {'GROQ_API_KEY': 'x'})
    def test_fehlendes_pflichtfeld_bleibt_fehler(self):
        with patch.object(av.urllib.request, 'urlopen', side_effect=groq_400({'schwaechen': []})):
            with self.assertRaises(RuntimeError):
                av.groq('p', STORY, ausgabe_tokens=100)


class Wortzeiten(unittest.TestCase):
    def test_gleicher_start_wird_gemeinsam_gezeigt(self):
        # Vor dem Fix: ValueError im Videobau, obwohl Skript und Pruefung bestanden.
        import bauen, tempfile
        w = [{'w': 'We', 's': 1.0, 'e': 1.2}, {'w': 'Work', 's': 1.2, 'e': 1.4},
             {'w': 'grew', 's': 1.2, 'e': 1.5}, {'w': 'fast.', 's': 1.6, 'e': 1.9}]
        with tempfile.TemporaryDirectory() as t:
            bauen.untertitel(w, Path(t) / 'u.ass')
            ass = (Path(t) / 'u.ass').read_text(encoding='utf-8')
        self.assertIn('WORK GREW', ass)
        self.assertIn('0:00:01.20,0:00:01.60', ass)  # keine erfundenen Zeiten


if __name__ == '__main__':
    unittest.main()
