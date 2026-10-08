"""Regressionspruefungen ohne API-Zugaenge, Modelle oder Telegram-Nachrichten."""
import copy
import html
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time
import shutil
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
import budget
import freigabe
import kritik
import lauf
from qualitaet import bewerten, STORY_KATEGORIEN, VIDEO_KATEGORIEN


SKRIPT = {'kanal': 'Test', 'thema': 'Firma', 'titel': ['Eine', 'Geschichte'],
          'teile': [{'text': 'How did this happen?'}], 'beschreibung': 'Beschreibung',
          'hashtags': [], 'pruefung': {'ok': True},
          'story': {'note': 9, 'kategorien': dict.fromkeys(STORY_KATEGORIEN, 9), 'schwaechen': []}}
def audio_fixture(sha, art='short'):
    """Explizit kuenstliche ASR-Daten fuer die Zugangskontrolle, keine Messung."""
    worte = 'Be sure to like share and save this video'.split()
    roh = {'dauer_s': 70, 'sprache': 'en', 'woerter': [
        {'w': w, 's': start + i * .15, 'e': start + (i + 1) * .15, 'p': .99}
        for start in ([8, 68] if art == 'lang' else [68]) for i, w in enumerate(worte)]}
    return {'version': 1, 'ok': True, 'befunde': [], 'video_sha256': sha, 'videoformat': art, 'roh': roh}


TEST_SHA = hashlib.sha256(b'gepruefter-testfilm').hexdigest()
KRITIK = {'note': 9, 'technik': {'befunde': [], 'dauer_s': 70, 'fps': 30, 'lufs': -14},
          'video_sha256': TEST_SHA, 'audio_pruefung': audio_fixture(TEST_SHA),
          'probleme': [], 'fazit': 'Gut', 'kategorien': dict.fromkeys(VIDEO_KATEGORIEN, 9)}


class TempTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path.cwd()
        os.chdir(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.chdir, self.cwd)


class QualitaetTest(unittest.TestCase):
    def test_gueltige_videos_von_sieben_bis_zehn_werden_freigegeben(self):
        k = copy.deepcopy(KRITIK)
        k['note'] = 6
        self.assertTrue(bewerten(SKRIPT, k)[1])
        for n in (7, 8, 9, 10):
            k['note'] = n
            k['kategorien'] = dict.fromkeys(VIDEO_KATEGORIEN, 7)
            s = copy.deepcopy(SKRIPT)
            s['story'] = {'note': n, 'kategorien': dict.fromkeys(STORY_KATEGORIEN, 7)}
            self.assertEqual(bewerten(s, k), (n, []))

    def test_hohe_gesamtnote_verdeckt_keinen_schwachen_bereich(self):
        for feld in VIDEO_KATEGORIEN:
            k = copy.deepcopy(KRITIK)
            k['note'] = 10
            k['kategorien'][feld] = 6
            self.assertTrue(bewerten(SKRIPT, k)[1])
        for feld in STORY_KATEGORIEN:
            s = copy.deepcopy(SKRIPT)
            s['story']['kategorien'][feld] = 5 if feld == 'teilbarkeit' else 6
            self.assertTrue(bewerten(s, KRITIK)[1])

    def test_teilbarkeit_prognose_sechs_sperrt_keine_bestandene_story(self):
        s = copy.deepcopy(SKRIPT)
        s['story']['note'] = 7
        s['story']['kategorien']['teilbarkeit'] = 6
        self.assertEqual(bewerten(s, KRITIK)[1], [])
        s['story']['kategorien']['hook'] = 6
        self.assertTrue(bewerten(s, KRITIK)[1])

    def test_schwere_und_fehlende_problembewertung_sperren(self):
        for schwere in ('mittel', 'schwer', None, 'unknown'):
            k = dict(KRITIK, probleme=[{'schwere': schwere, 'text': 'Stimme schwer verstaendlich'}])
            self.assertTrue(bewerten(SKRIPT, k)[1])
        self.assertFalse(bewerten(SKRIPT, dict(KRITIK, probleme=[{'schwere': 'leicht'}]))[1])

    def test_story_fehlt_oder_ist_schwach_sperrt(self):
        for story in (None, {}, {'note': 6, 'kategorien': dict.fromkeys(STORY_KATEGORIEN, 9)}):
            self.assertTrue(bewerten(dict(SKRIPT, story=story), KRITIK)[1])

    def test_fehlende_und_defekte_pruefungen_sperren(self):
        for k in (None, {}, [], {'note': 10}, {'note': 10, 'technik': {'befunde': []}}):
            with self.subTest(k=k):
                self.assertTrue(bewerten(SKRIPT, k)[1])

    def test_ungepruefte_fakten_sperren(self):
        for ok in (False, None, 1, 'true'):
            s = dict(SKRIPT, pruefung={'ok': ok})
            self.assertTrue(bewerten(s, KRITIK)[1])
        self.assertTrue(bewerten({}, KRITIK)[1])

    def test_niedrige_ungueltige_noten_sperren(self):
        for note in (6, 0, 11, None, True, '9', float('nan'), float('inf')):
            with self.subTest(note=note):
                self.assertTrue(bewerten(SKRIPT, dict(KRITIK, note=note))[1])

    def test_technikfehler_sperrt_auch_zehn(self):
        k = copy.deepcopy(KRITIK)
        k['note'] = 10
        k['technik']['befunde'] = ['keine Tonspur']
        self.assertIn('keine Tonspur', bewerten(SKRIPT, k)[1])

    def test_ungueltige_messwerte_sperren(self):
        for feld in ('dauer_s', 'fps', 'lufs'):
            k = copy.deepcopy(KRITIK)
            k['technik'][feld] = float('nan')
            self.assertTrue(bewerten(SKRIPT, k)[1])


class BudgetTest(TempTest):
    def test_ersatzfenster_bekommt_nur_rest(self):
        r = budget.reservieren('test', 1800)
        self.assertEqual(budget.rest('test', 1800), 0)
        budget.abschliessen('test', r, 1100)
        r2 = budget.reservieren('test', 1800)
        self.assertEqual(r2[0], 700)
        budget.abschliessen('test', r2, 250)
        self.assertEqual(budget.rest('test', 1800), 450)

    def test_harter_abbruch_behaelt_reservierung(self):
        budget.reservieren('test', 1800)
        self.assertEqual(budget.reservieren('test', 1800)[0], 0)

    def test_naechster_tag_hat_neues_budget(self):
        with patch('budget.heute', return_value='2026-10-05'):
            budget.reservieren('test', 1800)
        with patch('budget.heute', return_value='2026-10-06'):
            self.assertEqual(budget.rest('test', 1800), 1800)

    def test_kanaele_haben_getrennte_budgets(self):
        budget.reservieren('a', 1800)
        self.assertEqual(budget.rest('b', 1800), 1800)

    def test_defekte_datei_wird_nicht_zurueckgesetzt(self):
        budget.speichern('test', {'datum': budget.heute(), 'sekunden': 'ungueltig'})
        with self.assertRaises(ValueError):
            budget.rest('test', 1800)


class LaufTest(TempTest):
    def test_schwache_skriptzwischenfassung_nach_timeout_wird_nicht_gebaut(self):
        def fake(args, deadline):
            if args[0] == 'fabrik/skript.py':
                with patch.dict(SKRIPT, story={'note': 6, 'kategorien': dict.fromkeys(STORY_KATEGORIEN, 6)}):
                    self.fake_schritt(args, deadline)
                raise subprocess.TimeoutExpired(args, 1)
            return 0
        with patch('lauf.schritt', side_effect=fake) as schritte, patch('lauf.melden'):
            lauf.produzieren('kanaele/test.json', 'test', '', time.monotonic(), 1800, self.themen)
        self.assertFalse(any(c.args[0][0] == 'fabrik/bauen.py' for c in schritte.call_args_list))

    def test_telegramthema_nur_nach_erfolgreicher_zustellung_entfernen(self):
        self.themen.nehmen.return_value = 'LEGO'
        self.ausfuehren([dict(KRITIK, note=10)], sendefehler=True)
        self.themen.erledigen.assert_not_called()
        self.ausfuehren([dict(KRITIK, note=10)])
        self.themen.erledigen.assert_called_once_with('test', 'LEGO')

    def test_gepruefte_skriptzwischenfassung_nach_timeout_wird_gebaut(self):
        self.feedback = [dict(KRITIK, note=10)]
        def fake(args, deadline):
            if args[0] == 'fabrik/skript.py':
                self.fake_schritt(args, deadline)
                raise subprocess.TimeoutExpired(args, 1)
            return self.fake_schritt(args, deadline)
        with patch('lauf.schritt', side_effect=fake) as schritte, patch('lauf.melden'), \
                patch('lauf.VERSUCHE_MAX', 1):
            lauf.produzieren('kanaele/test.json', 'test', '', time.monotonic(), 1800, self.themen)
        self.assertTrue(any(c.args[0][0] == 'fabrik/bauen.py' for c in schritte.call_args_list))
        bericht = json.loads(Path('ausgabe/bericht.json').read_text())
        self.assertEqual(bericht['status'], 'gesendet')
        self.assertTrue(bericht['runden'][0]['skript_zwischenfassung'])

    def test_baufehler_setzt_selbes_geprueftes_skript_mit_cache_fort(self):
        self.feedback = [dict(KRITIK, note=10)]
        baut = []
        def fake(args, deadline):
            if args[0] == 'fabrik/bauen.py':
                baut.append(args)
                if len(baut) == 1:
                    return 1
                Path(args[2], 'short.mp4').write_bytes(b'fertiges-video')
            return self.fake_schritt(args, deadline)
        with patch('lauf.schritt', side_effect=fake) as schritte, patch('lauf.melden'), \
                patch('lauf.VERSUCHE_MAX', 2):
            # Nur 600 Sekunden frei: neuer Entwurf passt nicht, Fortsetzung schon.
            lauf.produzieren('kanaele/test.json', 'test', '', time.monotonic(), 600, self.themen)
        self.assertEqual(sum(c.args[0][0] == 'fabrik/skript.py' for c in schritte.call_args_list), 1)
        self.assertEqual(baut[1][-1], 'versuch1')
        self.assertEqual(json.loads(Path('versuch1/skript.json').read_text()),
                         json.loads(Path('versuch2/skript.json').read_text()))
        self.assertEqual(json.loads(Path('ausgabe/bericht.json').read_text())['status'], 'gesendet')

    def setUp(self):
        super().setUp()
        Path('kanaele').mkdir()
        Path('kanaele/test.json').write_text('{}', encoding='utf-8')
        self.themen = Mock()
        self.themen.nehmen.return_value = ''
        self.feedback = []

    def fake_schritt(self, args, deadline):
        ordner = Path(args[2]).parent if args[0] == 'fabrik/skript.py' else None
        if ordner:
            ordner.mkdir(exist_ok=True)
            (ordner / 'skript.json').write_text(json.dumps(SKRIPT), encoding='utf-8')
            (ordner / 'short.mp4').write_bytes(b'video')
        if args[0] == 'fabrik/kritik.py':
            k = self.feedback.pop(0)
            if k is None:
                return 1
            Path(args[3]).write_text(json.dumps(k), encoding='utf-8')
        if args[0] == 'fabrik/nachbessern.py':
            shutil.copytree(args[1], args[3])
            Path(args[3], 'korrektur.json').write_text(json.dumps({
                'aktionen': [{'art': 'untertitel', 'variante': 'ruhig'}]}), encoding='utf-8')
        return 0

    def ausfuehren(self, feedback, thema='', sendefehler=False):
        self.feedback = feedback[:]
        def fake(args, deadline):
            if sendefehler and args[0] == 'fabrik/freigabe.py':
                return 1
            return self.fake_schritt(args, deadline)
        with patch('lauf.schritt', side_effect=fake) as schritte, patch('lauf.melden'), \
                patch('lauf.VERSUCHE_MAX', len(feedback)), patch('lauf.VERSUCH_S', 0):
            start = time.monotonic()
            try:
                ergebnis = lauf.produzieren('kanaele/test.json', 'test', thema, start, 1800, self.themen)
            except RuntimeError:
                if not sendefehler:
                    raise
                ergebnis = 1
        return ergebnis, [c.args[0] for c in schritte.call_args_list]

    def test_pruefungsausfall_sendet_nichts(self):
        _, calls = self.ausfuehren([None])
        self.assertFalse(any(a[0] == 'fabrik/freigabe.py' for a in calls))
        self.assertEqual(json.loads(Path('verlauf/test.json').read_text())[0]['status'], 'pruefung_fehlt')

    def test_sechs_geht_nur_als_markierter_entwurf(self):
        # Nutzerentscheidung 08.10.2026: fertig gebaut, nur KI-Note 6/10 -> Entwurf zur
        # Nutzerentscheidung (vorher: gar nichts). Ein Freigabe-Versand OHNE Entwurfsmarker
        # darf es dafuer nie geben.
        os.environ.pop('CF_ENTWURF', None)
        _, calls = self.ausfuehren([dict(KRITIK, note=6)])
        self.assertTrue(any(a[0] == 'fabrik/freigabe.py' for a in calls))
        self.assertEqual(os.environ.pop('CF_ENTWURF', None), '1')

    def test_vier_sendet_nichts(self):
        os.environ.pop('CF_ENTWURF', None)
        _, calls = self.ausfuehren([dict(KRITIK, note=4)])
        self.assertFalse(any(a[0] == 'fabrik/freigabe.py' for a in calls))

    def test_schwache_story_verbraucht_keinen_videobau(self):
        with patch.dict(SKRIPT, story={'note': 6, 'kategorien': dict.fromkeys(STORY_KATEGORIEN, 7)}):
            _, calls = self.ausfuehren([KRITIK])
        self.assertFalse(any(a[0] in ('fabrik/bauen.py', 'fabrik/kritik.py', 'fabrik/freigabe.py') for a in calls))

    def test_technikfehler_sendet_nichts(self):
        k = copy.deepcopy(KRITIK)
        k['technik']['befunde'] = ['Ton kaputt']
        _, calls = self.ausfuehren([k])
        self.assertFalse(any(a[0] == 'fabrik/freigabe.py' for a in calls))

    def test_bester_gueltiger_kandidat_bleibt_beim_naechsten_fehler(self):
        ergebnis, calls = self.ausfuehren([KRITIK, None])
        self.assertEqual(ergebnis, 0)
        self.assertEqual(sum(a[0] == 'fabrik/freigabe.py' for a in calls), 1)
        self.assertEqual(json.loads(Path('ausgabe/kritik.json').read_text())['note'], 9)
        self.assertEqual(json.loads(Path('verlauf/test.json').read_text())[0]['status'], 'gesendet')

    def test_festes_thema_bleibt_bei_wiederholung(self):
        _, calls = self.ausfuehren([dict(KRITIK, note=7), KRITIK], 'Mein Thema')
        self.assertEqual([a[3] for a in calls if a[0] == 'fabrik/skript.py'], ['Mein Thema'])
        self.assertEqual(sum(a[0] == 'fabrik/nachbessern.py' for a in calls), 1)
        self.assertEqual(json.loads(Path('ausgabe/skript.json').read_text())['thema'], SKRIPT['thema'])
        self.themen.nehmen.assert_not_called()

    def test_zustellfehler_wird_nicht_als_gesendet_verbucht(self):
        ergebnis, _ = self.ausfuehren([KRITIK], sendefehler=True)
        self.assertEqual(ergebnis, 1)
        self.assertFalse(any(e['status'] == 'gesendet'
                             for e in json.loads(Path('verlauf/test.json').read_text())))

    def test_leeres_budget_nimmt_kein_thema_aus_der_warteschlange(self):
        budget.reservieren('test', lauf.BUDGET_S)
        with patch('themen.nehmen') as nehmen, patch('lauf.schritt') as schritt:
            self.assertEqual(lauf.main('kanaele/test.json'), 0)
        nehmen.assert_not_called()
        schritt.assert_not_called()

    def test_abgelaufene_deadline_startet_keinen_prozess(self):
        with patch('lauf.subprocess.Popen') as popen:
            with self.assertRaises(subprocess.TimeoutExpired):
                lauf.schritt(['fabrik/skript.py'], time.monotonic() - 1)
        popen.assert_not_called()

    def test_gescheiterte_korrektur_behaelt_besseres_video_und_lernt(self):
        self.ausfuehren([KRITIK, dict(KRITIK, note=6)])
        self.assertEqual(json.loads(Path('ausgabe/kritik.json').read_text())['note'], 9)
        daten = json.loads(Path('lernen/test.json').read_text())
        self.assertFalse(daten['korrekturen'][0]['verbessert'])
        self.assertEqual(daten['korrekturen'][0]['vorher'], 9)

    def test_erfolgreiche_korrektur_wird_gespeichert(self):
        self.ausfuehren([dict(KRITIK, note=7), dict(KRITIK, note=10)])
        daten = json.loads(Path('lernen/test.json').read_text())
        self.assertTrue(daten['korrekturen'][0]['verbessert'])
        self.assertEqual(json.loads(Path('ausgabe/kritik.json').read_text())['note'], 10)

    def test_pruefungsausfall_nach_korrektur_bleibt_im_gedaechtnis(self):
        self.ausfuehren([KRITIK, None])
        daten = json.loads(Path('lernen/test.json').read_text())['korrekturen']
        self.assertEqual(len(daten), 1)
        self.assertEqual(daten[0]['vorher'], 9)
        self.assertFalse(daten[0]['auswertbar'])
        self.assertFalse(daten[0]['verbessert'])

    def test_nach_pruefungsausfall_nur_pruefen_und_lernergebnis_nachtragen(self):
        _, calls = self.ausfuehren([KRITIK, None, dict(KRITIK, note=10)])
        self.assertEqual(sum(a[0] == 'fabrik/skript.py' for a in calls), 1)
        self.assertEqual(sum(a[0] == 'fabrik/bauen.py' for a in calls), 2)
        self.assertEqual(sum(a[0] == 'fabrik/nachbessern.py' for a in calls), 1)
        daten = json.loads(Path('lernen/test.json').read_text())['korrekturen']
        self.assertEqual(len(daten), 1)
        self.assertEqual(daten[0]['vorher'], 9)
        self.assertEqual(daten[0]['nachher'], 10)
        self.assertTrue(daten[0]['verbessert'])

    def test_pilot_sendet_keine_telegram_vorschau(self):
        with patch.dict(os.environ, {'CF_PILOT': '1'}):
            _, calls = self.ausfuehren([dict(KRITIK, note=10)])
        self.assertFalse(any(a[0] == 'fabrik/freigabe.py' for a in calls))
        self.assertEqual(json.loads(Path('ausgabe/bericht.json').read_text())['status'], 'pilot_bestanden')

    def test_gesperrtes_pilotvideo_meldet_fehlgeschlagene_qualitaetspruefung(self):
        with patch.dict(os.environ, {'CF_PILOT': '1'}):
            ergebnis, calls = self.ausfuehren([dict(KRITIK, note=6)])
        self.assertEqual(ergebnis, 2)
        self.assertFalse(any(a[0] == 'fabrik/freigabe.py' for a in calls))
        self.assertEqual(json.loads(Path('ausgabe/bericht.json').read_text())['status'], 'gesperrt')

    def test_pilot_bleibt_bei_verbrauchtem_produktionsbudget_ausfuehrbar(self):
        budget.reservieren('test', lauf.BUDGET_S)
        with patch.dict(os.environ, {'CF_PILOT': '1'}), \
                patch('lauf.produzieren', return_value=0) as bauen:
            self.assertEqual(lauf.main('kanaele/test.json'), 0)
        bauen.assert_called_once()
        self.assertEqual(budget.rest('test', lauf.BUDGET_S), 0)

    def test_budget_wird_auch_beim_normalen_fehler_abgerechnet(self):
        with patch('lauf.produzieren', side_effect=RuntimeError('Arbeiterfehler')), \
                patch('lauf.time.monotonic', side_effect=[100, 220]):
            with self.assertRaises(RuntimeError):
                lauf.main('kanaele/test.json')
        self.assertEqual(budget.rest('test', 1800), 1680)


class WorkflowTest(TempTest):
    def test_tagesziel_eins_oder_zwei_auch_bei_manuellem_start(self):
        Path('verlauf').mkdir()
        Path('verlauf/test.json').write_text(json.dumps([
            {'datum': budget.heute(), 'status': 'gesendet'}]), encoding='utf-8')
        self.assertEqual(self.vorpruefung('workflow_dispatch', 'test'), [])
        Path('kanaele/test.json').write_text('{"tagesziel": 2}')
        self.assertEqual(self.vorpruefung('workflow_dispatch', 'alle'), ['test'])

    def setUp(self):
        super().setUp()
        workflow = Path(__file__).resolve().parents[1] / '.github/workflows/video.yml'
        text = workflow.read_text(encoding='utf-8')
        self.code = textwrap.dedent(text.split("python3 - <<'EOF'\n", 1)[1].split('\n          EOF', 1)[0])
        Path('kanaele').mkdir()
        Path('kanaele/test.json').write_text('{}', encoding='utf-8')

    def vorpruefung(self, ereignis='schedule', eingabe=''):
        env = {'EREIGNIS': ereignis, 'EINGABE': eingabe, 'GITHUB_OUTPUT': 'outputs.txt'}
        with patch.dict(os.environ, env):
            exec(compile(self.code, 'video.yml:vorpruefung', 'exec'), {})
        return json.loads(Path('outputs.txt').read_text().split('kanaele=')[-1])

    def test_neuer_kanal_wird_automatisch_erkannt(self):
        self.assertEqual(self.vorpruefung(), ['test'])

    def test_gesendeter_kanal_wird_uebersprungen(self):
        Path('verlauf').mkdir()
        Path('verlauf/test.json').write_text(json.dumps([
            {'datum': budget.heute(), 'status': 'gesendet'}]), encoding='utf-8')
        self.assertEqual(self.vorpruefung(), [])

    def test_ersatzlauf_mit_leerem_budget_wird_uebersprungen(self):
        budget.reservieren('test', lauf.BUDGET_S)
        self.assertEqual(self.vorpruefung('workflow_dispatch', 'alle'), [])

    def test_kleiner_rest_ohne_gueltigen_entwurf_startet_keinen_neubau(self):
        with patch('budget.rest', return_value=393):
            self.assertEqual(self.vorpruefung('workflow_dispatch', 'alle'), [])
            self.assertEqual(self.vorpruefung('workflow_dispatch', 'test'), [])

    def test_kleiner_rest_darf_gueltigen_entwurf_fortsetzen(self):
        import entwurf_cache
        Path('bau').mkdir()
        Path('bau/skript.json').write_text(json.dumps(SKRIPT))
        entwurf_cache.sichern('test', 'kanaele/test.json', '', 'bau')
        with patch('budget.rest', return_value=393):
            self.assertEqual(self.vorpruefung('workflow_dispatch', 'alle'), ['test'])
        with patch('budget.rest', return_value=180):
            self.assertEqual(self.vorpruefung('workflow_dispatch', 'alle'), [])

    def test_unbekannte_kanaleingabe_wird_abgelehnt(self):
        with self.assertRaises(SystemExit):
            self.vorpruefung('workflow_dispatch', '../../anderer-pfad')


class TelegramTest(TempTest):
    def zustellen(self, videoformat='short', original=''):
        skript = dict(SKRIPT, videoformat=videoformat)
        Path('skript.json').write_text(json.dumps(skript), encoding='utf-8')
        Path('kritik.json').write_text(json.dumps(dict(KRITIK,
            audio_pruefung=audio_fixture(TEST_SHA, videoformat))), encoding='utf-8')
        Path('video.mp4').write_bytes(b'gepruefter-testfilm')
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': 'test', 'CF_ORIGINAL_URL': original}), \
                patch('freigabe.telegram', return_value={'ok': True}) as tg:
            freigabe.senden('skript.json', 'video.mp4')
        return [c.args[1].get('text', '') for c in tg.call_args_list]

    def test_short_enthaelt_skript_und_beide_uploadtexte(self):
        texte = self.zustellen()
        self.assertTrue(any('How did this happen?' in t and 'Skript' in t for t in texte))
        self.assertTrue(any('#shorts' in t and 'YouTube-Titel' in t for t in texte))
        self.assertTrue(any('TikTok' in t for t in texte))

    def test_langvideo_hat_eigene_uploadtexte_und_originalverweis(self):
        original = 'https://github.com/aKhaaaaaan/contentfabrik/actions/runs/123'
        texte = self.zustellen('lang', original)
        self.assertTrue(any(original in t for t in texte))
        self.assertTrue(any('YouTube-Titel' in t for t in texte))
        self.assertFalse(any('#shorts' in t or 'TikTok' in t for t in texte))
        self.assertTrue(any('How did this happen?' in t and 'Skript' in t for t in texte))

    def test_direkter_aufruf_umgeht_pruefung_nicht(self):
        Path('skript.json').write_text(json.dumps(SKRIPT), encoding='utf-8')
        with patch('freigabe.telegram') as tg:
            with self.assertRaises(ValueError):
                freigabe.senden('skript.json', 'existiert-nicht.mp4')
        tg.assert_not_called()

    def test_lange_texte_und_lizenzen_bleiben_vollstaendig(self):
        text = ('🚀 <Tool> & Beschreibung\n' * 500) + 'Photos: Urheber CC BY-SA (Quelle)'
        teile = list(freigabe.kopiertexte(text))
        self.assertGreater(len(teile), 1)
        self.assertEqual(''.join(html.unescape(t[6:-7]) for t in teile), text)
        self.assertTrue(all(len(t.encode('utf-16-le')) // 2 < 4096 for t in teile))

    def test_telegram_ok_false_ist_fehler(self):
        antwort = Mock()
        antwort.__enter__ = Mock(return_value=antwort)
        antwort.__exit__ = Mock(return_value=False)
        antwort.read.return_value = b'{"ok": false}'
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': 'test'}), \
                patch('freigabe.urllib.request.urlopen', return_value=antwort):
            with self.assertRaises(RuntimeError):
                freigabe.telegram('sendMessage', {'text': 'test'})


class TechnikTest(TempTest):
    def test_technikfehler_verbraucht_keine_ki_anfrage(self):
        Path('skript.json').write_text(json.dumps(SKRIPT), encoding='utf-8')
        with patch('kritik.technik', return_value={'befunde': ['keine Tonspur']}), \
                patch('kritik.hochladen') as upload, patch('kritik.gemini') as ki:
            kritik.kritik('video.mp4', 'skript.json', 'kritik.json')
        upload.assert_not_called()
        ki.assert_not_called()
        self.assertTrue(bewerten(SKRIPT, json.loads(Path('kritik.json').read_text()))[1])

    def test_normaler_ffprobe_bruch_und_lautheit(self):
        info = {'streams': [{'codec_type': 'video', 'width': 1080, 'height': 1920,
                            'codec_name': 'h264', 'avg_frame_rate': '30000/1001'},
                           {'codec_type': 'audio', 'codec_name': 'aac', 'sample_rate': '48000', 'channels': 2}],
                'format': {'duration': '70'}}
        antworten = [subprocess.CompletedProcess([], 0, json.dumps(info), ''),
                     subprocess.CompletedProcess([], 0, '', 'I: -14.0 LUFS')]
        with patch('subprocess.run', side_effect=antworten):
            t = kritik.technik('video.mp4')
        self.assertEqual(t['befunde'], [])
        self.assertAlmostEqual(t['fps'], 30, places=1)


if __name__ == '__main__':
    unittest.main()
