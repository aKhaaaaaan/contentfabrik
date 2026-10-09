"""Nutzernote -> konkrete Lehre (09.10.2026).

Alter Stand, den diese Tests erkennen: Ein Knopfdruck „6/10" landete nur als nackter Satz im
Regelbuch; was an dem Video schlecht war, erfuhr der Autor nie. Dass die KI das Video viel
besser bewertet hatte als der Nutzer (Nintendo: KI 9, Nutzer < 5), wurde nicht festgehalten.
"""
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
from test_betrieb import TempTest
import bewertung

KRITIK = {'note': 8, 'probleme': [{'art': 'bild_passt_nicht', 'text': 'Sparschwein statt Funktion'},
                                  {'art': 'standbild', 'text': 'Zu lange dasselbe Bild'}]}
SKRIPT = {'kanal': 'AI Tools Explained', 'thema': 'Aurelio', 'titel': ['Your Money', 'Aurelio']}


class Nutzernote(TempTest):
    def druecken(self, wert, kritik=KRITIK):
        bewertung.video_merken(77, 'abcdef0123456789' + '0' * 48, SKRIPT, kritik)
        with patch('lernen.aktualisieren') as lernt:
            antwort = bewertung.knopf(1, {'data': f'bw:abcdef0123456789:{wert}', 'message': {'message_id': 77}})
        return antwort, lernt

    def test_schwache_note_macht_die_befunde_zur_lehre(self):
        _, lernt = self.druecken('5')
        kanal, kritik = lernt.call_args.args
        self.assertEqual(kanal, 'ai-tools-explained')
        texte = ' '.join(p['text'] for p in kritik['probleme'])
        self.assertIn('rated this video 5/10', texte)
        self.assertIn('Sparschwein statt Funktion', texte)

    def test_zu_milde_ki_wird_festgehalten(self):
        self.druecken('5')
        d = bewertung._lesen(bewertung.REDAKTION, {})
        self.assertIn('die KI war zu mild', d['nutzerfeedback'][-1]['wortlaut'])

    def test_gute_note_ohne_regel_aenderung(self):
        _, lernt = self.druecken('9')
        lernt.assert_not_called()

    def test_ablehnung_lernt_auch(self):
        _, lernt = self.druecken('nein')
        self.assertIn('rated this video abgelehnt', lernt.call_args.args[1]['probleme'][0]['text'])

    def test_alte_videos_ohne_befunde_bleiben_ruhig(self):
        _, lernt = self.druecken('5', kritik=None)
        lernt.assert_not_called()
