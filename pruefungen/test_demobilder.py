"""Echte Werkzeug-Bilder statt Symbolbilder (GEMELDET 09.10.2026, Aurelio-Short, Nutzernote 6/10:
„Die Videos nutzen Fotos, die nicht mit dem Text zusammenhaengen").

Alter Stand, den diese Tests erkennen: README-GIF lieferte hoechstens EIN Standbild, der Bildplaner
erfuhr nie, dass es echtes Material gibt (21 von 21 Einstellungen Symbol-Illustration), und eine
kurz ueberlastete Bildpruefung verwarf jedes Bild sofort.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
from PIL import Image
import bauen
import bildplan
import illustration

README = ('# Aurelio\n![CI](https://github.com/x/y/actions/workflows/ci.yml/badge.svg)\n'
          '![Aurelio: the net worth, what the funds really hold, and the chat](docs/demo.gif)\n'
          '<img src="docs/logo.svg">\n')


class _Antwort:
    def __init__(self, daten):
        self.daten = daten

    def read(self):
        return self.daten


class Demobilder(unittest.TestCase):
    def test_readme_medien_mit_beschreibung_ohne_abzeichen(self):
        with patch('urllib.request.urlopen', lambda *a, **k: _Antwort(README.encode())):
            medien = bauen.readme_medien('https://github.com/LosaLosSantos/aurelio-finance')
        self.assertEqual(len(medien), 1)
        self.assertTrue(medien[0][0].endswith('/HEAD/docs/demo.gif'))
        self.assertIn('net worth', medien[0][1])

    def test_animierte_vorfuehrung_gibt_mehrere_verschiedene_standbilder(self):
        with tempfile.TemporaryDirectory() as d:
            gif = Path(d) / 'demo'
            farben = [(200, 30, 30), (30, 200, 30), (30, 30, 200), (200, 200, 30), (30, 200, 200), (90, 90, 90)]
            bilder = [Image.new('RGB', (960, 540), f) for f in farben]
            bilder[0].save(gif, 'GIF', save_all=True, append_images=bilder[1:], duration=200)
            standbilder = bauen.gif_bilder(gif)
            self.assertEqual(len(standbilder), 4)
            mitten = {Image.open(f).convert('RGB').getpixel((480, 270)) for f in standbilder}
            self.assertEqual(len(mitten), 4, 'vier verschiedene Momente der Vorfuehrung')
            Image.new('RGB', (960, 540)).save(Path(d) / 'still.png')
            self.assertEqual(bauen.gif_bilder(Path(d) / 'still.png'), [])

    def test_bildplaner_bekommt_echtes_material(self):
        s = {'teile': [{'quelle_url': 'https://github.com/x/aurelio', 'text': 'a'},
                       {'quelle_url': 'https://github.com/x/aurelio', 'text': 'b'},
                       {'quelle_url': 'https://de.wikipedia.org/wiki/X', 'text': 'c'}]}
        with patch('bauen.readme_medien', return_value=[('https://r/x/aurelio/HEAD/docs/demo.gif', 'net worth')]) as rm:
            m = bildplan.demo_material(s)
        rm.assert_called_once_with('https://github.com/x/aurelio')
        self.assertEqual(m[0]['media'][0], {'file': 'demo.gif', 'alt': 'net worth', 'animated': True})
        quelle = Path(bildplan.__file__).read_text(encoding='utf-8')
        self.assertIn("'tool_demo_material': demo_material(s)", quelle)


class Bildpruefung(unittest.TestCase):
    def test_kurze_ueberlast_wird_einmal_neu_geprueft(self):
        antworten = [RuntimeError('Zeitlimit'), ({'ok': True, 'grund': 'passt'}, 'lite')]

        def gemini(*a, **k):
            x = antworten.pop(0)
            if isinstance(x, Exception):
                raise x
            return x
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'k'}), patch('skript.gemini', gemini), \
                patch.object(illustration, 'PRUEF_PAUSE_S', 0):
            self.assertTrue(illustration.pruefen(b'bild', 'szene')['ok'])

    def test_dauerhafter_ausfall_nimmt_weiter_kein_ungepruftes_bild(self):
        def gemini(*a, **k):
            raise RuntimeError('weg')
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'k'}), patch('skript.gemini', gemini), \
                patch.object(illustration, 'PRUEF_PAUSE_S', 0):
            self.assertFalse(illustration.pruefen(b'bild', 'szene')['ok'])


if __name__ == '__main__':
    unittest.main()
