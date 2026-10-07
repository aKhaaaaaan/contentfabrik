"""Regressionen fuer verlorene Nutzerideen und verschwendete KI-Zeit."""
import json, os, unittest
from pathlib import Path
from unittest.mock import patch
from test_betrieb import TempTest
import skript, themen


class ThemenTest(TempTest):
    def test_workflow_bestaetigt_erst_nach_git_push(self):
        workflow = Path(__file__).resolve().parents[1] / '.github/workflows/themen.yml'
        text = workflow.read_text(encoding='utf-8')
        speichern = text.index('- name: Warteschlange sichern')
        bestaetigen = text.index('- name: Gesicherte Nachrichten bestaetigen')
        self.assertIn('git push -q && exit 0', text[speichern:bestaetigen])
        self.assertNotIn('continue-on-error', text[speichern:bestaetigen])
        self.assertIn("steps.sichern.outcome == 'success'", text[bestaetigen:])

    def abholen(self, text, update_id=20):
        update = {'update_id': update_id, 'message': {'chat': {'id': 456}, 'text': text}}
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': '456'}), \
                patch('themen._tg', return_value={'ok': True, 'result': [update]}) as tg, \
                patch('skript.gemini') as ki:
            themen.abholen()
        return tg, ki

    def test_zehn_ideen_eine_nachricht_ohne_ki_ohne_vorzeitige_bestaetigung(self):
        tg, ki = self.abholen('Business:\n' + '\n'.join(f'{i}. Marke {i}' for i in range(1, 11)))
        self.assertEqual([x['thema'] for x in themen.laden()], [f'Marke {i}' for i in range(1, 11)])
        self.assertEqual(len({x['id'] for x in themen.laden()}), 10)
        ki.assert_not_called()
        tg.assert_called_once_with('getUpdates', offset=0, limit=100)
        self.assertEqual(themen.telegram_laden()['offset'], 21)

    def test_wiederholte_updates_duplizieren_keine_themen(self):
        self.abholen('Business: LEGO')
        self.abholen('Business: LEGO')
        self.assertEqual(len(themen.laden()), 1)
        self.assertEqual(len(themen.telegram_laden()['bestaetigungen']), 1)

    def test_kanal_vorrang_vor_feedback_und_nummerierung(self):
        self.abholen('KI:\n- Video mit mehr Bildern\n2) Ein Bildworkflow')
        self.assertEqual([x['kanal'] for x in themen.laden()], ['ai-tools-explained'] * 2)
        self.assertEqual([x['thema'] for x in themen.laden()], ['Video mit mehr Bildern', 'Ein Bildworkflow'])

    def test_ungueltige_liste_wird_nicht_abgeschnitten_oder_teilweise_uebernommen(self):
        for text in ['Business:', 'Business: ' + 'a' * 201,
                     'Business:\n' + '\n'.join(str(i) for i in range(26))]:
            with self.subTest(text=text[:40]):
                self.assertRaises(ValueError, themen.themenliste, text)
        self.abholen('Business: ' + 'a' * 201)
        self.assertEqual(themen.laden(), [])
        self.assertIn('200 Zeichen', themen.telegram_laden()['bestaetigungen'][0]['text'])

    def test_lesen_entfernt_nichts_erledigen_nur_passenden_eintrag(self):
        self.abholen('Business:\nLEGO\nNike\nLEGO')
        self.assertEqual(themen.nehmen('business-origin-stories'), 'LEGO')
        self.assertEqual(themen.nehmen('business-origin-stories'), 'LEGO')
        self.assertFalse(themen.erledigen('ai-tools-explained', 'LEGO'))
        self.assertEqual(len(themen.laden()), 3)
        self.assertTrue(themen.erledigen('business-origin-stories', 'LEGO'))
        self.assertEqual([x['thema'] for x in themen.laden()], ['Nike', 'LEGO'])

    def test_speicherfehler_bestaetigt_nichts_bei_telegram(self):
        with patch('themen.speichern', side_effect=OSError('Dateisystem')):
            self.assertRaises(OSError, self.abholen, 'Business: LEGO')
        self.assertFalse(themen.TELEGRAM.exists())

    def test_bestaetigung_nach_sicherung_und_retry_bei_telegram_ausfall(self):
        self.abholen('Business: LEGO')
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': '456'}), \
                patch('themen._tg', return_value={'ok': False}) as tg:
            self.assertRaises(RuntimeError, themen.bestaetigen)
        self.assertEqual(tg.call_count, 1)
        self.assertEqual(len(themen.telegram_laden()['bestaetigungen']), 1)
        self.assertEqual(len(themen.laden()), 1)
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': '456'}), \
                patch('themen._tg', return_value={'ok': True}) as tg:
            themen.bestaetigen()
        self.assertEqual(tg.call_args_list[-1].args, ('getUpdates',))
        self.assertEqual(tg.call_args_list[-1].kwargs, {'offset': 21, 'limit': 1})
        self.assertEqual(themen.telegram_laden()['bestaetigungen'], [])


class SkriptBudgetTest(TempTest):
    def entwurf(self):
        return {'thema': 'Firma', 'titel_zeile1': 'A story', 'titel_zeile2': 'A decision',
                'schluesselwoerter': ['story'], 'beschreibung': 'A story.', 'hashtags': [],
                'teile': [{'platz': i + 1, 'text': ' '.join(['fact'] * 30), 'suche': 'workshop'}
                          for i in range(6)]}

    def ausfuehren(self, note=10, fehler=False):
        Path('kanal.json').write_text(json.dumps({'name': 'Test', 'format': 'geschichte',
                                  'stimmen': ['bm_george'], 'laenge_s': [62, 90]}), encoding='utf-8')
        story = {'note': note, 'kategorien': dict.fromkeys(skript.STORY_KATEGORIEN, note),
                 'schwaechen': ['More concrete tension'], 'besserer_hook': 'A decision'}
        antworten = [(self.entwurf(), 'test'), ({'ok': True, 'probleme': []}, 'test'), (story, 'test')]
        if fehler:
            antworten.append(RuntimeError('Zeitbudget'))
        with patch('skript.hinweise', return_value=('', [{'name': 'Firma', 'quelle': 'Test',
                                'text': 'fact', 'url': 'https://test'}])), \
                patch('skript.gemini', side_effect=antworten) as ki, \
                patch('erfolg.waehlen', return_value='bm_george'), patch('erfolg.vorbilder', return_value=[]), \
                patch('zweit.pruefen', return_value=None):
            skript.main('kanal.json', 'skript.json', 'Firma')
        return ki

    def test_story_mit_aufsteigenden_phasen_braucht_keine_countdown_reparatur(self):
        ki = self.ausfuehren()
        self.assertEqual(ki.call_count, 3)
        gespeichert = json.loads(Path('skript.json').read_text())
        self.assertFalse(any('platz' in t for t in gespeichert['teile']))
        self.assertNotIn('countdown', ki.call_args_list[0].args[0])

    def test_bestandenes_skript_bleibt_bei_optionalem_ki_ausfall(self):
        self.ausfuehren(note=8, fehler=True)
        gespeichert = json.loads(Path('skript.json').read_text())
        self.assertEqual(skript.skript_gruende(gespeichert), [])
        self.assertEqual(gespeichert['story']['note'], 8)

    def test_schwaches_skript_besteht_auch_bei_optionalem_ki_ausfall_nicht(self):
        with self.assertRaises(SystemExit) as e:
            self.ausfuehren(note=6, fehler=True)
        self.assertEqual(e.exception.code, 3)
        self.assertTrue(skript.skript_gruende(json.loads(Path('skript.json').read_text())))

    def test_konkrete_marke_braucht_keine_ki_themenauswahl(self):
        q = {'name': 'KFC', 'text': 'source'}
        with patch('trends.wikipedia', return_value=q) as wiki, patch('skript.gemini') as ki:
            wahl, quelle = skript.wiki_waehlen('KFC', 'Auftrag', {}, 7000)
        ki.assert_not_called()
        wiki.assert_called_once_with('KFC', grenze=7000)
        self.assertEqual(wahl['thema'], 'KFC')
        self.assertEqual(quelle, q)

    def test_komplexes_nutzerthema_wird_zugeordnet_aber_nicht_ersetzt(self):
        with patch('trends.wikipedia', return_value={'name': 'Nike'}) as wiki, \
                patch('skript.gemini', return_value=({'thema': 'Nike', 'wikipedia': 'Nike'}, 'test')) as ki:
            skript.wiki_waehlen('Wie Nike mit Laufschuhen angefangen hat', 'Auftrag', {}, 7000)
        self.assertIn('explicit user topic is binding', ki.call_args.args[0])
        self.assertEqual(ki.call_args.kwargs['modelle'], skript.SEHEN)
        wiki.assert_called_once_with('Nike', grenze=7000)


if __name__ == '__main__':
    unittest.main()
