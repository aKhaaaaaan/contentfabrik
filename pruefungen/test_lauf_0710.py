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
    def test_liste_statt_text_wird_angeglichen(self):
        # Run 37659694533: '/teile/0/suche' expected string, but got array -> kein Skript.
        schema = {'type': 'OBJECT', 'properties': {'teile': {'type': 'ARRAY', 'items': {
            'type': 'OBJECT', 'properties': {'suche': {'type': 'STRING'}}, 'required': ['suche']}}},
            'required': ['teile']}
        roh = {'teile': [{'suche': ['coworking office', 'empty desks']}]}
        with patch.object(av.urllib.request, 'urlopen', side_effect=groq_400(roh)):
            d, _, _ = av.groq('p', schema, ausgabe_tokens=100)
        self.assertEqual(d['teile'][0]['suche'], 'coworking office, empty desks')

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


class Fesseln(unittest.TestCase):
    """Nutzerwunsch: nicht wegwischen. Vorher 1 s Einblenden, keine Stille vor der Wendung.
    Mit echtem ffmpeg 7.1 nachgemessen: Pegel ab 0,05 s voll, 5,45-6,0 s exakt 0."""

    def test_musik_sofort_und_still_vor_wendung(self):
        import bauen
        k = bauen.musik_kette(0.1, 80, [30.0])
        self.assertIn('afade=t=in:d=0.05', k)
        self.assertNotIn('afade=t=in:d=1,', k)
        self.assertIn("volume=0:enable='between(t,29.450,30.000)'", k)

    def test_keine_pause_am_anfang_oder_ende(self):
        import bauen
        self.assertNotIn('enable', bauen.musik_kette(0.1, 80, [1.0, 79.5]))

    def test_skriptauftrag_verlangt_wendung_ohne_begruessung(self):
        import dramaturgie
        a = dramaturgie.auftrag({'videoformat': 'short'})
        self.assertIn('beat wendung', a)
        self.assertIn('No greeting', a)
        self.assertIn('like', a.lower())  # Like/Teilen/Speichern bleibt Pflicht


class Geraeusche(unittest.TestCase):
    """Passende Geraeusche nur CC0 von Freesound; Ausfall kippt nie das Video.
    Live geprueft 07.10.: 'cash register' -> Freesound CC0, Pegel 3,15-4,65 s, weich aus."""

    def antwort(self, results):
        return io.BytesIO(json.dumps({'results': results}).encode())

    def test_nur_cc0_freesound_kurz(self):
        import bauen, tempfile
        results = [{'id': 'a', 'license': 'by', 'source': 'freesound', 'url': 'https://cdn.example/s.mp3', 'duration': 2000, 'title': 'x'},
                   {'id': 'b', 'license': 'cc0', 'source': 'jamendo', 'url': 'https://cdn.example/s.mp3', 'duration': 2000, 'title': 'x'},
                   {'id': 'c', 'license': 'cc0', 'source': 'freesound', 'url': 'https://cdn.example/s.mp3', 'duration': 900_000, 'title': 'x'},
                   {'id': 'd', 'license': 'cc0', 'source': 'freesound', 'url': 'https://cdn.example/s.mp3', 'duration': 3000,
                    'title': 'Cash register music loop'},
                   {'id': 'ok', 'license': 'cc0', 'source': 'freesound', 'url': 'https://cdn.example/s.mp3', 'duration': 3000,
                    'title': 'Cash register', 'creator': 'someone'}]
        with tempfile.TemporaryDirectory() as t, patch.object(bauen, 'PIXABAY_CACHE', Path(t)), \
                patch('urllib.request.urlopen', side_effect=[self.antwort(results), io.BytesIO(b'mp3')]):
            pfad, nennung = bauen.geraeusch_holen('cash register')
            self.assertEqual(pfad.name, 'geraeusch_ok.mp3')
        self.assertIn('CC0', nennung)

    def test_ausfall_liefert_nichts_statt_fehler(self):
        import bauen
        with patch('urllib.request.urlopen', side_effect=OSError('offline')):
            self.assertEqual(bauen.geraeusch_holen('crowd cheering'), (None, None))
        self.assertEqual(bauen.geraeusch_holen(''), (None, None))

    def test_skript_darf_geraeusch_nennen(self):
        import skript, dramaturgie
        teil = skript.SKRIPT_SCHEMA['properties']['teile']['items']['properties']
        self.assertIn('geraeusch', teil)
        self.assertIn('geraeusch', dramaturgie.auftrag({'videoformat': 'short'}))


class KeineBildschirme(unittest.TestCase):
    def test_szenenregel_verbietet_bildschirm_als_motiv(self):
        # Vor dem Fix verlangten Bildplaene Dashboards/Monitore -> lesbare Zahlen, Bilder verworfen.
        import prompts
        self.assertIn('Never make a screen', prompts.SZENEN)
        self.assertIn('physical', prompts.SZENEN)


class BildkontingentLeer(unittest.TestCase):
    """Lauf 37749486997: 'free allocation used up' -> 5 sinnlose Bauversuche."""

    def test_erster_fehler_setzt_merker_und_spart_weitere_anfragen(self):
        import illustration, tempfile
        body = json.dumps({'success': False, 'errors': [{'message': "AiError: you have used up your daily "
                           "free allocation of 10,000 neurons, please upgrade"}]}).encode()
        fehler = urllib.error.HTTPError('https://api.cloudflare.com', 429, 'x', {}, io.BytesIO(body))
        alt = os.getcwd()
        with tempfile.TemporaryDirectory() as t:
            os.chdir(t)
            try:
                with patch.dict(os.environ, {'CLOUDFLARE_AI_TOKEN': 'x'}), \
                        patch.object(illustration.urllib.request, 'urlopen', side_effect=fehler) as up:
                    self.assertIsNone(illustration._anfrage('flux-1-schnell', {'prompt': 'p'}))
                    self.assertTrue(illustration.KONTINGENT_LEER.exists())
                    self.assertIsNone(illustration._anfrage('flux-1-schnell', {'prompt': 'p'}))
                self.assertEqual(up.call_count, 1)
            finally:
                os.chdir(alt)

    def test_lauf_wiederholt_bei_leerem_kontingent_nicht(self):
        quelle = (Path(__file__).resolve().parents[1] / 'fabrik/lauf.py').read_text(encoding='utf-8')
        self.assertIn('if basis or kontingent_leer:', quelle)
        self.assertIn('Cloudflare-Bildkontingent aufgebraucht', quelle)


class Wortgrenze(unittest.TestCase):
    def test_short_standard_kokoro_170_216(self):
        # Vor dem 07.10.: 90 s * 2.9 = 261 Woerter erlaubt -> 117 s Ton, Tempo 1.25.
        import skript
        kanal = {'name': 'X', 'format': 'geschichte'}
        with patch('prompts.skript', side_effect=lambda k, t, f, b, w: w):
            self.assertEqual(skript.anweisung(kanal, 'WeWork', []), '170-216')

    def test_orus_kanaele_kuerzer(self):
        # Lauf 37749486997: Orus 207 Woerter = 109 s (~1.9 W/s). Vorher galt fuer alle 170-216.
        import json, skript
        wurzel = Path(__file__).resolve().parents[1]
        erwartet = {'business-origin-stories': '142-180', 'ai-tools-explained': '156-198'}
        for k, grenzen in erwartet.items():
            kanal = json.loads((wurzel / f'kanaele/{k}.json').read_text(encoding='utf-8'))
            with patch('prompts.skript', side_effect=lambda a, t, f, b, w: w):
                self.assertEqual(skript.anweisung(kanal, 'X', []), grenzen)
        self.assertEqual(skript.wortrate({'woerter_pro_sekunde': 'quatsch'}), 2.4)


if __name__ == '__main__':
    unittest.main()
