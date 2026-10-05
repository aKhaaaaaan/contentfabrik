"""Echte Bildgeometrie, Untertitelzeiten und vorsichtige Zuschauer-Auswertung."""
import copy
import datetime
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image
from test_betrieb import TempTest, SKRIPT, KRITIK
import bauen
import dramaturgie
import doku
import erfolg
import kritik
import lernen
import prompts
import rendercache
import ton


class AkzentTest(unittest.TestCase):
    def setUp(self):
        self.teile = [{'text': 'It started with playing cards.', 'bildtext': 'playing cards'}]
        self.words = [{'w': w, 's': i * .4, 'e': i * .4 + .3}
                      for i, w in enumerate(self.teile[0]['text'].split())]

    def test_akzent_erscheint_beim_gesprochenen_detail(self):
        a = dramaturgie.akzente(self.teile, self.words, [4])[0]
        self.assertAlmostEqual(a['s'], 1.2)
        self.assertEqual(a['text'], 'playing cards')
        self.assertLessEqual(a['e'], 4)

    def test_erfundene_phrase_und_ass_befehle_werden_nicht_angezeigt(self):
        for text in ('a secret fortune', r'playing {\pos(0,0)}cards', 'cards'):
            self.teile[0]['bildtext'] = text
            self.assertEqual(dramaturgie.akzente(self.teile, self.words, [4]), [])

    def test_phrase_aus_falschem_abschnitt_oder_ueber_lange_pause_ist_kein_akzent(self):
        self.assertEqual(dramaturgie.akzente(self.teile, self.words, [1]), [])
        self.words[-1]['s'], self.words[-1]['e'] = 3.2, 3.5
        self.assertEqual(dramaturgie.akzente(self.teile, self.words, [4]), [])

    def test_akzente_werden_nicht_auf_jeden_abschnitt_gepackt(self):
        teile = self.teile * 3
        words = [dict(w, s=w['s'] + i * 4, e=w['e'] + i * 4) for i in range(3) for w in self.words]
        self.assertEqual([a['teil'] for a in dramaturgie.akzente(teile, words, [4] * 3)], [0, 2])


class GestaltungTest(TempTest):
    def setUp(self):
        super().setUp()
        bauen.format_setzen()
        self.addCleanup(bauen.format_setzen)
        self.addCleanup(bauen.FORTSCHRITT.update, plaetze=[], aktuell=None)

    def test_hohe_fotos_und_breite_karten_bleiben_vor_untertiteln_und_knoepfen(self):
        for art in ('short', 'lang'):
            bauen.format_setzen(art)
            for size, foto in (((800, 1600), True), ((1800, 400), False)):
                Image.new('RGB', size, (230, 25, 40)).save('quelle.png')
                arr = np.array(bauen.karten_ebene('quelle.png', kasten=foto))
                ys, xs = np.where((arr[:, :, 0] > 200) & (arr[:, :, 1] < 60) & (arr[:, :, 3] > 200))
                self.assertGreaterEqual(xs.min(), bauen.LAYOUT['links'])
                self.assertLessEqual(xs.max(), bauen.LAYOUT['rechts'])
                if art == 'lang':
                    self.assertLess(xs.max() + 30, bauen.LAYOUT['akzent_x'] - 210)
                    self.assertLess(ys.max() + 32, bauen.LAYOUT['untertitel_y'] - 80)
                else:
                    self.assertLess(ys.max() + 32, bauen.LAYOUT['akzent_y'] - 30)
                self.assertEqual(arr.shape[:2], (bauen.H, bauen.B))

    def test_untertitel_halten_nicht_ueber_lange_sprechpausen(self):
        words = [{'w': 'Pause.', 's': 0, 'e': .4}, {'w': 'Continue.', 's': 3, 'e': 3.5}]
        bauen.untertitel(words, 'text.ass')
        ass = Path('text.ass').read_text()
        self.assertIn('0:00:00.65', ass)
        self.assertIn(r'\pos(486,1420)', ass)
        self.assertNotIn(r'\fscx108', ass)

    def test_lange_woerter_passen_in_die_tatsaechliche_pixelbreite(self):
        bauen.untertitel([{'w': 'INTERNATIONALIZATION', 's': 0, 'e': 1}], 'text.ass')
        ass = Path('text.ass').read_text()
        import re
        groesse = int(re.search(r'\\fs(\d+)', ass)[1])
        f = bauen.schrift(groesse, str(bauen.SCHRIFTEN / 'Anton-Regular.ttf'))
        self.assertLessEqual(f.getlength('INTERNATIONALIZATION'), 768)
        self.assertGreaterEqual(groesse, 52)

    def test_ass_eingaben_duerfen_keine_position_einschleusen(self):
        bauen.untertitel([{'w': r'{\pos(0,0)}word', 's': 0, 'e': 1}], 'text.ass')
        self.assertNotIn(r'\pos(0,0)', Path('text.ass').read_text())

    def test_defekte_wortzeiten_brechen_die_darstellung_ab(self):
        for words in ([{'w': 'word', 's': 1, 'e': .5}],
                      [{'w': 'one', 's': 1, 'e': 1.5}, {'w': 'two', 's': 1, 'e': 2}]):
            with self.assertRaises(ValueError):
                bauen.untertitel(words, 'text.ass')

    def test_whisper_nullzeiten_werden_ohne_erfundene_zeiten_mit_nachbarwort_gezeigt(self):
        bauen.untertitel([{'w': 'the', 's': .1, 'e': .1},
                         {'w': 'founder', 's': .1, 'e': .6}], 'text.ass')
        ass = Path('text.ass').read_text()
        self.assertIn('THE FOUNDER', ass)
        self.assertIn('0:00:00.10,0:00:00.85', ass)

    def test_querformat_untertitel_und_demo_erhalten_ihre_groesse(self):
        bauen.format_setzen('lang')
        bauen.untertitel([{'w': 'Evidence.', 's': 0, 'e': 1}], 'text.ass')
        ass = Path('text.ass').read_text()
        self.assertIn('PlayResX: 1920', ass)
        self.assertIn('PlayResY: 1080', ass)
        self.assertIn(r'\pos(960,965)', ass)
        with patch('bauen.subprocess.run') as ffmpeg:
            bauen.demo_stueck('demo.mp4', 'ebene.png', 'mini.png', 5, 'aus.mp4')
        graph = ffmpeg.call_args.args[0][ffmpeg.call_args.args[0].index('-filter_complex') + 1]
        self.assertNotIn('zoompan', graph)
        self.assertIn('scale=1240:420', graph)

    def test_querformat_akzent_ist_neben_dem_bild_lesbar_und_keine_textwand(self):
        bauen.format_setzen('lang')
        f, lines, x, _ = bauen.bildtext_layout('Two different machines')
        self.assertEqual(len(lines), 2)
        self.assertGreaterEqual(f.size, 42)
        self.assertLessEqual(max(f.getlength(line) for line in lines), 420)
        self.assertGreater(x - 210, bauen.LAYOUT['foto'][2] + 30)

    def test_palette_und_format_machen_abschnittcache_ungueltig(self):
        for aenderung in ({'titel_farbe': '#FFC83D'}, {'videoformat': 'lang'}):
            self.assertNotEqual(rendercache.stueck_key(SKRIPT, 0, 10, 'code'),
                                rendercache.stueck_key(dict(SKRIPT, **aenderung), 0, 10, 'code'))
        self.assertEqual(bauen.akzent_farbe({'titel_farbe': '#FFC83D'}), (255, 200, 61))


class ZuschauerTest(unittest.TestCase):
    def setUp(self):
        self.v = {'titel': 'A story', 'aufrufe': 200, 'oeffentlich': True, 'veroeffentlicht': '2026-09-20',
                  'kurve': [[0, 1], [.01, .99], [.02, .7], [.03, .68], [.04, .67]]}
        self.unsere = {erfolg._norm('A story'): {'abschnitte_s': [1, 4, 5],
                       'gliederung': ['Opening', 'Evidence', 'Conclusion']}}

    def test_lokaler_verlust_wird_dem_richtigen_abschnitt_zugeordnet(self):
        e = erfolg.absprung(self.v, self.unsere)
        self.assertEqual(e['teil'], 0)
        self.assertAlmostEqual(e['verlust'], .29)
        self.assertIn('does not establish', e['text'])

    def test_wenig_daten_einzelner_ausreisser_und_natuerlicher_verlauf_sind_keine_lehre(self):
        for daten in ({'aufrufe': 12}, {'kurve': [[0, 1], [.01, .5], [.02, .99]]},
                      {'kurve': [[0, .6], [.01, .58], [.02, .55], [.03, .49]]},
                      {'kurve': [[0, 1], [.01, float('nan')], [.02, .5]]}):
            self.assertIsNone(erfolg.absprung(dict(self.v, **daten), self.unsere))

    def test_kurve_wird_bei_wachstum_und_nach_einer_woche_neu_geprueft(self):
        heute = datetime.date(2026, 10, 5)
        v = dict(self.v, kurve_stand='2026-10-04', kurve_aufrufe=200)
        self.assertFalse(erfolg.kurve_faellig(v, heute))
        self.assertTrue(erfolg.kurve_faellig(dict(v, aufrufe=300), heute))
        self.assertTrue(erfolg.kurve_faellig(dict(v, kurve_stand='2026-09-28'), heute))
        self.assertFalse(erfolg.kurve_faellig(dict(v, oeffentlich=False), heute))
        self.assertFalse(erfolg.kurve_faellig(dict(v, aufrufe=20), heute))

    def test_shorts_und_langvideos_werden_nicht_gemeinsam_als_vorbilder_gewertet(self):
        short = dict(self.v, einstellungen={}, hook='Short', anteil_prozent=80)
        lang = dict(self.v, einstellungen={'videoformat': 'lang'}, hook='Long', anteil_prozent=40)
        with patch('erfolg.laden', return_value={'videos': {'short': short, 'lang': lang}}):
            self.assertEqual([v['hook'] for v in erfolg._bewertet('test')], ['Short'])
            self.assertEqual([v['hook'] for v in erfolg._bewertet('test', 'lang')], ['Long'])


class LangformatTest(unittest.TestCase):
    def test_gemessene_dauer_bleibt_in_natuerlichen_sprechgrenzen(self):
        self.assertLess(ton.tempo_fuer(330, [360, 480], 1.05, 'lang', 6), 1.05)
        self.assertEqual(ton.tempo_fuer(400, [360, 480], 1.05, 'lang', 6), 1.05)
        self.assertLessEqual(ton.tempo_fuer(900, [360, 480], 1.05, 'lang', 6), 1.15)
        self.assertGreaterEqual(ton.tempo_fuer(200, [360, 480], 1.05, 'lang', 6), .9)
    def test_doku_bleibt_bei_schwacher_story_auch_im_direkten_sendeaufruf_gesperrt(self):
        for story in (None, {'note': 8, 'kategorien': dict.fromkeys(doku.KATEGORIEN, 9)},
                      {'note': 10, 'kategorien': dict.fromkeys(doku.KATEGORIEN, 7)}):
            with patch('doku.urllib.request.urlopen') as netz, self.assertRaises(ValueError):
                doku.senden(Path('missing.md'), {'pruefung': {'ok': True}, 'story': story})
            netz.assert_not_called()

    def test_formatregeln_und_laenge_sind_getrennt(self):
        self.assertEqual(dramaturgie.laengen({'videoformat': 'lang'}), [360, 600])
        self.assertIn('3-5 chapters', dramaturgie.auftrag({'videoformat': 'lang'}))
        self.assertIn('first frame', dramaturgie.auftrag({}))
        with self.assertRaises(ValueError):
            dramaturgie.laengen({'laenge_s': [60, 600]})
        with self.assertRaises(ValueError):
            dramaturgie.laengen({'videoformat': 'lang', 'laenge_s': [600, 300]})

    def test_langvideo_nimmt_nicht_die_short_zeitgrenze(self):
        info = {'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080,
                            'codec_name': 'h264', 'avg_frame_rate': '30/1'},
                           {'codec_type': 'audio', 'codec_name': 'aac', 'sample_rate': '48000', 'channels': 2}],
                'format': {'duration': '400'}}
        with patch('subprocess.run', side_effect=[subprocess.CompletedProcess([], 0, json.dumps(info)),
                  subprocess.CompletedProcess([], 0, stderr='I: -14.0 LUFS')]):
            self.assertEqual(kritik.technik('video.mp4', {'videoformat': 'lang'})['befunde'], [])


class LernenQualitaetTest(TempTest):
    def test_hoeherer_score_mit_neuem_publikationshindernis_ist_kein_erfolg(self):
        nachher = dict(KRITIK, note=10, probleme=[{'schwere': 'mittel', 'text': 'Unlesbarer Text'}])
        e = lernen.korrektur_eintragen('test', KRITIK, nachher, {'aktionen': []}, 10, 'a')
        self.assertFalse(e['verbessert'])
