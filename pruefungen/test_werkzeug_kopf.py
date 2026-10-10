"""AI Tools: Tool-Name als Ueberschrift, Logo am Abschnittsanfang; Short mit verschwommenem
Hintergrund aus demselben Bild (Nutzerwunsch 10.10.2026, Punkt 2 mehrfach gemeldet).

Alter Stand, den diese Tests erkennen: kein Werkzeug-Feld im Skript, keine Ueberschrift/kein Logo;
im Short fuellte die Illustration den Bildschirm ohne verschwommenen Rand aus demselben Bild.
"""
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import bauen
import prompts
import skript
import vorschaubild

WURZEL = Path(__file__).resolve().parents[1]


def magenta(img):
    return sum(1 for p in img.getdata() if p[0] > 230 and p[1] < 30 and p[2] > 230 and p[3] > 200)


class Kopf(unittest.TestCase):
    def setUp(self):
        bauen.format_setzen('short')

    def test_ueberschrift_und_logo(self):
        logo = Image.new('RGBA', (256, 256), (250, 0, 250, 255))  # Magenta: kommt sonst nirgends vor
        ohne = bauen.bild_fuer({'text': 'x'}, ['A', 'B'], 3, 10, durchsichtig=True)
        mit = bauen.bild_fuer({'text': 'x', 'werkzeug': 'Gamma'}, ['A', 'B'], 3, 10, durchsichtig=True, logo=logo)
        oben = (0, bauen.LAYOUT['titel_y'], bauen.B, bauen.LAYOUT['titel_y'] + 90)
        anders = sum(1 for a, b in zip(mit.crop(oben).getdata(), ohne.crop(oben).getdata()) if a != b)
        self.assertGreater(anders, 2000)  # Ueberschrift sichtbar
        self.assertGreater(magenta(mit), 10000)  # Logo eingesetzt

    def test_ohne_logo_nur_ueberschrift(self):
        mit = bauen.bild_fuer({'text': 'x', 'werkzeug': 'Gamma'}, ['A', 'B'], 4, 10, durchsichtig=True)
        self.assertEqual(magenta(mit), 0)


class Skript(unittest.TestCase):
    def test_schema_und_auftrag(self):
        felder = skript.SKRIPT_SCHEMA['properties']['teile']['items']['properties']
        self.assertIn('werkzeug', felder)
        ai = prompts.skript({'name': 'AI Tools Explained', 'format': 'erklaerung', 'nur_quellen': True}, 'X', '', '', '150-190')
        bus = prompts.skript({'name': 'Business Origin Stories', 'format': 'geschichte'}, 'X', '', '', '150-190')
        self.assertIn('Set werkzeug on EVERY part', ai)
        self.assertNotIn('Set werkzeug', bus)


class Logo(unittest.TestCase):
    def test_herstellerseite_bekommt_seitensymbol(self):
        puffer = io.BytesIO()
        Image.new('RGB', (256, 256), (255, 0, 0)).save(puffer, 'PNG')
        with patch.object(vorschaubild, 'logo_wikidata', return_value=None), \
                patch.object(vorschaubild, '_holen', return_value=puffer.getvalue()) as h:
            logo = vorschaubild.werkzeug_logo('Gamma', 'https://gamma.app/pricing')
        self.assertEqual(logo.size, (256, 256))
        self.assertIn('domain=gamma.app', h.call_args.args[0])

    def test_zu_kleines_logo_wird_verworfen(self):
        puffer = io.BytesIO()
        Image.new('RGB', (32, 32)).save(puffer, 'PNG')
        with patch.object(vorschaubild, 'logo_wikidata', return_value=None), \
                patch.object(vorschaubild, '_holen', return_value=puffer.getvalue()):
            self.assertIsNone(vorschaubild.werkzeug_logo('X', 'https://x.example/'))


class ShortHintergrund(unittest.TestCase):
    def test_short_illustration_mit_verschwommenem_eigenen_hintergrund(self):
        quelle = (WURZEL / 'fabrik/bauen.py').read_text(encoding='utf-8')
        i = quelle.index("            if ill:  # GEMELDET 10.10.2026: auch im Short")
        block = quelle[i:i + 400]
        self.assertIn("karten_ebene(ill, kasten='gross')", block)
        self.assertIn('karten_filter(ill, ebene, kpfad)', block)
        bauen.format_setzen('short')
        x1, y1, x2, y2 = bauen.LAYOUT['gross']
        self.assertGreaterEqual((x2 - x1) / bauen.B, 0.8)  # Motiv gross
        self.assertLess((x2 - x1) / bauen.B, 1.0)  # Rand aus verschwommenem Bild sichtbar


if __name__ == '__main__':
    unittest.main()
