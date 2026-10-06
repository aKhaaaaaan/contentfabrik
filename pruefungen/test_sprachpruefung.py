"""Endton-Sperren und Videobindung mit kuenstlichen Rohdaten pruefen."""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from test_betrieb import TempTest, SKRIPT, KRITIK, audio_fixture
import freigabe
import kritik
import sprachpruefung as sprache
from qualitaet import bewerten


def roh(text='Be sure to like share and save this video', start=66, dauer=70, p=.99):
    return {'dauer_s': dauer, 'sprache': 'en', 'woerter': [
        {'w': w, 's': start + i * .15, 'e': start + (i + 1) * .15, 'p': p}
        for i, w in enumerate(text.split())]}


class SprachpruefungTest(TempTest):
    def test_alle_drei_aktionen_im_short_schluss(self):
        r = sprache.cta_bewerten(roh(), 'short', 70)
        self.assertTrue(r['ok'])
        self.assertEqual(r['treffer'][0]['von_s'], 66.45)
        for text in ('Like and share this video', 'Like and save this video', 'Share and save this video',
                     'Subscribe for more', 'Do not like share and save this video'):
            self.assertFalse(sprache.cta_bewerten(roh(text), 'short', 70)['ok'], text)

    def test_anfangs_cta_allein_ersetzt_schluss_nicht(self):
        self.assertFalse(sprache.cta_bewerten(roh(start=5), 'short', 70)['ok'])

    def test_langvideo_braucht_zwei_cta_in_passenden_fenstern(self):
        a = roh(start=12, dauer=600)
        b = roh(start=570, dauer=600)
        self.assertFalse(sprache.cta_bewerten(a, 'lang', 600)['ok'])
        self.assertFalse(sprache.cta_bewerten(b, 'lang', 600)['ok'])
        a['woerter'] += b['woerter']
        self.assertTrue(sprache.cta_bewerten(a, 'lang', 600)['ok'])

    def test_gestreute_aktionen_sind_kein_gemeinsamer_aufruf(self):
        d = roh()
        for i, w in enumerate(d['woerter']):
            w['s'] = i * 7
            w['e'] = i * 7 + 1
        self.assertFalse(sprache.cta_bewerten(d, 'short', 70)['ok'])

    def test_unzuverlaessige_erkennung_und_gefakte_zeitstempel_sperren(self):
        for d in (roh(p=.1), {'dauer_s': 70, 'woerter': []}, roh(dauer=100)):
            self.assertFalse(sprache.cta_bewerten(d, 'short', 70)['ok'])
        for feld, wert in [('s', float('nan')), ('e', 999), ('p', True), ('p', 1.5)]:
            d = roh()
            d['woerter'][0][feld] = wert
            self.assertFalse(sprache.cta_bewerten(d, 'short', 70)['ok'])

    def test_rohcache_gehoert_zum_exakten_mp4_und_nicht_zum_skript(self):
        Path('video.mp4').write_bytes(b'ein mp4 fuer unit-test')
        with patch('sprachpruefung.importlib.metadata.version', return_value='test'), \
                patch('sprachpruefung.transkribieren', return_value=roh()) as asr:
            a = sprache.pruefen('video.mp4', SKRIPT, 70)
            b = sprache.pruefen('video.mp4', dict(SKRIPT, teile=[{'text': 'Never provide ASR prompts'}]), 70)
            self.assertTrue(a['ok'])
            self.assertTrue(b['wiederverwendet'])
            self.assertEqual(asr.call_count, 1)
            Path('video.mp4').write_bytes(b'geaenderter mp4-ton')
            c = sprache.pruefen('video.mp4', SKRIPT, 70)
            self.assertFalse(c['wiederverwendet'])
            self.assertEqual(asr.call_count, 2)

    def test_asr_ohne_skript_hotwords_oder_angeglichene_untertitel(self):
        class Info:
            duration, language = 70, 'en'
        with patch('sprachpruefung.modell') as model:
            model.return_value.transcribe.return_value = ([], Info())
            sprache.transkribieren('fertiger-mix.mp4')
        args, kw = model.return_value.transcribe.call_args
        self.assertEqual(args, ('fertiger-mix.mp4',))
        self.assertIsNone(kw['initial_prompt'])
        self.assertNotIn('hotwords', kw)
        self.assertTrue(kw['vad_filter'])
        self.assertFalse(kw['condition_on_previous_text'])

    def test_erkennungsfehler_ist_keine_freigabe(self):
        Path('video.mp4').write_bytes(b'mp4')
        with patch('sprachpruefung.importlib.metadata.version', return_value='test'), \
                patch('sprachpruefung.transkribieren', side_effect=RuntimeError('ASR fehlt')):
            a = sprache.pruefen('video.mp4', SKRIPT, 70)
        self.assertFalse(a['ok'])
        self.assertTrue(a['befunde'])

    def test_hohe_ki_note_ersetzt_rohe_endton_pruefung_nicht(self):
        for audio in (None, {'ok': True}, dict(KRITIK['audio_pruefung'], video_sha256='falsch'),
                      dict(KRITIK['audio_pruefung'], roh=roh('Subscribe for more'))):
            self.assertTrue(bewerten(SKRIPT, dict(KRITIK, audio_pruefung=audio))[1])

    def test_geaenderte_datei_wird_trotz_guter_alter_kritik_nicht_versendet(self):
        Path('skript.json').write_text(json.dumps(SKRIPT))
        Path('kritik.json').write_text(json.dumps(KRITIK))
        Path('video.mp4').write_bytes(b'geaendert')
        with patch('freigabe.telegram') as tg, self.assertRaisesRegex(ValueError, 'geaendert'):
            freigabe.senden('skript.json', 'video.mp4')
        tg.assert_not_called()

    def kritik_ausfuehren(self, audio):
        Path('skript.json').write_text(json.dumps(SKRIPT))
        Path('video.mp4').write_bytes(b'video')
        with patch('kritik.technik', return_value=copy.deepcopy(KRITIK['technik'])), \
                patch('bildplan.pruefen', return_value={'befunde': []}), \
                patch('sprachpruefung.pruefen', return_value=audio):
            return kritik.kritik('video.mp4', 'skript.json', 'kritik.json')

    def test_fehlender_gesprochener_cta_verbraucht_keine_gemini_anfrage(self):
        with patch('kritik.hochladen') as upload, patch('kritik.gemini') as api:
            k = self.kritik_ausfuehren({'ok': False, 'befunde': ['CTA nicht erkannt']})
        self.assertIsNone(k['note'])
        self.assertTrue(bewerten(SKRIPT, k)[1])
        api.assert_not_called()
        upload.assert_not_called()

    def test_leere_kontingente_verhindern_unnoetigen_video_upload(self):
        import os
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('ki_speicher.sperre', return_value='Tageskontingent erschoepft'), \
                patch('kritik.hochladen') as upload, patch('kritik.gemini') as api, \
                self.assertRaisesRegex(RuntimeError, 'kein unnoetiger Video-Upload'):
            self.kritik_ausfuehren(audio_fixture(hashlib.sha256(b'video').hexdigest()))
        upload.assert_not_called()
        api.assert_not_called()

    def test_video_cache_spart_upload_und_api_nur_fuer_identisches_video_und_prompt(self):
        import os
        sha = hashlib.sha256(b'video').hexdigest()
        audio = audio_fixture(sha)
        urteil = {k: copy.deepcopy(KRITIK[k]) for k in ('note', 'kategorien', 'probleme', 'fazit')}
        urteil['staerken'] = ['Gut']
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('kritik.hochladen', return_value={'uri': 'uri', 'name': 'files/test'}) as upload, \
                patch('kritik.urllib.request.urlopen'), \
                patch('kritik.gemini', return_value=(urteil, 'gemini-3.8-flash')) as api:
            a = self.kritik_ausfuehren(audio)
            b = self.kritik_ausfuehren(audio)
        self.assertFalse(a['ki_cache_wiederverwendet'])
        self.assertTrue(b['ki_cache_wiederverwendet'])
        self.assertEqual(api.call_count, 1)
        self.assertEqual(upload.call_count, 1)
        self.assertEqual(bewerten(SKRIPT, b)[1], [])
        with patch('kritik.prompts.video', return_value='Geaenderte Pruefkriterien'), \
                patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('kritik.hochladen', return_value={'uri': 'neu', 'name': 'files/neu'}) as upload, \
                patch('kritik.urllib.request.urlopen'), \
                patch('kritik.gemini', return_value=(urteil, 'gemini-3.8-flash')) as api:
            c = self.kritik_ausfuehren(audio)
        self.assertFalse(c['ki_cache_wiederverwendet'])
        self.assertEqual(api.call_count, 1)
