"""Skript-Autor: Luecken aus dem Langvideo-Pilot 37945779063 (09.10.2026).

Alter Stand, den diese Tests erkennen:
- Ein falsches NEBENfeld (z. B. beat "re-hook", platz null) liess Claudes ganzes Skript durch
  die Schemapruefung fallen; Claude wurde fuer den Lauf gesperrt, das Protokoll zeigte nur "sonnet".
- Jede Gemini-Antwort hatte hoechstens 45 s; ein Langvideo-Skript (~1.200 Woerter JSON) lief
  bei 3.8-flash und 3.5-flash jedes Mal in TimeoutError.
"""
import copy
import unittest
from pathlib import Path
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import ki_speicher
import skript

WURZEL = Path(__file__).resolve().parents[1]
GUT = {'thema': 'Netflix', 'titel_zeile1': 'A', 'titel_zeile2': 'B', 'schluesselwoerter': ['x'],
       'beschreibung': 'd', 'hashtags': ['#a'],
       'teile': [{'suche': 's', 'text': 'In 2010, Netflix bought streaming rights.', 'beat': 'hook'},
                 {'suche': 's', 'text': 'Then the plan changed.', 'beat': 're-hook', 'platz': None,
                  'bildmodus': 'figur'}]}


class Bereinigen(unittest.TestCase):
    def test_falsche_nebenfelder_kosten_nicht_das_skript(self):
        self.assertFalse(ki_speicher.schema_ok(GUT, skript.SKRIPT_SCHEMA))  # alter Stand: verworfen
        sauber, entfernt = ki_speicher.bereinigen(copy.deepcopy(GUT), skript.SKRIPT_SCHEMA)
        self.assertTrue(ki_speicher.schema_ok(sauber, skript.SKRIPT_SCHEMA))
        self.assertEqual(sauber['teile'][1], {'suche': 's', 'text': 'Then the plan changed.'})
        self.assertEqual(sauber['teile'][0]['beat'], 'hook')  # gueltige Felder bleiben
        self.assertEqual(len(entfernt), 3)

    def test_pflichtfelder_werden_nie_still_entfernt(self):
        kaputt = copy.deepcopy(GUT)
        kaputt['teile'][0]['text'] = 42
        sauber, _ = ki_speicher.bereinigen(kaputt, skript.SKRIPT_SCHEMA)
        self.assertEqual(sauber['teile'][0]['text'], 42)
        self.assertFalse(ki_speicher.schema_ok(sauber, skript.SKRIPT_SCHEMA))

    def test_unbekannte_felder_bleiben(self):
        sauber, _ = ki_speicher.bereinigen(dict(GUT, videoformat='lang'), skript.SKRIPT_SCHEMA)
        self.assertEqual(sauber['videoformat'], 'lang')


class Einbau(unittest.TestCase):
    def setUp(self):
        self.quelle = (WURZEL / 'fabrik/skript.py').read_text(encoding='utf-8')

    def test_claude_antwort_wird_bereinigt_und_grund_genannt(self):
        self.assertIn('e, entfernt = ki_speicher.bereinigen(e, SKRIPT_SCHEMA)', self.quelle)
        self.assertIn('Antwort passt nicht zum Schema (fehlt/falsch:', self.quelle)

    def test_gemini_und_groq_antworten_werden_bereinigt(self):
        self.assertIn('ergebnis, _ = ki_speicher.bereinigen(json.loads(text), schema)', self.quelle)
        self.assertIn('antwort, _ = ki_speicher.bereinigen(antwort, schema)', self.quelle)

    def test_langvideo_bekommt_mehr_antwortzeit(self):
        self.assertIn('antwort_s=150 if lang else 45', self.quelle)
        self.assertNotIn('timeout=min(45, rest)', self.quelle)

    def test_antwortzeit_erreicht_die_anfrage(self):
        with patch.object(skript, '_gemini', return_value=({}, 'm')) as g:
            skript.gemini('p', {'type': 'OBJECT'}, antwort_s=150)
        self.assertEqual(g.call_args.kwargs['antwort_s'], 150)
        self.assertGreaterEqual(g.call_args.kwargs['anfrage_s'], 300)


if __name__ == '__main__':
    unittest.main()
