"""Nutzerthema mit festen, datierten Quellen (Faktencheck „kostenlose" KI-Tools, 09.10.2026).

Alter Stand, den diese Tests erkennen:
- AI Tools Explained (nur_quellen) holte zu JEDEM Thema GitHub-/HF-Projekte als einzige Quellen;
  ein Preis-Faktencheck haette nur unpassende Repos als Belege gehabt (Zahlenprobe sperrt).
- Der Skriptauftrag fuer 'erklaerung' verbot Aussagen zu Gratiszugang - genau das Thema.
- Ein Bildplan-'demo' ohne GitHub-/HF-Seite brach den ganzen Bau ab (ValueError).
"""
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import prompts
import skript
import trends

WURZEL = Path(__file__).resolve().parents[1]
QUELLE = {'quelle': 'Official pricing page, checked 2026-10-09', 'name': 'Looka',
          'url': 'https://looka.com/pricing/', 'text': 'Basic Logo Package: $35 one-time purchase.'}


class Themenquellen(unittest.TestCase):
    def kanal(self, **mehr):
        k = json.loads((WURZEL / 'kanaele/ai-tools-explained.json').read_text(encoding='utf-8'))
        k.update(mehr)
        return k

    def test_feste_quellen_ersetzen_die_repo_suche(self):
        with patch.object(trends, 'ki_quellen', side_effect=AssertionError('Repo-Suche')), \
                patch.object(trends, 'schwerpunkt', return_value=None), \
                patch('kommentare.wuensche', return_value=None):
            text, quellen = skript.hinweise(self.kanal(_themenquellen=[QUELLE]), 'Free AI tools checked')
        self.assertEqual([q['url'] for q in quellen], ['https://looka.com/pricing/'])
        self.assertIn('$35 one-time purchase', text)
        self.assertNotIn('FIXED RANKING', text)

    def test_warteschlange_reicht_die_quellen_an_den_kanal(self):
        quelle = (WURZEL / 'fabrik/skript.py').read_text(encoding='utf-8')
        self.assertIn("kanal['_themenquellen'] = vorgabe['quellen']", quelle)

    def test_auftrag_erlaubt_belegte_preise(self):
        mit = prompts.skript(self.kanal(_themenquellen=[QUELLE]), 'Free AI tools checked', '', '', '150-190')
        ohne = prompts.skript(self.kanal(), 'Free AI tools checked', '', '', '150-190')
        self.assertIn('exact documented limit or price', mit)
        self.assertNotIn('Do not invent free access', mit)
        self.assertIn('Do not invent free access', ohne)

    def test_demo_ohne_karte_wird_gemalte_szene(self):
        quelle = (WURZEL / 'fabrik/bauen.py').read_text(encoding='utf-8')
        self.assertNotIn("raise ValueError(f'Phase {shot[\"phase\"]}: kein echtes Tool-Beispiel", quelle)
        self.assertIn("weder Beispielbild noch Karte - gemalte Szene", quelle)

    def test_eingetragenes_thema_ist_vollstaendig_belegt(self):
        liste = json.loads((WURZEL / 'themen/warteschlange.json').read_text(encoding='utf-8'))
        eintrag = next((x for x in liste if x.get('id') == 'redaktion-2026-10-09-1'), None)
        if eintrag is None:  # nach erfolgreicher Zustellung regulaer aus der Warteschlange entfernt
            self.skipTest('Faktencheck-Thema bereits produziert und entfernt')
        self.assertEqual(eintrag['kanal'], 'ai-tools-explained')
        self.assertGreaterEqual(len(eintrag['quellen']), 5)
        for q in eintrag['quellen']:
            self.assertTrue(q['url'].startswith('https://'))
            self.assertIn('2026-10-09', q['quelle'])
            self.assertTrue(q['text'] and q['name'])


    def test_pruefdatum_im_quellenkopf_zaehlt_als_beleg(self):
        # Pilot 37962348927: "checked six official pricing pages on October 9, 2026" fiel durch die
        # Zahlenprobe, weil sie nur name+text las, nicht den Quellenkopf mit dem Pruefdatum.
        quelle = (WURZEL / 'fabrik/skript.py').read_text(encoding='utf-8')
        self.assertIn("f\"{q.get('quelle', '')} {q.get('name', '')} {q.get('text', '')}\" for q in quellen", quelle)
        liste = json.loads((WURZEL / 'themen/warteschlange.json').read_text(encoding='utf-8'))
        eintrag = next((x for x in liste if x.get('id') == 'redaktion-2026-10-09-1'), None)
        if eintrag is None:  # nach erfolgreicher Zustellung regulaer aus der Warteschlange entfernt
            self.skipTest('Faktencheck-Thema bereits produziert und entfernt')
        self.assertTrue(all('October 9, 2026' in q['text'] for q in eintrag['quellen']))


if __name__ == '__main__':
    unittest.main()
