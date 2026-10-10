"""Zwei Bewertungsleisten (Story / Video) und Kommentar mit Lernwirkung (Nutzerwunsch 10.10.2026).

Alter Stand, den diese Tests erkennen: nur EINE Notenleiste - Story und Video waren nicht getrennt
bewertbar; ein Kommentar landete nur als Text in der Feedback-Liste, nicht als Kanal-Regel.
"""
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
from test_betrieb import TempTest
import bewertung

SHA = 'abcdef0123456789' + '0' * 48
SKRIPT = {'kanal': 'Business Origin Stories', 'thema': 'Netflix', 'titel': ['From DVDs', 'to Streaming'],
          'story': {'note': 8, 'schwaechen': ['Timeline instead of conflict in the middle']}}
KRITIK = {'note': 8, 'probleme': [{'art': 'bild_passt_nicht', 'text': 'Motive passen nicht zum Gesagten'}]}


class Leisten(TempTest):
    def test_zwei_notenleisten_plus_ok_ablehnen(self):
        reihen = bewertung.knoepfe(SHA)['inline_keyboard']
        daten = [[k['callback_data'].split(':')[0] for k in r] for r in reihen]
        self.assertEqual(set(daten[0]), {'bs'})
        self.assertEqual(set(daten[1]), {'bv'})
        self.assertEqual(len(reihen[0]), 7)
        self.assertTrue(all(len(k['callback_data'].encode()) <= 64 for r in reihen for k in r))

    def druecken(self, daten, update=1):
        bewertung.video_merken(77, SHA, SKRIPT, KRITIK)
        with patch('lernen.aktualisieren') as lernt:
            antwort = bewertung.knopf(update, {'data': daten, 'message': {'message_id': 77}})
        return antwort, lernt

    def test_story_note_lernt_aus_den_story_schwaechen(self):
        antwort, lernt = self.druecken('bs:abcdef0123456789:5')
        self.assertIn('Story 5/10', antwort)
        texte = ' '.join(p['text'] for p in lernt.call_args.args[1]['probleme'])
        self.assertIn('Timeline instead of conflict', texte)
        self.assertNotIn('Motive passen nicht', texte)

    def test_video_note_lernt_aus_den_video_befunden(self):
        antwort, lernt = self.druecken('bv:abcdef0123456789:6')
        self.assertIn('Video 6/10', antwort)
        texte = ' '.join(p['text'] for p in lernt.call_args.args[1]['probleme'])
        self.assertIn('Motive passen nicht', texte)

    def test_unsinnige_knoepfe_werden_abgelehnt(self):
        antwort, _ = self.druecken('bs:abcdef0123456789:ok')
        self.assertIn('Unbekannter Knopf', antwort)

    def test_kommentar_wird_kanal_regel(self):
        bewertung.video_merken(77, SHA, SKRIPT, KRITIK)
        with patch('lernen.aktualisieren') as lernt:
            bewertung.antwort_auf_video(5, {'reply_to_message': {'message_id': 77},
                                            'text': 'Die Motive passen nicht zu den Woertern'})
        kanal, kritik = lernt.call_args.args
        self.assertEqual(kanal, 'business-origin-stories')
        self.assertIn('Die Motive passen nicht', kritik['probleme'][0]['text'])
