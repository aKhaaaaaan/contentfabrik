"""API-Vertraege, Bildfreigabe und echte Audiosignale ohne externe Anfragen."""
import base64
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import wave
import urllib.error
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
from test_betrieb import TempTest
import bauen
import illustration
import prompts
import skript
import ton
import zweit


def antwort(d):
    return io.StringIO(json.dumps(d))


class MusikbettTest(TempTest):
    def test_alpha_bild_zeigt_raster_statt_unsichtbarer_magenta_pixel(self):
        im = Image.new('RGBA', (100, 100), (255, 0, 255, 0))
        im.putpixel((50, 50), (12, 20, 30, 255))
        rgb = bauen.bild_rgb(im)
        self.assertEqual(rgb.getpixel((50, 50)), (12, 20, 30))
        self.assertIn(rgb.getpixel((0, 0)), ((240, 240, 240), (210, 210, 210)))

    def test_rueckfall_hat_nutzbare_dynamik_und_keine_klickenden_enden(self):
        pfad = ton.musikbett('score.wav', rate=8000)
        with wave.open(str(pfad)) as w:
            self.assertGreater(w.getnframes() / w.getframerate(), 15)
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16) / 32767
        self.assertGreater(np.sqrt(np.mean(x * x)), .02)
        self.assertLess(np.abs(x).max(), .81)
        self.assertEqual(float(x[0]), 0)
        self.assertEqual(float(x[-1]), 0)


class GeminiVertragTest(unittest.TestCase):
    def test_unbekanntes_modell_wird_nicht_fuer_jede_anfrage_erneut_versucht(self):
        d = {'candidates': [{'content': {'parts': [{'text': '{"ok":true}'}]}}]}
        fehler = urllib.error.HTTPError('https://example.test', 404, 'Not Found', {}, io.BytesIO(b'{}'))
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('skript.NICHT_VERFUEGBAR', set()), \
                patch('skript.urllib.request.urlopen', side_effect=[fehler, antwort(d), antwort(d)]) as netz, \
                patch('skript.time.sleep') as warten:
            for _ in range(2):
                self.assertEqual(skript.gemini('Pruefung', {}, modelle=['unbekannt', 'gemini-flash-latest'])[0], {'ok': True})
        self.assertEqual(netz.call_count, 3)
        warten.assert_not_called()

    def anfrage(self, modell, **kw):
        daten = {'candidates': [{'content': {'parts': [{'text': '{"ok":true}'}]}}]}
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('skript.urllib.request.urlopen', return_value=antwort(daten)) as netz:
            erg, _ = skript.gemini('konkreter Auftrag', {'type': 'OBJECT'},
                                    modelle=[modell], temperatur=0.1, **kw)
        self.assertEqual(erg, {'ok': True})
        return json.loads(netz.call_args.args[0].data)

    def test_medien_vor_auftrag_und_korrekte_bildtypen(self):
        d = self.anfrage('gemini-3.8-flash', bilder=[b'\x89PNG\r\n\x1a\nabc',
            b'RIFF1234WEBPabc', b'\xff\xd8abc'], dateien=[('video/mp4', 'video-uri')])
        p = d['contents'][0]['parts']
        self.assertEqual([e['inline_data']['mime_type'] for e in p[:3]],
                         ['image/png', 'image/webp', 'image/jpeg'])
        self.assertEqual(p[3]['file_data']['file_uri'], 'video-uri')
        self.assertEqual(p[-1], {'text': 'konkreter Auftrag'})
        self.assertEqual(base64.b64decode(p[0]['inline_data']['data']), b'\x89PNG\r\n\x1a\nabc')

    def test_gemini_drei_und_aliase_behalten_sampling_standardwerte(self):
        for modell in ('gemini-3.8-flash', 'gemini-flash-latest', 'gemini-flash-lite-latest'):
            self.assertNotIn('temperature', self.anfrage(modell)['generationConfig'])

    def test_aeltere_modelle_behalten_explizite_temperatur(self):
        self.assertEqual(self.anfrage('gemini-2.5-flash')['generationConfig']['temperature'], 0.1)

    def test_fehlendes_zweitpruefer_ergebnis_wird_nicht_als_faktenfreigabe_gedeutet(self):
        d = {'choices': [{'message': {'content': '{}'}}]}
        with patch.dict(os.environ, {'GROQ_API_KEY': 'test'}), \
                patch('zweit.urllib.request.urlopen', side_effect=lambda *a, **k: antwort(d)), \
                patch('zweit.time.sleep'):
            self.assertIsNone(zweit.pruefen('A factual claim.', 'A source.'))


class BildTest(TempTest):
    def png(self):
        b = io.BytesIO()
        Image.new('RGB', (768, 1360)).save(b, 'PNG')
        return b.getvalue()

    def test_nicht_erreichbare_pruefung_gibt_bild_nicht_frei(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('skript.gemini', side_effect=RuntimeError('Ausfall')):
            self.assertFalse(illustration.pruefen(self.png(), 'a factory')['ok'])

    def test_ohne_pruefer_wird_keine_bildgenerierung_bezahlt(self):
        with patch.dict(os.environ, {}, clear=True), patch('illustration._anfrage') as api:
            self.assertIsNone(illustration.bild('factory', 'bild.jpg'))
        api.assert_not_called()

    def test_korrektur_erhaelt_szene_und_uebernimmt_sichtbaren_fehler(self):
        szene = 'a worker assembling a bicycle, a workshop in 1900, warm window light'
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('illustration._anfrage', return_value=self.png()) as api, \
                patch('illustration.pruefen', side_effect=[{'ok': False, 'grund': 'Extra fingers'},
                                                         {'ok': True, 'grund': ''}]):
            self.assertEqual(illustration.bild(szene, 'bild.jpg'), Path('bild.jpg'))
        self.assertEqual(api.call_count, 2)
        prompt = api.call_args.args[1]['prompt']
        self.assertIn(szene, prompt)
        self.assertIn('Extra fingers', prompt)
        self.assertLessEqual(len(prompt), 2048)

    def test_klein_ref_wird_hochkant_generiert_ohne_unterstuetzte_steps_zu_erfinden(self):
        Path('figuren').mkdir()
        Image.new('RGB', (1000, 1000)).save('figuren/test.jpg')
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('illustration.FIGUREN', Path('figuren')), \
                patch('illustration._anfrage', return_value=self.png()) as api, \
                patch('illustration.pruefen', return_value={'ok': True, 'grund': ''}):
            illustration.bild('fictional worker in workshop', 'bild.jpg', 'test', figur=True)
        self.assertEqual(api.call_args.args[0], 'flux-2-klein-4b')
        self.assertGreater(api.call_args.args[1]['height'], api.call_args.args[1]['width'])
        self.assertNotIn('steps', api.call_args.args[1])

    def test_referenz_upload_begrenzt_groesse_und_erhaelt_original(self):
        Image.new('RGB', (1000, 800)).save('ref.jpg')
        d = {'success': True, 'result': {'image': base64.b64encode(b'bild').decode()}}
        with patch.dict(os.environ, {'CLOUDFLARE_AI_TOKEN': 'test'}), \
                patch('illustration.urllib.request.urlopen', return_value=antwort(d)) as api:
            self.assertEqual(illustration._anfrage('flux-2-klein-4b', {'prompt': 'scene'}, 'ref.jpg'), b'bild')
        body = api.call_args.args[0].data
        jpeg = body.split(b'Content-Type: image/jpeg\r\n\r\n')[1].split(b'\r\n--')[0]
        with Image.open(io.BytesIO(jpeg)) as im:
            self.assertLess(max(im.size), 512)
        with Image.open('ref.jpg') as im:
            self.assertEqual(im.size, (1000, 800))

    def test_langformat_referenzbild_bekommt_querformat_und_passende_bildkontrolle(self):
        Path('figuren').mkdir()
        Image.new('RGB', (1000, 1000)).save('figuren/test.jpg')
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('illustration.FIGUREN', Path('figuren')), \
                patch('illustration._anfrage', return_value=self.png()) as api, \
                patch('illustration.pruefen', return_value={'ok': True, 'grund': ''}) as pruefer:
            illustration.bild('fictional worker in workshop', 'bild.jpg', 'test', figur=True, videoformat='lang')
        self.assertEqual((api.call_args.args[1]['width'], api.call_args.args[1]['height']), (1360, 768))
        self.assertIn('landscape', api.call_args.args[1]['prompt'])
        self.assertEqual(pruefer.call_args.args[-1], 'lang')

    def test_unvollstaendige_oder_falsche_bilddatei_wird_nicht_gespeichert(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('illustration._anfrage', return_value=b'not an image'), \
                patch('illustration.pruefen') as pruefer:
            self.assertIsNone(illustration.bild('factory', 'bild.jpg'))
        self.assertFalse(Path('bild.jpg').exists())
        pruefer.assert_not_called()

    def test_bildidentitaet_wird_mit_referenz_geprueft(self):
        Path('ref.jpg').write_bytes(self.png())
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test'}), \
                patch('skript.gemini', return_value=({'ok': False, 'grund': 'Changed face'}, 'test')) as api:
            ergebnis = illustration.pruefen(self.png(), 'workshop', 'ref.jpg')
        self.assertFalse(ergebnis['ok'])
        self.assertEqual(len(api.call_args.kwargs['bilder']), 2)

    def test_stock_waehlt_beste_datei_und_verwechselt_alten_cache_nicht(self):
        h = {'id': 9, 'pageURL': 'https://pixabay/9', 'duration': 10, 'tags': 'factory',
             'videos': {'large': {'url': 'https://clip/large'}, 'medium': {'url': 'https://clip/medium'}}}
        Path('clips').mkdir()
        Path('clips/pixabay_9.mp4').write_bytes(b'old small video')
        downloads = []
        def netz(req, **kw):
            if 'api/videos/' in req.full_url:
                return antwort({'hits': [h]})
            downloads.append(req.full_url)
            return io.BytesIO(b'large video')
        with patch.dict(os.environ, {'PIXABAY_API_KEY': 'test'}), \
                patch('bauen.waehle', return_value=[h]), patch('urllib.request.urlopen', side_effect=netz):
            p, _ = bauen.clip_fuer('factory', set(), 10, 'A factory.')
        self.assertEqual(downloads, ['https://clip/large'])
        self.assertEqual(p.read_bytes(), b'large video')
        self.assertEqual(Path('clips/pixabay_9.mp4').read_bytes(), b'old small video')


class TonTest(TempTest):
    def test_britische_und_amerikanische_stimmen_bekommen_passende_phonetik(self):
        k = Mock()
        for stimme, sprache in [('bm_george', 'en-gb'), ('bf_emma', 'en-gb'), ('am_michael', 'en-us')]:
            ton.sprechen(k, 'The exact verified text.', stimme, 1.05)
            self.assertEqual(k.create.call_args.kwargs['lang'], sprache)
            self.assertEqual(k.create.call_args.args[0], 'The exact verified text.')

    def test_effekte_sind_kurz_klickfrei_und_unter_der_stimme(self):
        x = ton.effekt(np.ones(3000), 'impact', 1000)
        self.assertLessEqual(len(x), 800)
        self.assertEqual(x[0], 0)
        self.assertEqual(x[-1], 0)
        self.assertLessEqual(float(np.abs(x).max()), 0.201)

    def test_doppelte_dichte_und_ungueltige_effekte_werden_entfernt(self):
        e = [(0, 'riser'), (0, 'impact'), (0, 'impact'), (1, 'whoosh'),
             (1.1, 'whoosh'), (2, 'whoosh'), (None, 'pop'), (float('nan'), 'impact'), (10, 'pop')]
        self.assertEqual(ton.ereignisse(e, 10), [(0, 'impact'), (1, 'whoosh'), (2, 'whoosh')])

    def test_riser_endet_am_akzent_auch_wenn_er_frueh_kommt(self):
        x = np.ones(3000, dtype=np.float32).tobytes()
        with patch('bauen.subprocess.run', return_value=subprocess.CompletedProcess([], 0, x)):
            bauen.effekte_spur([(1, 'riser')], 3, 1000, 'effekte.wav')
        with wave.open('effekte.wav') as w:
            audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        self.assertGreater(np.abs(audio[:1000]).max(), 0)
        self.assertEqual(audio[0], 0)
        self.assertEqual(np.abs(audio[1000:]).max(), 0)

    def test_ueberlappende_effekte_clippen_nicht(self):
        spur = ton.begrenzen(np.array([1.5, -1.5, 0.0]))
        self.assertLessEqual(np.abs(spur).max(), 0.6)
        self.assertEqual(spur[0], -spur[1])


class SkriptLaengeTest(TempTest):
    def test_langformat_erreicht_schreiber_storypruefer_und_renderdaten(self):
        kanal = {'name': 'Test', 'format': 'geschichte', 'stimmen': ['bm_george'],
                 'videoformat': 'lang', 'laenge_s': [360, 480]}
        Path('kanal.json').write_text(json.dumps(kanal), encoding='utf-8')
        entwurf = {'thema': 'Firma', 'titel_zeile1': 'A story', 'titel_zeile2': 'A decision',
                   'schluesselwoerter': ['story'], 'beschreibung': 'A story.', 'hashtags': [],
                   'teile': [{'text': ' '.join(['fact'] * 30) + '.', 'suche': 'workshop'} for _ in range(30)]}
        quelle = {'name': 'Firma', 'quelle': 'Test', 'text': 'fact', 'url': 'https://test'}
        with patch('skript.hinweise', return_value=('', [quelle])), \
                patch('skript.gemini', side_effect=[(entwurf, 'test'), ({'ok': True, 'probleme': []}, 'test'),
                      ({'note': 10, 'kategorien': dict.fromkeys(skript.STORY_KATEGORIEN, 10),
                        'schwaechen': []}, 'test')]) as api, \
                patch('erfolg.waehlen', return_value='bm_george'), patch('erfolg.vorbilder', return_value=[]), \
                patch('zweit.pruefen', return_value=None):
            skript.main('kanal.json', 'skript.json', 'Firma')
        self.assertIn('long video', api.call_args_list[0].args[0])
        self.assertIn('3-5 chapters', api.call_args_list[-1].args[0])
        s = json.loads(Path('skript.json').read_text())
        self.assertEqual(s['videoformat'], 'lang')
        self.assertEqual(s['laenge_s'], [360, 480])

    def test_zu_langes_skript_wird_vor_faktencheck_gekuerzt(self):
        kanal = {'name': 'Test', 'format': 'geschichte', 'stimmen': ['bm_george'], 'laenge_s': [62, 90]}
        Path('kanal.json').write_text(json.dumps(kanal), encoding='utf-8')
        kurz = {'thema': 'Firma', 'titel_zeile1': 'A story', 'titel_zeile2': 'A decision',
                'schluesselwoerter': ['story'], 'beschreibung': 'A story.', 'hashtags': [],
                'teile': [{'text': ' '.join(['fact'] * 30) + '.', 'suche': 'workshop'} for _ in range(6)]}
        lang = copy.deepcopy(kurz)
        for t in lang['teile']:
            t['text'] *= 2
        quelle = {'name': 'Firma', 'quelle': 'Test', 'text': 'fact', 'url': 'https://test'}
        with patch('skript.hinweise', return_value=('', [quelle])), \
                patch('skript.gemini', side_effect=[(lang, 'test'), (kurz, 'test'),
                    ({'ok': True, 'probleme': []}, 'test'),
                    ({'note': 10, 'kategorien': dict.fromkeys(skript.STORY_KATEGORIEN, 10),
                      'schwaechen': []}, 'test')]) as api, \
                patch('erfolg.waehlen', return_value='bm_george'), patch('erfolg.vorbilder', return_value=[]), \
                patch('zweit.pruefen', return_value=None):
            skript.main('kanal.json', 'skript.json', 'Firma')
        self.assertIn('maximum is', api.call_args_list[1].args[0])
        gespeichert = json.loads(Path('skript.json').read_text())
        self.assertEqual(sum(len(t['text'].split()) for t in gespeichert['teile']), 180)
        self.assertEqual(gespeichert['prompt_version'], prompts.VERSION)


if __name__ == '__main__':
    unittest.main()
