"""Bilddichte und Nutzerablehnung duerfen nicht durch hohe KI-Noten verschwinden."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
from test_betrieb import TempTest, SKRIPT, KRITIK
import bildplan
import lernen
import freigabe
from qualitaet import video_bewerten


class BildplanTest(TempTest):
    def plan(self, n=4, dauer=16):
        return {'einstellungen': [{'s': i * dauer/n, 'dauer_s': dauer/n,
                'material_id': str(i), 'material_art': 'foto'} for i in range(n)]}

    def test_mehrere_einstellungen_pro_phase_ohne_sprechtextaenderung(self):
        s = copy.deepcopy(SKRIPT)
        s['teile'] = [{'text': 'One two three four.'}]
        slots = bildplan.slots(s, [15], [{'w': str(i), 's': i, 'e': i+.5} for i in range(15)])
        self.assertEqual(len(slots), 4)
        self.assertEqual({x['phase'] for x in slots}, {0})
        self.assertAlmostEqual(sum(x['dauer_s'] for x in slots), 15)
        self.assertEqual(s['teile'][0]['text'], 'One two three four.')

    def test_korrekte_bildfolge_besteht(self):
        self.assertEqual(bildplan.pruefen(self.plan(), 16)['befunde'], [])

    def test_zooms_auf_dieselbe_datei_zaehlen_nicht_als_neue_motive(self):
        p = self.plan()
        for s in p['einstellungen']:
            s['material_id'] = 'same photo'
        self.assertTrue(bildplan.pruefen(p, 16)['befunde'])

    def test_hintergrund_und_zu_lange_einstellung_sperren(self):
        p = self.plan(1)
        p['einstellungen'][0]['material_art'] = 'hintergrund'
        gr = bildplan.pruefen(p, 16)['befunde']
        self.assertIn('Sprechabschnitt ohne passendes Hauptbild', gr)
        self.assertIn('Einstellung zu lang ohne neues Motiv', gr)

    def test_bildluecke_und_fehlendes_ende_sperren(self):
        p = self.plan()
        p['einstellungen'][1]['s'] += 1
        self.assertTrue(bildplan.pruefen(p, 17)['befunde'])

    def test_gemini_plan_muss_jeden_slot_genau_einmal_abdecken(self):
        with patch('skript.gemini', return_value=({'einstellungen': []}, 'test')), self.assertRaises(ValueError):
            bildplan.vorbereiten(SKRIPT, [15], [])

    def test_globales_nutzerfeedback_erreicht_beide_kanaele(self):
        Path('lernen').mkdir()
        Path('lernen/redaktion.json').write_text(json.dumps({'regeln': ['Multiple shots per phase']}))
        self.assertIn('Multiple shots per phase', lernen.regeln('business-origin-stories'))
        self.assertIn('Multiple shots per phase', lernen.regeln('ai-tools-explained'))

    def test_ausdruecklich_abgelehnte_datei_wird_trotz_ki_neun_nicht_gesendet(self):
        Path('lernen').mkdir()
        Path('video.mp4').write_bytes(b'rejected actual video')
        h = bildplan.material_id('video.mp4')
        Path('lernen/redaktion.json').write_text(json.dumps({'nutzerfeedback': [
            {'video_sha256': h, 'status': 'abgelehnt'}]}))
        self.assertTrue(video_bewerten(dict(KRITIK, video_sha256=h))[1])
        Path('skript.json').write_text(json.dumps(SKRIPT))
        Path('kritik.json').write_text(json.dumps(KRITIK))
        with patch('freigabe.telegram') as tg, self.assertRaises(ValueError):
            freigabe.senden('skript.json', 'video.mp4')
        tg.assert_not_called()
