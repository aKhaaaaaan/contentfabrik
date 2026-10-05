import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
from test_betrieb import TempTest, SKRIPT, KRITIK
import lernen
import nachbessern
import rendercache


class PlanTest(TempTest):
    def setUp(self):
        super().setUp()
        self.s = copy.deepcopy(SKRIPT)
        self.s['teile'] = [{'text': 'First fact.', 'suche': 'first', 'platz': 2, 'quelle_url': 'https://a'},
                           {'text': 'Second fact.', 'suche': 'second', 'platz': 1, 'quelle_url': 'https://b'}]
        self.m = {'abschnitte_s': [10, 20]}
        self.k = copy.deepcopy(KRITIK)
        self.k['probleme'] = [{'art': 'bild_passt_nicht', 'zeit': '00:15', 'text': 'Falsche Firma im Bild'}]
        self.antwort = {'bilder': [{'index': 1, 'suche': 'specific factory', 'szene': 'accurate factory',
                                   'bildmodus': 'stock'}], 'texte': []}

    def test_nur_beanstandetes_bild_aendert_sich(self):
        with patch('skript.gemini', return_value=(self.antwort, 'test')):
            neu, plan = nachbessern.planen(self.s, self.k, self.m, {}, 'test')
        self.assertEqual(neu['teile'][0], self.s['teile'][0])
        self.assertEqual(neu['teile'][1]['text'], self.s['teile'][1]['text'])
        self.assertEqual(neu['teile'][1]['quelle_url'], 'https://b')
        self.assertEqual(neu['teile'][1]['platz'], 1)
        self.assertEqual(plan['teile'], [1])
        self.assertEqual(self.s['teile'][1]['suche'], 'second')

    def test_fremder_index_ist_kein_korrekturauftrag(self):
        self.antwort['bilder'][0]['index'] = 0
        with patch('skript.gemini', return_value=(self.antwort, 'test')):
            with self.assertRaises(ValueError):
                nachbessern.planen(self.s, self.k, self.m, {}, 'test')

    def test_unbeauftragter_sprechtext_wird_abgelehnt(self):
        self.antwort['texte'] = [{'index': 1, 'text': 'Invented fact.'}]
        with patch('skript.gemini', return_value=(self.antwort, 'test')):
            with self.assertRaises(ValueError):
                nachbessern.planen(self.s, self.k, self.m, {}, 'test')

    def test_textkorrektur_muss_neu_durch_faktencheck(self):
        self.s['belege'] = [{'name': 'Firma', 'text': 'First fact. Second fact.'}]
        self.k['probleme'] = [{'art': 'hook', 'zeit': '00:00', 'text': 'Hook langweilig'}]
        v = {'bilder': [], 'texte': [{'index': 0, 'text': 'A stronger, true opening.'}]}
        with patch('skript.gemini', return_value=(v, 'test')), patch('nachbessern.faktencheck') as check:
            neu, _ = nachbessern.planen(self.s, self.k, self.m, {}, 'test')
        check.assert_called_once_with(neu)

    def test_faktencheck_fehler_verwirft_sprechtextkorrektur(self):
        self.s['belege'] = [{'text': 'First fact.'}]
        self.k['probleme'] = [{'art': 'hook', 'zeit': '00:00', 'text': 'Hook langweilig'}]
        v = {'bilder': [], 'texte': [{'index': 0, 'text': 'Invented opening.'}]}
        with patch('skript.gemini', return_value=(v, 'test')), \
                patch('nachbessern.faktencheck', side_effect=ValueError('unbelegt')):
            with self.assertRaises(ValueError):
                nachbessern.planen(self.s, self.k, self.m, {}, 'test')
        self.assertEqual(self.s['teile'][0]['text'], 'First fact.')

    def test_hook_ohne_quelltexte_bleibt_erhalten(self):
        self.k['probleme'] = [{'art': 'hook', 'zeit': '00:00', 'text': 'Hook langweilig'}]
        with patch('skript.gemini') as ki:
            neu, plan = nachbessern.planen(self.s, self.k, self.m, {}, 'test')
        self.assertIsNone(neu)
        self.assertTrue(plan['offen'])
        ki.assert_not_called()

    def test_fehlende_zeitmarke_waehlt_nicht_beliebigen_abschnitt(self):
        self.k['probleme'][0]['zeit'] = '-'
        with patch('skript.gemini') as ki:
            neu, _ = nachbessern.planen(self.s, self.k, self.m, {}, 'test')
        self.assertIsNone(neu)
        ki.assert_not_called()

    def test_untertitelkorrektur_erhaelt_sprechtext(self):
        self.k['probleme'] = [{'art': 'text', 'zeit': '00:15', 'text': 'Untertitel springen'}]
        neu, plan = nachbessern.planen(self.s, self.k, self.m, {}, 'test')
        self.assertEqual(neu['teile'], self.s['teile'])
        self.assertEqual(plan['aktionen'][0]['art'], 'untertitel')

    def test_waehlt_die_schwaechste_kategorie_und_nur_eine_eingriffsart(self):
        self.k['kategorien'] = {'text': 3, 'bild_passt': 6}
        self.k['probleme'].append({'art': 'text', 'zeit': '00:02', 'text': 'Text abgeschnitten'})
        with patch('skript.gemini') as ki:
            neu, plan = nachbessern.planen(self.s, self.k, self.m, {}, 'test')
        self.assertEqual(plan['schwerpunkt'], 'untertitel')
        self.assertEqual(len(plan['aktionen']), 1)
        self.assertEqual(neu['teile'], self.s['teile'])
        ki.assert_not_called()

    def test_stimmen_bleiben_in_der_auswahl_des_betreibers(self):
        self.s['stimme'] = 'a'
        self.k['probleme'] = [{'art': 'stimme', 'zeit': '00:00', 'text': 'Stimme unnatuerlich'}]
        neu, _ = nachbessern.planen(self.s, self.k, self.m, {'stimmen': ['a', 'b']}, 'test')
        self.assertEqual(neu['stimme'], 'b')

    def test_falsche_zahl_sperrt_trotz_ki_zustimmung(self):
        self.s['belege'] = [{'text': 'Founded in 1980.'}]
        self.s['teile'][0]['text'] = 'Founded in 1999.'
        with patch('skript.gemini', return_value=({'ok': True}, 'test')):
            with self.assertRaises(ValueError):
                nachbessern.faktencheck(self.s)


class ZeitTest(unittest.TestCase):
    def test_grenze_gehoert_zum_folgenden_abschnitt(self):
        self.assertEqual(nachbessern.abschnitte('00:10', [10, 20]), [1])

    def test_bereich_deckt_mehrere_abschnitte_ab(self):
        self.assertEqual(nachbessern.abschnitte('00:09–00:12', [10, 20]), [0, 1])

    def test_invalid_und_videoende_sind_keine_ziele(self):
        for zeit in ('-', '00:99', '00:30', '00:20-00:10', 'irgendwann'):
            self.assertEqual(nachbessern.abschnitte(zeit, [10, 20]), [])
        self.assertEqual(nachbessern.abschnitte('00:01', [float('nan')]), [])


class GedaechtnisTest(TempTest):
    def test_regeln_und_gelerntes_bleiben_beide_erhalten(self):
        lernen.speichern('test', {'regeln': ['alte Regel']})
        lernen.korrektur_eintragen('test', dict(KRITIK, note=7), KRITIK,
            {'aktionen': [{'art': 'untertitel', 'variante': 'ruhig'}]}, 10, 'a')
        with patch('skript.gemini', return_value=({'regeln': ['neue Regel']}, 'test')):
            lernen.aktualisieren('test', dict(KRITIK, probleme=[{'art': 'text', 'text': 'springt'}]))
        d = lernen.laden('test')
        self.assertEqual(d['regeln'], ['neue Regel'])
        self.assertEqual(len(d['korrekturen']), 1)

    def test_technik_rueckschritt_ist_kein_erfolg(self):
        k = copy.deepcopy(KRITIK)
        k['note'] = 10
        k['technik']['befunde'] = ['Ton fehlt']
        e = lernen.korrektur_eintragen('test', KRITIK, k, {'aktionen': []}, 10, 'a')
        self.assertFalse(e['verbessert'])

    def test_wiederholter_eintrag_zaehlt_nur_einmal(self):
        for _ in range(2):
            lernen.korrektur_eintragen('test', KRITIK, KRITIK, {'aktionen': []}, 10, 'a')
        self.assertEqual(len(lernen.laden('test')['korrekturen']), 1)

    def test_gemessene_erfolge_beeinflussen_auswahl_erst_mit_daten(self):
        liste = []
        for o, erfolg in [('ruhig', False), ('kompakt', True)]:
            liste += [{'aktionen': [{'art': 'untertitel', 'variante': o}], 'verbessert': erfolg}] * 3
        lernen.speichern('test', {'korrekturen': liste})
        self.assertEqual(lernen.waehlen('test', 'untertitel', ['ruhig', 'kompakt']), 'kompakt')
        self.assertEqual(lernen.waehlen('anderer', 'untertitel', ['ruhig', 'kompakt']), 'ruhig')

    def test_mehrere_aenderungen_beweisen_keine_einzelne_wirkung(self):
        lernen.speichern('test', {'korrekturen': [{'aktionen': [
            {'art': 'untertitel', 'variante': 'ruhig'}, {'art': 'stimme', 'variante': 'a'}],
            'verbessert': True}] * 3})
        self.assertEqual(lernen.waehlen('test', 'untertitel', ['ruhig', 'kompakt']), 'ruhig')

    def test_erfolgreiche_profile_werden_fuer_neue_videos_empfohlen(self):
        e = {'aktionen': [{'art': 'untertitel', 'variante': 'kompakt'}], 'verbessert': True}
        lernen.speichern('test', {'korrekturen': [e, e]})
        self.assertEqual(lernen.erprobte_einstellungen('test'), {})
        lernen.speichern('test', {'korrekturen': [e, e, e]})
        self.assertEqual(lernen.erprobte_einstellungen('test'), {'untertitel_profil': 'kompakt'})

    def test_erfolglose_profile_werden_nicht_zu_standard(self):
        e = {'aktionen': [{'art': 'untertitel', 'variante': 'kompakt'}], 'verbessert': False}
        lernen.speichern('test', {'korrekturen': [e] * 5})
        self.assertEqual(lernen.erprobte_einstellungen('test'), {})

    def test_fehlende_pruefungen_beeinflussen_weder_auswahl_noch_standard(self):
        e = {'aktionen': [{'art': 'untertitel', 'variante': 'ruhig'}],
             'verbessert': False, 'auswertbar': False}
        lernen.speichern('test', {'korrekturen': [e] * 5})
        self.assertEqual(lernen.waehlen('test', 'untertitel', ['ruhig', 'kompakt']), 'ruhig')
        self.assertEqual(lernen.erprobte_einstellungen('test'), {})


class CacheTest(TempTest):
    def test_bildaenderung_erhaelt_audio_aber_nicht_betroffenen_clip(self):
        a = copy.deepcopy(SKRIPT)
        b = copy.deepcopy(a)
        b['teile'][0]['suche'] = 'new picture'
        self.assertEqual(rendercache.audio_key(a, 'code'), rendercache.audio_key(b, 'code'))
        self.assertNotEqual(rendercache.stueck_key(a, 0, 10, 'code'), rendercache.stueck_key(b, 0, 10, 'code'))

    def test_sprechtextaenderung_macht_audio_unbrauchbar(self):
        b = copy.deepcopy(SKRIPT)
        b['teile'][0]['text'] = 'Changed fact.'
        self.assertNotEqual(rendercache.audio_key(SKRIPT, 'code'), rendercache.audio_key(b, 'code'))

    def test_untertitelprofil_aendert_keine_rohen_clips(self):
        b = dict(SKRIPT, untertitel_profil='kompakt')
        self.assertEqual(rendercache.stueck_key(SKRIPT, 0, 10, 'code'), rendercache.stueck_key(b, 0, 10, 'code'))

    def test_nur_vollstaendige_lokale_dateien_duerfen_wiederverwendet_werden(self):
        Path('clip.mp4').write_bytes(b'video')
        self.assertTrue(rendercache.dateien_ok('.', ['clip.mp4']))
        self.assertFalse(rendercache.dateien_ok('.', ['../clip.mp4']))
        Path('clip.mp4').write_bytes(b'')
        self.assertFalse(rendercache.dateien_ok('.', ['clip.mp4']))

    def test_bauer_verwendet_audio_und_unveraenderte_abschnitte(self):
        import bauen
        from PIL import Image
        s = copy.deepcopy(SKRIPT)
        s['teile'] = [{'text': 'First.', 'suche': 'a'}, {'text': 'Second.', 'suche': 'b'}]
        code = hashlib.sha256(Path(bauen.__file__).read_bytes() + Path(bauen.prompts.__file__).read_bytes()
                              + Path(bauen.audioqualitaet.__file__).read_bytes()
                              + Path(bauen.dramaturgie.__file__).read_bytes()
                              + Path(bauen.__file__).with_name('illustration.py').read_bytes()
                              + Path(bauen.__file__).with_name('infografik.py').read_bytes()
                              + Path(bauen.__file__).with_name('bibliothek.py').read_bytes()
                              + (Path(bauen.__file__).resolve().parents[1] / 'assets/illustrationen/katalog.json').read_bytes()).hexdigest()
        Path('alt').mkdir()
        Path('alt/stimme.wav').write_bytes(b'audio')
        Path('alt/woerter.json').write_text(json.dumps([
            {'w': 'First.', 's': 0, 'e': 1}, {'w': 'Second.', 's': 3, 'e': 4}]), encoding='utf-8')
        for i in range(2):
            Path(f'alt/stueck_{i:02d}.mp4').write_bytes(b'video')
        rendercache.speichern('alt', {'audio': {'key': rendercache.audio_key(s, code),
            'rate': 24000, 'laengen': [3, 4], 'tempo': 1.05},
            'stuecke': {str(i): {'key': rendercache.stueck_key(s, i, d, code),
                'dateien': [f'stueck_{i:02d}.mp4'], 'quellen': [], 'ereignisse': [], 'fotos': [],
                'material_id': f'asset-{i}', 'material_art': 'clip'}
                for i, d in enumerate([3, 4])}})
        s['teile'][1]['suche'] = 'corrected'
        s['teile'][1]['bildmodus'] = 'stock'
        Path('neu').mkdir()
        Path('neu/skript.json').write_text(json.dumps(s), encoding='utf-8')
        Path('stock.mp4').write_bytes(b'new source clip')
        shots = [{'teil': t, 'phase': i, 's': sum([3, 4][:i]), 'dauer_s': d}
                 for i, (t, d) in enumerate(zip(s['teile'], [3, 4]))]
        def ffmpeg(args, **kw):
            (Path(kw.get('cwd', '.')) / args[-1]).write_bytes(b'video')
            return subprocess.CompletedProcess(args, 0)
        with patch('bauen.subprocess.run', side_effect=ffmpeg), \
                patch('bauen.bildplan.vorbereiten', return_value=(shots, {})), \
                patch('bauen.bild_fuer', return_value=Image.new('RGBA', (8, 8))), \
                patch('bauen.clip_fuer', return_value=(Path('stock.mp4'), {'quelle': 'Pixabay', 'id': 3})), \
                patch('bauen.karte_fuer', return_value=None), patch('bauen.musik_holen', return_value=(None, None)), \
                patch('bauen.effekte_spur'), patch('bauen.foto_fuer', return_value=(None, None)):
            bauen.main('neu/skript.json', 'neu', 'alt')
        m = json.loads(Path('neu/messung.json').read_text())
        self.assertTrue(m['stimme_wiederverwendet'])
        self.assertEqual(m['stuecke_wiederverwendet'], 1)
        self.assertEqual(m['stuecke_neu'], 1)
        self.assertEqual(Path('neu/stuecke.txt').read_text().splitlines(),
                         ["file 'stueck_00.mp4'", "file 'stueck_01.mp4'"])


if __name__ == '__main__':
    unittest.main()
