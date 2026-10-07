"""Tagesplanung, gepruefte Teilproduktion und Text-Ausweichweg ohne echte API-Aufrufe."""
import copy, datetime, json, os, time
from pathlib import Path
from unittest.mock import patch
from test_betrieb import TempTest, SKRIPT
import autorenvergleich as av
import entwurf_cache as ec
import skript, themen


class TagesplanTest(TempTest):
    def test_listentitel_ist_keine_elfte_idee(self):
        kanal, ideen = themen.themenliste('Business:\nDie 10 besten Video-Ideen für den Start\n'
                                         + '\n'.join(f'{i}. Firma {i}' for i in range(1, 11)))
        self.assertEqual(len(ideen), 10)
        self.assertEqual(kanal, 'business-origin-stories')

    def test_recherche_blockiert_keine_bereite_idee_zukunft_wartet(self):
        morgen = (datetime.datetime.now(datetime.timezone.utc).date() + datetime.timedelta(days=2)).isoformat()
        themen.speichern([{'kanal': 'business-origin-stories', 'thema': 'Unbekannte Person', 'status': 'recherche'},
                         {'kanal': 'business-origin-stories', 'thema': 'Zukunft', 'geplant_ab': morgen},
                         {'kanal': 'business-origin-stories', 'thema': 'WeWork', 'status': 'bereit'}])
        self.assertEqual(themen.nehmen('business-origin-stories'), 'WeWork')
        self.assertEqual(len(themen.laden()), 3)

    def test_vorgegebener_artikel_braucht_keine_neue_zuordnung(self):
        themen.speichern([{'kanal': 'business-origin-stories', 'thema': 'Unsere Geschichte', 'wikipedia': 'WeWork'}])
        with patch('trends.wikipedia', return_value={'name': 'WeWork', 'text': 'facts'}) as quelle, \
                patch('skript.gemini') as ki:
            wahl, q = skript.wiki_waehlen('Unsere Geschichte', 'Auftrag', {}, 7000)
        ki.assert_not_called()
        quelle.assert_called_once_with('WeWork', grenze=7000)
        self.assertEqual(wahl['thema'], 'Unsere Geschichte')

    def test_quellensnapshot_nur_fuer_richtigen_artikel_und_24_stunden(self):
        vorgabe = {'id': 'telegram-1-0', 'wikipedia': 'WeWork'}
        Path('themen/quellen').mkdir(parents=True)
        p = Path('themen/quellen/telegram-1-0.json')
        q = {'quelle': 'Wikipedia', 'url': 'https://en.wikipedia.org/wiki/WeWork',
             'angefragter_artikel': 'WeWork', 'abgerufen_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        p.write_text(json.dumps(q))
        self.assertTrue(themen.quelle(vorgabe))
        self.assertIsNone(themen.quelle(dict(vorgabe, wikipedia='Tesla')))
        q['abgerufen_utc'] = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).isoformat()
        p.write_text(json.dumps(q))
        self.assertIsNone(themen.quelle(vorgabe))


class EntwurfCacheTest(TempTest):
    def setUp(self):
        super().setUp()
        Path('profil.json').write_text('{"name":"Test"}')
        Path('bau').mkdir()
        Path('bau/skript.json').write_text(json.dumps(SKRIPT))
        Path('bau/stimme.wav').write_bytes(b'vorhandene-stimme')

    def sichern(self):
        return ec.sichern('test', 'profil.json', 'Nutzerthema', 'bau')

    def test_neuer_lauf_erhaelt_skript_und_teilbau(self):
        self.assertTrue(self.sichern())
        ordner = ec.laden('test', 'profil.json', 'Nutzerthema')
        self.assertEqual(json.loads((ordner / 'skript.json').read_text()), SKRIPT)
        self.assertEqual((ordner / 'stimme.wav').read_bytes(), b'vorhandene-stimme')

    def test_alter_andere_idee_anderes_profil_oder_tampering_werden_abgelehnt(self):
        self.sichern()
        self.assertIsNone(ec.laden('test', 'profil.json', 'Anderes Thema'))
        with patch('entwurf_cache.time.time', return_value=time.time() + ec.TTL + 1):
            self.assertIsNone(ec.laden('test', 'profil.json', 'Nutzerthema'))
        meta, _ = ec.pfade('test')
        d = json.loads(meta.read_text())
        d['skript']['teile'][0]['text'] = 'Ungepruefte Aenderung'
        meta.write_text(json.dumps(d))
        self.assertIsNone(ec.laden('test', 'profil.json', 'Nutzerthema'))
        self.sichern()
        Path('profil.json').write_text('{"name":"Anderes Profil"}')
        self.assertIsNone(ec.laden('test', 'profil.json', 'Nutzerthema'))

    def test_bauarbeit_verlaengert_pruefung_nicht(self):
        with patch('entwurf_cache.time.time', return_value=1000):
            self.sichern()
        s = copy.deepcopy(SKRIPT)
        s['musik_pegel'] = 0.03
        Path('bau/skript.json').write_text(json.dumps(s))
        with patch('entwurf_cache.time.time', return_value=2000):
            self.sichern()
        meta, _ = ec.pfade('test')
        self.assertEqual(json.loads(meta.read_text())['erstellt'], 1000)

    def test_schwaches_skript_wird_nicht_gesichert(self):
        s = copy.deepcopy(SKRIPT)
        s['story']['note'] = 6
        Path('bau/skript.json').write_text(json.dumps(s))
        self.assertFalse(self.sichern())
        self.assertIsNone(ec.laden('test', 'profil.json', 'Nutzerthema'))


class TextFallbackTest(TempTest):
    def test_text_bei_ausfall_groq_schema_geprueft_kein_kuenstliches_ok(self):
        with patch.dict(os.environ, {'CF_TEXT_FALLBACK': 'groq', 'GROQ_API_KEY': 'test'}), \
                patch('skript._gemini', side_effect=RuntimeError('503')) as gem, \
                patch('autorenvergleich.groq', return_value=({'ok': False, 'probleme': ['Falsche Zahl']},
                                                            av.GROQ_MODELL, {})) as groq:
            d, m = skript.gemini('Quelle und Text', skript.PRUEF_SCHEMA)
        self.assertFalse(d['ok'])
        self.assertTrue(m.startswith('groq:'))
        self.assertEqual(gem.call_args.kwargs['anfrage_s'], 12)
        self.assertEqual(groq.call_args.kwargs['ausgabe_tokens'], 768)

    def test_medien_oder_permanenter_requestfehler_weichen_nicht_auf_text_aus(self):
        for kw, fehler in [({'bilder': [b'JPEG']}, '503'), ({}, 'Gemini-Anfrage abgelehnt (HTTP 400)')]:
            with self.subTest(kw=kw), patch.dict(os.environ, {'CF_TEXT_FALLBACK': 'groq'}), \
                    patch('skript._gemini', side_effect=RuntimeError(fehler)), \
                    patch('autorenvergleich.groq') as groq:
                self.assertRaises(RuntimeError, skript.gemini, 'Auftrag', skript.PRUEF_SCHEMA, **kw)
            groq.assert_not_called()

    def test_falsches_schema_gibt_keine_faktenfreigabe(self):
        with patch.dict(os.environ, {'CF_TEXT_FALLBACK': 'groq', 'GROQ_API_KEY': 'test'}), \
                patch('skript._gemini', side_effect=RuntimeError('503')), \
                patch('autorenvergleich.groq', return_value=({'ok': 'true'}, av.GROQ_MODELL, {})):
            self.assertRaisesRegex(RuntimeError, 'Schema', skript.gemini, 'Auftrag', skript.PRUEF_SCHEMA)

    def test_keine_neue_groq_anfrage_nach_arbeiter_deadline(self):
        with patch.dict(os.environ, {'CF_TEXT_FALLBACK': 'groq', 'GROQ_API_KEY': 'test',
                                    'CF_SCHRITT_ENDE': str(time.monotonic() - 1)}), \
                patch('skript._gemini', side_effect=RuntimeError('Zeitbudget')), \
                patch('autorenvergleich.groq') as groq:
            self.assertRaises(RuntimeError, skript.gemini, 'Auftrag', skript.PRUEF_SCHEMA)
        groq.assert_not_called()

    def test_ai_erklaerung_nimmt_eine_belegte_quelle_ohne_ranking(self):
        q = {'name': 'Tool', 'quelle': 'Test', 'url': 'https://test', 'text': 'Primary facts', 'belegt': True}
        with patch('trends.ki_quellen', return_value=[q, dict(q, name='Other')]) as netz:
            text, quellen = skript.hinweise({'nur_quellen': True, 'format': 'erklaerung'}, 'Tool')
        netz.assert_called_once_with(maximal=1)
        self.assertEqual(len(quellen), 1)
        self.assertNotIn('FIXED RANKING', text)
