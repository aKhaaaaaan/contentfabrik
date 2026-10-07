"""Quota-Reset, begrenzte Wiederholungen und Cache ohne echte API pruefen."""
import datetime
import io
import json
import os
import time
import urllib.error
from pathlib import Path
from unittest.mock import patch
from test_betrieb import TempTest
import ki_speicher as speicher
import skript


def antwort(daten=None, finish='STOP'):
    return io.BytesIO(json.dumps({'candidates': [{'finishReason': finish, 'content': {
        'parts': [{'text': json.dumps(daten or {'ok': True, 'probleme': []})}]}}]}).encode())


def fehler(code, text='', headers=None):
    return urllib.error.HTTPError('https://example.test?key=secret', code, 'Fehler',
                                  headers or {}, io.BytesIO(text.encode()))


class KiSpeicherTest(TempTest):
    def test_netzwerk_timeout_wechselt_modell_statt_doppeltem_timeout(self):
        with patch('skript.urllib.request.urlopen', side_effect=[TimeoutError(), antwort()]) as netz, \
                patch('skript.time.sleep') as warten:
            skript.gemini('Auftrag', skript.PRUEF_SCHEMA, modelle=['haengt', 'antwortet'])
        self.assertEqual(netz.call_count, 2)
        self.assertIn('haengt', netz.call_args_list[0].args[0].full_url)
        self.assertIn('antwortet', netz.call_args_list[1].args[0].full_url)
        self.assertLessEqual(netz.call_args.kwargs['timeout'], 45)
        warten.assert_not_called()

    def test_abgelaufene_schritt_deadline_verbraucht_keine_anfrage(self):
        with patch.dict(os.environ, {'CF_SCHRITT_ENDE': str(time.monotonic() - 1)}), \
                patch('skript.urllib.request.urlopen') as netz:
            self.assertRaisesRegex(RuntimeError, 'Zeitbudget', self.anfrage)
        netz.assert_not_called()

    def setUp(self):
        super().setUp()
        p = patch.dict(os.environ, {'GEMINI_API_KEY': 'secret'})
        p.start()
        self.addCleanup(p.stop)

    def anfrage(self, **kw):
        return skript.gemini('Skript A mit Quelle A', skript.PRUEF_SCHEMA, modelle=['test'], **kw)

    def test_tageslimit_stoppt_erneute_anfragen_auch_nach_prozessneustart(self):
        with patch('skript.urllib.request.urlopen', side_effect=fehler(429, 'GenerateRequestsPerDay')), \
                patch('skript.time.sleep') as warten:
            with self.assertRaisesRegex(RuntimeError, 'Tageskontingent'):
                self.anfrage()
        with patch('skript.urllib.request.urlopen') as netz, self.assertRaisesRegex(RuntimeError, 'Tageskontingent'):
            self.anfrage()
        netz.assert_not_called()
        warten.assert_not_called()
        self.assertNotIn('secret', speicher.KONTINGENT.read_text())

    def test_abgelaufene_sperre_und_anderer_zugang_werden_nicht_blockiert(self):
        with patch('ki_speicher.time.time', return_value=1000):
            speicher.sperren('secret', 'test', 'ueberlastet', 300)
        self.assertIsNone(speicher.sperre('anderer-zugang', 'test', 1100))
        self.assertIsNone(speicher.sperre('secret', 'test', 1300))
        self.assertEqual(speicher.sperre('secret', 'test', 1100), 'ueberlastet')

    def test_reset_beruecksichtigt_pazifik_sommer_und_winterzeit(self):
        for tag, stunde in [('2026-10-06', 7), ('2026-12-06', 8)]:
            jetzt = datetime.datetime.fromisoformat(tag + 'T20:00:00+00:00').timestamp()
            reset = datetime.datetime.fromtimestamp(speicher.tagesreset(jetzt), datetime.timezone.utc)
            self.assertEqual(reset.hour, stunde)
            self.assertEqual(reset.day, 7)
        # Tage der Zeitumstellung: eine valide Tages-Sperre kann 25 Stunden dauern.
        for iso, stunden in [('2026-03-08T08:00:00+00:00', 23), ('2026-11-01T07:00:00+00:00', 25)]:
            jetzt = datetime.datetime.fromisoformat(iso).timestamp()
            self.assertEqual(speicher.tagesreset(jetzt) - jetzt, stunden * 3600)
            with patch('ki_speicher.time.time', return_value=jetzt):
                speicher.sperren('secret', 'test', 'Tageskontingent erschoepft')
            self.assertIsNotNone(speicher.sperre('secret', 'test', jetzt))

    def test_ueberlastung_kuehlt_statt_dauerhaft_zu_sperren(self):
        with patch('skript.urllib.request.urlopen', side_effect=fehler(503)), patch('skript.time.sleep') as warten:
            with self.assertRaises(RuntimeError):
                self.anfrage()
        self.assertEqual(speicher.sperre('secret', 'test'), 'voruebergehend ueberlastet')
        warten.assert_not_called()

    def test_minutenlimit_einmal_warten_keine_tages_sperre(self):
        with patch('skript.urllib.request.urlopen', side_effect=[fehler(429, 'PerMinute', {'Retry-After': '12'}),
                                                                 antwort()]) as netz, \
                patch('skript.time.sleep') as warten:
            self.assertTrue(self.anfrage()[0]['ok'])
        self.assertEqual(netz.call_count, 2)
        warten.assert_called_once_with(12)
        self.assertIsNone(speicher.sperre('secret', 'test'))

    def test_lange_retry_after_blockiert_keine_minuten_im_prozess(self):
        with patch('skript.urllib.request.urlopen', side_effect=fehler(429, 'PerMinute', {'Retry-After': '120'})), \
                patch('skript.time.sleep') as warten, self.assertRaises(RuntimeError):
            self.anfrage()
        warten.assert_not_called()
        self.assertIsNotNone(speicher.sperre('secret', 'test'))

    def test_permanente_requestfehler_werden_nicht_wiederholt_oder_geleakt(self):
        for code in (400, 401, 403):
            with self.subTest(code=code), patch('skript.urllib.request.urlopen', side_effect=fehler(code, 'secret')) as netz, \
                    patch('skript.time.sleep') as warten, self.assertRaisesRegex(RuntimeError, f'HTTP {code}') as e:
                self.anfrage()
            self.assertNotIn('secret', str(e.exception))
            self.assertEqual(netz.call_count, 1)
            warten.assert_not_called()

    def test_identische_pruefung_wird_wiederverwendet_auch_bei_quota_sperre(self):
        with patch('skript.urllib.request.urlopen', return_value=antwort()) as netz:
            self.anfrage(cache='fakten')
        self.assertEqual(netz.call_count, 1)
        speicher.sperren('secret', 'test', 'Tageskontingent erschoepft')
        with patch('skript.urllib.request.urlopen') as netz:
            self.assertTrue(self.anfrage(cache='fakten')[0]['ok'])
        netz.assert_not_called()

    def test_neuer_prompt_oder_schema_oder_temperatur_braucht_neue_pruefung(self):
        with patch('skript.urllib.request.urlopen', side_effect=lambda *a, **k: antwort()) as netz:
            self.anfrage(cache='fakten')
            skript.gemini('Skript A mit Quelle B', skript.PRUEF_SCHEMA, modelle=['test'], cache='fakten')
            self.anfrage(cache='fakten', temperatur=.2)
            schema = dict(skript.PRUEF_SCHEMA, description='Neue Pruefanforderung')
            skript.gemini('Skript A mit Quelle A', schema, modelle=['test'], cache='fakten')
        self.assertEqual(netz.call_count, 4)

    def test_abgelaufener_oder_defekter_cache_besteht_nicht(self):
        key = speicher.cache_key('Auftrag', skript.PRUEF_SCHEMA, ['test'], None, 'fakten')
        speicher.cache_schreiben(key, {'ok': True, 'probleme': []}, 'test', skript.PRUEF_SCHEMA)
        with patch('ki_speicher.time.time', return_value=time.time() + speicher.TTL + 1):
            self.assertIsNone(speicher.cache_lesen(key, skript.PRUEF_SCHEMA, ['test']))
        p = speicher.CACHE / (key + '.json')
        d = json.loads(p.read_text())
        d['ergebnis'] = {'ok': 'true'}
        p.write_text(json.dumps(d))
        self.assertIsNone(speicher.cache_lesen(key, skript.PRUEF_SCHEMA, ['test']))

    def test_kreative_entwuerfe_und_vergleich_bleiben_frische_anfragen(self):
        with patch('skript.urllib.request.urlopen', side_effect=lambda *a, **k: antwort()) as netz:
            self.anfrage()
            self.anfrage()
        self.assertEqual(netz.call_count, 2)
        self.assertFalse(speicher.CACHE.exists())

    def test_abgeschnittene_antwort_nicht_speichern(self):
        with patch('skript.urllib.request.urlopen', side_effect=lambda *a, **k: antwort(finish='MAX_TOKENS')), \
                patch('skript.time.sleep'), self.assertRaises(RuntimeError):
            self.anfrage(cache='fakten')
        self.assertFalse(speicher.CACHE.exists())

    def test_medien_nicht_als_textcache_missbrauchen(self):
        with patch('skript.urllib.request.urlopen') as netz, self.assertRaises(ValueError):
            self.anfrage(cache='fakten', dateien=[('video/mp4', 'uri')])
        netz.assert_not_called()

    def test_speicherfehler_verbraucht_keine_zweite_anfrage(self):
        with patch('skript.urllib.request.urlopen', return_value=antwort()) as netz, \
                patch('ki_speicher.cache_schreiben', side_effect=OSError('kein Speicher')):
            self.assertTrue(self.anfrage(cache='fakten')[0]['ok'])
        self.assertEqual(netz.call_count, 1)

    def test_defekte_quota_datei_erzeugt_keine_ewige_sperre(self):
        speicher.speichern(speicher.KONTINGENT, {'version': 1, 'modelle': []})
        self.assertIsNone(speicher.sperre('secret', 'test'))
