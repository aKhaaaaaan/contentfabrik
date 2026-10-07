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


class FigurAusweg(unittest.TestCase):
    """Vor dem Fix: Einstellung 0 ohne Bild -> 'kein passendes Hauptbild', kein Video."""

    def test_anfang_nimmt_originalfigur(self):
        import bauen, illustration
        with patch.object(illustration, 'bild', return_value=None) as bild:
            ill = bauen.illustration_mit_ausweg('office', 'x.jpg', 'business-origin-stories', True, True, 'short')
        self.assertEqual(ill, illustration.FIGUREN / 'business-origin-stories.jpg')
        self.assertTrue(ill.is_file())
        self.assertEqual(bild.call_count, 1)

    def test_mitte_nimmt_szene_ohne_figur(self):
        import bauen, illustration
        with patch.object(illustration, 'bild', side_effect=[None, Path('szene.jpg')]) as bild:
            ill = bauen.illustration_mit_ausweg('office', 'x.jpg', 'business-origin-stories', True, False, 'short')
        self.assertEqual(ill, Path('szene.jpg'))
        self.assertFalse(bild.call_args.kwargs['figur'])

    def test_ohne_figur_kein_zweiter_versuch(self):
        import bauen, illustration
        with patch.object(illustration, 'bild', return_value=None) as bild:
            self.assertIsNone(bauen.illustration_mit_ausweg('x', 'x.jpg', 'k', False, True, 'short'))
        self.assertEqual(bild.call_count, 1)


class Wortgrenze(unittest.TestCase):
    def test_short_hoechstens_216_woerter(self):
        # Vor dem Fix: 90 s * 2.9 = 261 Woerter erlaubt -> 117 s Ton, Tempo 1.25.
        quelle = (Path(__file__).resolve().parents[1] / 'fabrik' / 'skript.py').read_text(encoding='utf-8')
        self.assertIn('(2.65 if lang else 2.4)', quelle)


if __name__ == '__main__':
    unittest.main()
