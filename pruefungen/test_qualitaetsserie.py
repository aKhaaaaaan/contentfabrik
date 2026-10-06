"""Messprotokoll pruefen, ohne Videos, Nachrichten oder Nutzerurteile zu erzeugen."""
import copy
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

from test_betrieb import TempTest, SKRIPT, KRITIK
import qualitaetsserie as qs


class QualitaetsserieTest(TempTest):
    def setUp(self):
        super().setUp()
        self.serie = {'aktiv': True, 'kanaele': ['test'], 'laeufe': [],
                      'erste_videos_je_kanal': 3, 'bestaetigungen_in_folge': 10}
        qs.speichern(self.serie)
        self.env = patch.dict(os.environ, {'GITHUB_RUN_ID': '123',
            'GITHUB_EVENT_NAME': 'workflow_dispatch', 'CF_PILOT': '0'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.sha = hashlib.sha256(b'fake video for unit test').hexdigest()

    def material(self):
        Path('ausgabe').mkdir()
        (Path('ausgabe') / 'short.mp4').write_bytes(b'fake video for unit test')
        for datei, daten in [('skript.json', SKRIPT),
                             ('kritik.json', dict(KRITIK, video_sha256=self.sha)),
                             ('bericht.json', {'status': 'gesendet'}),
                             ('bildablauf.json', {'einstellungen': [
                                 {'material_id': 'a'}, {'material_id': 'a'}, {'material_id': 'b'}]})]:
            qs.speichern(daten, Path('ausgabe') / datei)

    def urteil(self):
        return {'video_sha256': self.sha, 'pruefer': 'Unit-Test', 'note': None,
                'vollstaendig_angesehen': True, 'ohne_nachbearbeitung': True,
                'veroeffentlichbar': True, 'pruefpunkte': dict.fromkeys(qs.PRUEFPUNKTE, True)}

    def status(self):
        return qs.zusammenfassung(qs.lesen(qs.DATEI))['kanaele']['test']

    def test_ki_note_ist_keine_menschliche_freigabe_und_zooms_keine_motive(self):
        self.material()
        e = qs.erfassen('test')
        self.assertEqual(e['unterschiedliche_motive'], 2)
        self.assertEqual(e['ki_video_note'], 9)
        self.assertIsNone(e['sichtpruefung'])
        self.assertEqual(self.status()['freigegeben_in_folge'], 0)

    def test_abbruch_vor_video_wird_nicht_als_erfolg_gezaehlt(self):
        e = qs.erfassen('test')
        self.assertFalse(e['video_gebaut'])
        self.assertEqual(e['status'], 'kein_produktionsbericht')
        self.assertTrue(e['sperrgruende'])
        self.assertFalse(self.status()['initiale_drei_videos_gebaut'])

    def test_sichtpruefung_wird_bei_wiederholung_erhalten(self):
        self.material()
        e = qs.erfassen('test')
        qs.bewertung_eintragen(e['id'], self.urteil())
        qs.erfassen('test')
        self.assertEqual(len(qs.lesen(qs.DATEI)['laeufe']), 1)
        self.assertEqual(self.status()['freigegeben_in_folge'], 1)

    def test_falscher_hash_und_unvollstaendige_bewertung_abgelehnt(self):
        self.material()
        e = qs.erfassen('test')
        for urteil in (dict(self.urteil(), video_sha256='falsch'),
                       dict(self.urteil(), pruefpunkte={'hook': True}),
                       dict(self.urteil(), vollstaendig_angesehen='ja'),
                       dict(self.urteil(), note=10.5)):
            with self.assertRaises(ValueError):
                qs.bewertung_eintragen(e['id'], urteil)

    def test_sperre_bleibt_trotz_positivem_menschlichem_urteil(self):
        self.material()
        k = dict(KRITIK, video_sha256='andere datei')
        qs.speichern(k, Path('ausgabe/kritik.json'))
        e = qs.erfassen('test')
        qs.bewertung_eintragen(e['id'], self.urteil())
        self.assertEqual(self.status()['freigegeben_in_folge'], 0)

    def test_piloten_werden_nicht_als_normaler_tageslauf_erfasst(self):
        with patch.dict(os.environ, {'CF_PILOT': '1'}), self.assertRaises(ValueError):
            qs.erfassen('test')

    def test_neue_datei_unter_gleicher_lauf_id_nicht_mit_altem_urteil(self):
        self.material()
        qs.erfassen('test')
        Path('ausgabe/short.mp4').write_bytes(b'new')
        with self.assertRaises(ValueError):
            qs.erfassen('test')

    def serie_mit_zehn(self):
        self.material()
        e = qs.erfassen('test')
        s = qs.lesen(qs.DATEI)
        s['laeufe'] = []
        for i in range(10):
            neu = copy.deepcopy(e)
            neu.update(id=str(i), datum_utc=f'2026-10-{i+6:02d}', video_sha256=str(i),
                       sichtpruefung=dict(self.urteil(), video_sha256=str(i)))
            s['laeufe'].append(neu)
        return s

    def test_zehn_bestaetigungen_schalten_keinen_upload_frei(self):
        s = self.serie_mit_zehn()
        z = qs.zusammenfassung(s)
        self.assertTrue(z['kanaele']['test']['kontrollpunkt_zehn_erreicht'])
        self.assertFalse(z['automatischer_plattform_upload'])

    def test_fehler_ablehnung_oder_fehlende_sichtpruefung_unterbricht_folge(self):
        s = self.serie_mit_zehn()
        for aenderung in ({'sichtpruefung': None}, {'sperrgruende': ['Fehler']},
                          {'status': 'gesperrt'}, {'produktionsversion': 'neuer code'},
                          {'sichtpruefung': dict(self.urteil(), video_sha256='9',
                                                ohne_nachbearbeitung=False)}):
            mit_fehler = copy.deepcopy(s)
            mit_fehler['laeufe'][-1].update(aenderung)
            self.assertFalse(qs.zusammenfassung(mit_fehler)['kanaele']['test']['kontrollpunkt_zehn_erreicht'])

    def test_dasselbe_video_zaehlt_nicht_mehrfach(self):
        s = self.serie_mit_zehn()
        for e in s['laeufe']:
            e['video_sha256'] = self.sha
            e['sichtpruefung']['video_sha256'] = self.sha
        z = qs.zusammenfassung(s)['kanaele']['test']
        self.assertFalse(z['kontrollpunkt_zehn_erreicht'])
        self.assertFalse(z['initiale_drei_videos_gebaut'])
