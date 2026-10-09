"""Vorschaubild fuer Langvideos und eigener Stimmen-Schluessel (Nutzerauftrag 09.10.2026).

Alter Stand, den diese Tests erkennen: kein Vorschaubild (Modul fehlte), der Telegram-Versand
konnte nur Videos anhaengen, und die Stimme lief immer ueber den Gratis-Schluessel (10/Tag).
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
from PIL import Image

SKRIPT = {'kanal': 'Business Origin Stories', 'videoformat': 'lang', 'thema': 'Volkswagen: Dieselgate',
          'titel': ['The *Dieselgate* Story', 'How VW Rigged Its Tests'],
          'teile': [{'text': 'In 2015 ...', 'szene': 'a test bench'}]}


class Vorschaubild(unittest.TestCase):
    """GEMELDET 09.10.: Logo/Firma groesser als die Figur, Figur nicht im Vordergrund, wenig Text."""
    def test_wenige_woerter_nie_abgeschnitten(self):
        import vorschaubild
        self.assertEqual(vorschaubild.text(SKRIPT), [('DIESELGATE', True)])
        aurelio = {'thema': 'Aurelio, a self-hosted wealth app', 'titel': ['Your Money, Your PC', '*Aurelio* Explained']}
        self.assertEqual(vorschaubild.name(aurelio), 'Aurelio')
        self.assertEqual(vorschaubild.text(aurelio), [], 'kein abgeschnittenes „YOUR MONEY, YOUR"')

    def test_bildauftrag_ohne_marke_und_ohne_figur(self):
        import vorschaubild
        with patch('skript.gemini', lambda *a, **k: ({'szene': 'a vast car factory with an assembly line'}, 'lite')):
            auftrag = vorschaubild.szene(SKRIPT)
        self.assertNotIn('Volkswagen', auftrag)
        self.assertNotIn('Dieselgate', auftrag)
        self.assertIn('no person in the foreground', auftrag)
        with patch('skript.gemini', lambda *a, **k: ({'szene': 'Volkswagen factory'}, 'lite')):
            self.assertNotIn('Volkswagen', vorschaubild.szene(dict(SKRIPT, thema='Volkswagen: Dieselgate')))

    def test_logo_ist_das_groesste_element(self):
        import vorschaubild
        with tempfile.TemporaryDirectory() as d:
            ordner = Path(d)
            (ordner / 'skript.json').write_text(json.dumps(dict(SKRIPT, thema='Volkswagen: Dieselgate')),
                                                encoding='utf-8')
            Image.new('RGB', (1360, 768), (180, 120, 60)).save(ordner / 'ill_00.jpg')
            logo = Image.new('RGBA', (400, 400), (0, 40, 120, 255))
            with patch('illustration.bild', return_value=None), patch('illustration.haende_zaehlen', return_value=''),                     patch('vorschaubild.logo_bild', return_value=logo):
                pfad = vorschaubild.erstellen(ordner / 'skript.json', ordner / 'thumbnail.jpg')
            with Image.open(pfad) as im:
                self.assertEqual(im.size, (1280, 720))
                blau = sum(1 for p in im.getdata() if p[2] > 90 and p[0] < 40 and p[1] < 70)
            self.assertLessEqual(pfad.stat().st_size, 2 * 1024 * 1024)
            self.assertGreater(blau / (1280 * 720), .15, 'Logo nimmt mindestens 15 % der Flaeche ein')

    def test_lauf_erstellt_es_nur_fuer_langvideo(self):
        quelle = (Path(__file__).resolve().parents[1] / 'fabrik/lauf.py').read_text(encoding='utf-8')
        self.assertIn("if skript.get('videoformat') == 'lang':", quelle)
        self.assertIn("'fabrik/vorschaubild.py'", quelle)


class Versand(unittest.TestCase):
    def test_vorschaubild_geht_als_bilddatei(self):
        import freigabe
        gesendet = []
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'thumbnail.jpg'
            Image.new('RGB', (1280, 720)).save(p)
            with patch('freigabe.telegram', lambda *a, **k: gesendet.append((a, k)) or {'ok': True}):
                self.assertTrue(freigabe.vorschaubild_senden('1', p))
            self.assertFalse(freigabe.vorschaubild_senden('1', Path(d) / 'fehlt.jpg'))
        (methode, felder, datei), k = gesendet[0]
        self.assertEqual((methode, k['feld'], k['typ'], datei[0]), ('sendDocument', 'document', 'image/jpeg', 'thumbnail.jpg'))


class Stimmenschluessel(unittest.TestCase):
    def test_eigener_schluessel_vor_gratis(self):
        import stimme_gemini
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'gratis', 'GEMINI_TTS_API_KEY': ' bezahlt '}):
            self.assertEqual(stimme_gemini.schluessel(), 'bezahlt')
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'gratis', 'GEMINI_TTS_API_KEY': ''}):
            self.assertEqual(stimme_gemini.schluessel(), 'gratis')



class Haende(unittest.TestCase):
    """GEMELDET 09.10.: „Der Typ auf dem Bild hat 3 Haende mit Anzug" - Bildpruefung hatte bestanden."""
    def _gemini(self, personen):
        return lambda *a, **k: ({'personen': personen}, 'gemini-3.5-flash')

    def test_drei_haende_werden_abgelehnt(self):
        import illustration
        drei = [{'wer': 'Mann im Anzug', 'haende': ['Taschenuhr an der Brust', 'Faust links', 'Faust rechts']}]
        with patch('skript.gemini', self._gemini(drei)):
            self.assertIn('3 Haende', illustration.haende_zaehlen(b'x'))

    def test_zwei_haende_und_ausfall_sperren_nicht(self):
        import illustration
        zwei = [{'wer': 'Mann', 'haende': ['links', 'rechts']}, {'wer': 'Frau', 'haende': ['Tasse']}]
        with patch('skript.gemini', self._gemini(zwei)):
            self.assertEqual(illustration.haende_zaehlen(b'x'), '')
        with patch('skript.gemini', side_effect=RuntimeError('weg')):
            self.assertEqual(illustration.haende_zaehlen(b'x'), '')

    def test_figurbild_durchlaeuft_die_zaehlung(self):
        import illustration
        antworten = [({'ok': True, 'grund': ''}, 'lite'),
                     ({'personen': [{'wer': 'Mann', 'haende': ['a', 'b', 'c']}]}, 'gemini-3.5-flash')]
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'GEMINI_API_KEY': 'k'}),                 patch('skript.gemini', lambda *a, **k: antworten.pop(0)):
            ref = Path(d) / 'figur.jpg'
            Image.new('RGB', (10, 10)).save(ref)
            ergebnis = illustration.pruefen(b'bild', 'szene', ref)
        self.assertFalse(ergebnis['ok'])
        self.assertIn('3 Haende', ergebnis['grund'])


if __name__ == '__main__':
    unittest.main()
