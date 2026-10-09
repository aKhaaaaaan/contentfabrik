"""Langvideo: Geschichte statt Zeitleiste (09.10.2026).

Alter Stand, den diese Tests erkennen: Das Netflix-Langvideo (Story 6/10, Spannung 4,
Tempo 5) begann 28 Saetze mit einem Datum - nichts im Code bemerkte das, der Auftrag
verlangte es nicht anders. Daten: echtes Skript aus Pilot-Run 37945779063.
"""
import json
import unittest
from pathlib import Path

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import dramaturgie

WURZEL = Path(__file__).resolve().parents[1]
NETFLIX = json.loads((WURZEL / 'pruefungen/daten/zweit-netflix-langvideo.json').read_text(encoding='utf-8'))['skript']


class Chronik(unittest.TestCase):
    def test_echtes_netflix_skript_ist_eine_zeitleiste(self):
        self.assertGreater(dramaturgie.chronik_saetze([{'text': NETFLIX}]), dramaturgie.CHRONIK_MAX)

    def test_geschichte_mit_wenigen_daten_ist_ok(self):
        text = ('Reed Hastings owed a late fee. It annoyed him. In 1997, he and Marc Randolph tried '
                'mailing a CD to themselves. It arrived intact. That moment changed the plan.')
        self.assertEqual(dramaturgie.chronik_saetze([{'text': text}]), 1)

    def test_erkennt_typische_satzanfaenge(self):
        text = ('By early 2000, it grew. In September 1999, it changed. On April 14, 1998, it launched. '
                'Since 2007, it streamed. The year 2010 mattered.')
        self.assertEqual(dramaturgie.chronik_saetze([{'text': text}]), 4)

    def test_auftrag_und_schreiber_nutzen_die_regel(self):
        auftrag = dramaturgie.auftrag({'videoformat': 'lang'})
        self.assertIn('NOT A TIMELINE', auftrag)
        self.assertIn(f'At most {dramaturgie.CHRONIK_MAX} sentences', auftrag)
        self.assertNotIn('NOT A TIMELINE', dramaturgie.auftrag({'videoformat': 'short'}))
        quelle = (WURZEL / 'fabrik/skript.py').read_text(encoding='utf-8')
        self.assertIn('dramaturgie.chronik_saetze(e[', quelle)


    def test_schlusspruefung_verlangt_keine_chronologie(self):
        # Alter Prompt: "unranked chronological or causal structure" - lud zur Zeitleiste ein.
        import prompts
        kanal = {'name': 'Business Origin Stories', 'format': 'geschichte', 'videoformat': 'lang'}
        text = prompts.skript(kanal, 'Netflix', '', '', '1000-1200')
        self.assertNotIn('chronological or causal', text)
        self.assertIn('not a year-by-year chronology', text)


if __name__ == '__main__':
    unittest.main()
