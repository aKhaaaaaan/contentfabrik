"""Skript-Vorrat (Nutzerwunsch 07.10.2026): vorher schreiben, gepruft warten, nur dann bauen."""
import datetime
import json
import subprocess
from pathlib import Path
from unittest.mock import patch
from test_betrieb import TempTest
import vorrat

# Feste Laenge: diese Tests pruefen Vorrat-Regeln, nicht die Shorts-Laenge (seit 10.10. 35-45 s).
KANAL = {'name': 'Business Origin Stories', 'format': 'geschichte', 'laenge_s': [62, 90]}


def skript(thema='WeWork', ok=True):
    return {'thema': thema, 'titel': ['A', 'B'], 'teile': [{'text': 'One.'}],
            'pruefung': {'ok': ok, 'probleme': []}, 'story': {'note': 8}, 'modell': 'claude:sonnet'}


class VorratTest(TempTest):
    def setUp(self):
        super().setUp()
        Path('kanaele').mkdir()
        Path('kanaele/business-origin-stories.json').write_text(json.dumps(KANAL), encoding='utf-8')
        self.pfad = 'kanaele/business-origin-stories.json'
        self.ok = patch('qualitaet.skript_gruende', return_value=[])
        self.ok.start()

    def tearDown(self):
        self.ok.stop()
        super().tearDown()

    def ablegen(self, thema_eingabe, tage=0, ok=True, name='a'):
        Path('vorrat/business-origin-stories').mkdir(parents=True, exist_ok=True)
        erstellt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=tage)
        Path(f'vorrat/business-origin-stories/{name}.json').write_text(json.dumps(
            {'thema_eingabe': thema_eingabe, 'erstellt_utc': erstellt.isoformat(),
             'skript': skript(thema_eingabe or 'Frei', ok)}), encoding='utf-8')

    def test_passendes_thema_wird_genommen(self):
        self.ablegen('WeWork')
        ordner = vorrat.nehmen(self.pfad, 'WeWork')
        self.assertEqual(json.loads((ordner / 'skript.json').read_text())['thema'], 'WeWork')

    def test_spaeter_geplantes_nutzerthema_nicht_ohne_thema_bauen(self):
        self.ablegen('Netflix')
        self.assertIsNone(vorrat.nehmen(self.pfad, ''))
        self.assertIsNone(vorrat.nehmen(self.pfad, 'WeWork'))

    def test_abgelaufen_oder_ungeprueft_nie(self):
        self.ablegen('WeWork', tage=15)
        self.assertIsNone(vorrat.nehmen(self.pfad, 'WeWork'))
        self.ablegen('WeWork', ok=False, name='b')
        self.assertIsNone(vorrat.nehmen(self.pfad, 'WeWork'))

    def test_zu_langes_skript_fuer_die_stimme_ungueltig(self):
        # Lauf 37749486997: 207 Woerter fuer Orus (2 W/s) -> 109 s. Vorher galt es als gueltig.
        self.ablegen('WeWork')
        p = Path('vorrat/business-origin-stories/a.json')
        e = json.loads(p.read_text())
        e['skript']['teile'] = [{'text': ' '.join(['word'] * 200)}]
        p.write_text(json.dumps(e))
        Path(self.pfad).write_text(json.dumps(dict(KANAL, woerter_pro_sekunde=2.0)), encoding='utf-8')
        self.assertIsNone(vorrat.nehmen(self.pfad, 'WeWork'))
        Path(self.pfad).write_text(json.dumps(dict(KANAL, woerter_pro_sekunde=2.4)), encoding='utf-8')
        self.assertIsNotNone(vorrat.nehmen(self.pfad, 'WeWork'))

    def test_erledigen_entfernt_nur_das_gesendete(self):
        self.ablegen('WeWork', name='a')
        self.ablegen('Netflix', name='b')
        vorrat.erledigen('business-origin-stories', skript('WeWork'))
        self.assertEqual([e['thema_eingabe'] for _, e in vorrat.eintraege('business-origin-stories')], ['Netflix'])

    def test_fuellen_nimmt_nur_bestandene_skripte_auf(self):
        def lauf(args, timeout):
            thema = args[-1]
            Path(args[-2]).write_text(json.dumps(skript(thema, ok=thema != 'Enron')), encoding='utf-8')
            return subprocess.CompletedProcess(args, 0 if thema != 'Yahoo' else 2)
        with patch('vorrat.offene_themen', return_value=['Yahoo', 'Enron', 'WeWork', 'Netflix']), \
                patch('vorrat.subprocess.run', side_effect=lauf) as run:
            neu = vorrat.fuellen(self.pfad, frist_s=3600)
        self.assertEqual(neu, 2)
        self.assertEqual(sorted(e['thema_eingabe'] for _, e in vorrat.eintraege('business-origin-stories')),
                         ['Netflix', 'WeWork'])
        self.assertEqual(run.call_count, 4)

    def test_videolauf_nutzt_vorrat(self):
        # Vor dem Bau schrieb der Videolauf IMMER selbst (Skriptphase bis 1620 s).
        quelle = (Path(__file__).resolve().parents[1] / 'fabrik/lauf.py').read_text(encoding='utf-8')
        self.assertIn('vorrat.nehmen(kanal_pfad, festes_thema)', quelle)
        self.assertIn('vorrat.erledigen(kanal, skript)', quelle)
