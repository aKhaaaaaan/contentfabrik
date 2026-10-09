"""Selbst lernen - auch aus Fehlschlaegen, Regelbuch je Kanal sauber (09.10.2026).

Alter Stand, den diese Tests erkennen:
- Nur ein fertig gebautes und bewertetes Video fuehrte zu neuen Regeln. Scheiterte ein Lauf an
  Faktenpruefung/Story/Skriptqualitaet (die meisten Fehlschlaege), lernte die Fabrik nichts.
- lernen.aktualisieren schrieb gemeinsame Redaktions-/Telegram-Regeln mit ins Kanal-Regelbuch:
  Business enthielt „For AI Tools Explained ...", die 12er-Grenze fuellte sich mit Doppelten.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import lauf
import lernen
import skript


class Regelbuch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = patch.object(lernen, 'ORDNER', Path(self.tmp.name))
        self.ordner.start()
        lernen.speichern('business-origin-stories', {'regeln': ['Eigene Regel']})

    def tearDown(self):
        self.ordner.stop(); self.tmp.cleanup()

    def test_gemeinsame_regeln_landen_nicht_im_kanalbuch(self):
        auftraege = []

        def ki(prompt, schema, **k):
            auftraege.append(prompt)
            return {'regeln': ['Eigene Regel', 'Gemeinsame Redaktionsregel', 'Neue Lehre']}, 'm'
        with patch.object(lernen, 'redaktionsregeln', return_value=['Gemeinsame Redaktionsregel']), \
                patch.object(skript, 'gemini', side_effect=ki):
            neu = lernen.aktualisieren('business-origin-stories', {'probleme': [
                {'art': 'story', 'text': 'Timeline instead of story'}], 'kategorien': {}})
        self.assertEqual(neu, ['Eigene Regel', 'Neue Lehre'])
        teil = auftraege[0].split('Current channel rules:')[1]
        self.assertNotIn('Gemeinsame Redaktionsregel', teil)
        self.assertIn('belongs ONLY to the channel "business-origin-stories"', auftraege[0])
        gespeichert = json.loads((Path(self.tmp.name) / 'business-origin-stories.json').read_text(encoding='utf-8'))
        self.assertNotIn('Gemeinsame Redaktionsregel', gespeichert['regeln'])


class AusFehlschlaegen(unittest.TestCase):
    RUNDEN = [{'skript_probleme': ['[second checker] Claim X not in source'],
               'story_schwaechen': ['28 sentences start with a date'],
               'sperrgruende': ['Skript-spannung 5/10 unter 7/10']},
              {'baufehler': 'ValueError: kein Bild', 'skript_probleme': ['[second checker] Claim X not in source']}]

    def test_gescheiterter_lauf_wird_zur_lehre(self):
        with tempfile.TemporaryDirectory() as t, patch('lauf.Path', side_effect=lambda *a: Path(t, *a)), \
                patch.object(lauf, 'schritt', return_value=0) as s:
            self.assertTrue(lauf.aus_fehlern_lernen('business-origin-stories', self.RUNDEN, 1e18))
            datei = Path(s.call_args.args[0][2])
            probleme = json.loads(datei.read_text(encoding='utf-8'))['probleme']
        self.assertEqual(s.call_args.args[0][:2], ['fabrik/lernen.py', 'business-origin-stories'])
        self.assertEqual({p['art'] for p in probleme}, {'fakten', 'story', 'skript'})
        self.assertEqual(len(probleme), 3)  # doppelte Befunde nur einmal
        self.assertFalse(any('kein Bild' in p['text'] for p in probleme))  # Technik ist keine Schreibregel

    def test_ohne_befund_kein_ki_aufruf(self):
        with patch.object(lauf, 'schritt') as s:
            self.assertFalse(lauf.aus_fehlern_lernen('x', [{'baufehler': 'OSError'}], 1e18))
        s.assert_not_called()

    def test_lauf_lernt_vor_der_fehlermeldung(self):
        quelle = (Path(lauf.__file__)).read_text(encoding='utf-8')
        self.assertIn("aus_fehlern_lernen(kanal, bericht['runden']", quelle)


if __name__ == '__main__':
    unittest.main()
