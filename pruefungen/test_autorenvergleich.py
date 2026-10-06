"""Vergleichbarkeit und Sperren ohne echte KI-Anfragen pruefen."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
from unittest.mock import patch

from test_betrieb import TempTest
import autorenvergleich as av


def entwurf():
    teile = [{'text': 'What makes this useful? ' + 'clear ' * 20,
              'szene': 'An original illustrated presenter explains a practical example.'}]
    teile += [{'text': 'A practical example shows the next step clearly. ' + 'useful ' * 15,
               'szene': 'A matching illustrative shot.'} for _ in range(7)]
    teile += [{'text': 'Be sure to like, share and save this video.', 'szene': 'A closing shot.'}]
    return {'thema': 'Example', 'titel_zeile1': 'Example', 'titel_zeile2': 'Explained',
            'beschreibung': 'A practical explanation.', 'teile': teile}


def urteil():
    return {'fakten': {'ok': True, 'probleme': []}, 'story': {'note': 8,
        'kategorien': dict.fromkeys(av.STORY_KATEGORIEN, 8),
        'schwaechen': [], 'besserer_hook': ''}}


class AutorenvergleichTest(TempTest):
    def setUp(self):
        super().setUp()
        self.fall = {'id': 'test', 'kanal': 'test', 'thema': 'Example',
            'quellen': [{'text': 'A practical documented example.', 'name': 'Source'}],
            'quellen_sha256': hashlib.sha256(b'A practical documented example.').hexdigest()}
        Path('faelle.json').write_text(json.dumps({'faelle': [self.fall]}), encoding='utf-8')
        env = patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': ''})
        env.start()
        self.addCleanup(env.stop)

    def antwort(self, provider, prompt, schema, ausgabe_tokens=3072):
        return (entwurf() if schema is av.AUTOR_SCHEMA else urteil()), provider + '-actual', {}

    def bericht(self):
        return json.loads(Path('ergebnis/bericht.json').read_text(encoding='utf-8'))

    def test_beide_autoren_gleiche_quellen_aufgabe_und_verdeckte_kritik(self):
        with patch.object(av, 'anfrage', side_effect=self.antwort) as api:
            av.main('faelle.json', 'ergebnis', 1)
        calls = api.call_args_list
        autor = [c for c in calls if c.args[2] is av.AUTOR_SCHEMA]
        kritik = [c for c in calls if c.args[2] is av.PRUEF_SCHEMA]
        self.assertEqual(len(autor), 2)
        self.assertEqual(autor[0].args[1], autor[1].args[1])
        self.assertEqual(len(kritik), 4)
        for c in kritik:
            self.assertNotIn('gemini-actual', c.args[1])
            self.assertNotIn('groq-actual', c.args[1])
            self.assertIn(self.fall['quellen'][0]['text'], c.args[1])
        kandidaten = self.bericht()['kandidaten']
        self.assertEqual(kandidaten[0]['prompt_sha256'], kandidaten[1]['prompt_sha256'])
        self.assertTrue(all(k['quellen_sha256'] == self.fall['quellen_sha256'] for k in kandidaten))
        self.assertTrue(all(k['status'] == 'ki_vorpruefung_bestanden' for k in kandidaten))
        for k in kandidaten:
            self.assertEqual(k['autor_modell'], k['autor'] + '-actual')
            blind = Path('ergebnis/blind/' + k['id'] + '.md').read_text(encoding='utf-8')
            self.assertNotIn(k['autor_modell'], blind)

    def test_keine_menschliche_bewertung_oder_automatische_umstellung(self):
        with patch.object(av, 'anfrage', side_effect=self.antwort):
            av.main('faelle.json', 'ergebnis', 1)
        b = self.bericht()
        self.assertIsNone(b['menschliche_bewertung'])
        self.assertFalse(b['standardautor_geaendert'])
        self.assertTrue(all(k['menschliche_bewertung'] is None for k in b['kandidaten']))
        self.assertFalse(list(Path('ergebnis').rglob('*.mp4')))

    def test_geaenderte_quelle_vor_api_abgelehnt(self):
        self.fall['quellen'][0]['text'] += ' Changed.'
        Path('faelle.json').write_text(json.dumps({'faelle': [self.fall]}), encoding='utf-8')
        with patch.object(av, 'anfrage') as api, self.assertRaises(ValueError):
            av.main('faelle.json', 'ergebnis', 1)
        api.assert_not_called()

    def test_fehlender_pruefer_sperrt_trotz_gutem_anderen_urteil(self):
        def antwort(provider, prompt, schema, ausgabe_tokens=3072):
            if provider == 'groq' and schema is av.PRUEF_SCHEMA:
                raise RuntimeError('Testausfall')
            return self.antwort(provider, prompt, schema, ausgabe_tokens)
        with patch.object(av, 'anfrage', side_effect=antwort):
            av.main('faelle.json', 'ergebnis', 1)
        self.assertTrue(all(k['status'] == 'gesperrt_oder_pruefung_fehlt'
                            for k in self.bericht()['kandidaten']))

    def test_autorausfall_verhindert_nicht_zweiten_kandidaten(self):
        def antwort(provider, prompt, schema, ausgabe_tokens=3072):
            if provider == 'groq' and schema is av.AUTOR_SCHEMA:
                raise RuntimeError('Testausfall')
            return self.antwort(provider, prompt, schema, ausgabe_tokens)
        with patch.object(av, 'anfrage', side_effect=antwort):
            av.main('faelle.json', 'ergebnis', 1)
        status = {k['autor']: k['status'] for k in self.bericht()['kandidaten']}
        self.assertEqual(status['groq'], 'autorausfall')
        self.assertEqual(status['gemini'], 'ki_vorpruefung_bestanden')

    def test_alle_autorausfaelle_sind_kein_ausgewerteter_vergleich(self):
        with patch.object(av, 'anfrage', side_effect=RuntimeError('Testausfall')):
            av.main('faelle.json', 'ergebnis', 1)
        self.assertEqual(self.bericht()['status'], 'keine_verwertbaren_entwuerfe')

    def test_diagnose_enthaelt_keine_zugangsschluessel(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'secret-test-value'}):
            text = av.fehlertext(RuntimeError('https://example.test/?key=secret-test-value&token=another'))
        self.assertNotIn('secret-test-value', text)
        self.assertNotIn('another', text)

    def test_groq_schema_ist_rekursiv_geschlossen_und_veraendert_original_nicht(self):
        vorher = copy.deepcopy(av.PRUEF_SCHEMA)
        s = av.groq_schema(av.PRUEF_SCHEMA)
        def pruefen(d):
            self.assertEqual(d['type'], d['type'].lower())
            if d['type'] == 'object':
                self.assertFalse(d['additionalProperties'])
                self.assertEqual(set(d['required']), set(d['properties']))
                for p in d['properties'].values():
                    pruefen(p)
            if d['type'] == 'array':
                pruefen(d['items'])
        pruefen(s)
        self.assertEqual(av.PRUEF_SCHEMA, vorher)

    def test_vollstaendiger_cta_genau_einmal_und_am_ende(self):
        self.assertFalse(av.struktur(entwurf())[0])
        for text in ('Remember to like and share.', 'Save an image; share your workflow; like the result.'):
            d = entwurf()
            d['teile'][-1]['text'] = text
            self.assertTrue(any('Aufruf' in e for e in av.struktur(d)[0]))
        d = entwurf()
        d['teile'][1]['text'] += ' Like, share and save this video.'
        self.assertTrue(any('Aufruf' in e for e in av.struktur(d)[0]))
        d = entwurf()
        d['teile'][1]['text'], d['teile'][-1]['text'] = d['teile'][-1]['text'], d['teile'][1]['text']
        self.assertTrue(any('Aufruf' in e for e in av.struktur(d)[0]))

    def test_faktenkonflikt_sperrt_auch_bei_note_zehn(self):
        for fakten in ({'ok': False, 'probleme': []}, {'ok': True, 'probleme': ['unsupported']}):
            u = urteil()
            u['story']['note'] = 10
            u['fakten'] = fakten
            self.assertIn('Faktenpruefung nicht bestanden', av.urteilsgruende(u))

    def test_boolean_als_note_oder_fehlende_kategorie_abgelehnt(self):
        u = urteil()
        u['story']['note'] = True
        with self.assertRaises(ValueError):
            av.urteilsgruende(u)
        u = urteil()
        del u['story']['kategorien']['aufloesung']
        with self.assertRaises(ValueError):
            av.urteilsgruende(u)

    def test_schwache_aufloesung_sperrt(self):
        u = urteil()
        u['story']['kategorien']['aufloesung'] = 6
        self.assertTrue(av.urteilsgruende(u))

    def test_groq_verwendet_dokumentierte_parameter_und_validiert_antwort(self):
        data = {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(entwurf())}}],
                'usage': {'total_tokens': 123}}
        with patch.dict(os.environ, {'GROQ_API_KEY': 'unit-test-key'}), \
             patch.object(av, 'GROQ_VERBRAUCH', []), \
             patch.object(av.urllib.request, 'urlopen', return_value=io.StringIO(json.dumps(data))) as api:
            d, m, u = av.groq('Test', av.AUTOR_SCHEMA)
        body = json.loads(api.call_args.args[0].data)
        self.assertFalse(body['include_reasoning'])
        self.assertNotIn('reasoning_format', body)
        self.assertEqual(body['max_completion_tokens'], 3072)
        self.assertEqual(body['response_format']['type'], 'json_schema')
        self.assertTrue(body['response_format']['json_schema']['strict'])
        self.assertEqual(m, av.GROQ_MODELL)
        self.assertEqual(u['total_tokens'], 123)
        self.assertEqual(d, entwurf())

    def test_groq_unvollstaendige_ausgabe_wird_nicht_als_skript_gewertet(self):
        data = {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]}
        with patch.dict(os.environ, {'GROQ_API_KEY': 'unit-test-key'}), \
             patch.object(av, 'GROQ_VERBRAUCH', []), \
             patch.object(av.urllib.request, 'urlopen', return_value=io.StringIO(json.dumps(data))), \
             self.assertRaises(ValueError):
            av.groq('Test', av.AUTOR_SCHEMA)

    def test_groq_zu_grosser_auftrag_verbraucht_keine_anfrage(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'unit-test-key'}), \
             patch.object(av.urllib.request, 'urlopen') as api, self.assertRaises(ValueError):
            av.groq('X' * 24000, av.AUTOR_SCHEMA)
        api.assert_not_called()
