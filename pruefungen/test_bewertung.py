"""Bewertungsknoepfe unter gelieferten Videos (Nutzerwunsch 07.10.2026)."""
import json
import os
from pathlib import Path
from unittest.mock import patch
from test_betrieb import TempTest
import bewertung
import lernen
import themen

SHA = 'ab' * 32
SKRIPT = {'kanal': 'business-origin-stories', 'thema': 'WeWork', 'titel': ["WeWork's $47B Rise", 'And Its *Fall*']}


def knopfdruck(update_id, wert, chat=456, message_id=77):
    return {'update_id': update_id, 'callback_query': {
        'id': f'cb{update_id}', 'data': f'bw:{SHA[:16]}:{wert}',
        'message': {'message_id': message_id, 'chat': {'id': chat}}}}


class BewertungTest(TempTest):
    def abholen(self, *updates):
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': '456'}), \
                patch('themen._tg', return_value={'ok': True, 'result': list(updates)}) as tg:
            themen.abholen()
        return tg

    def test_knoepfe_passen_in_telegram_grenze(self):
        for reihe in bewertung.knoepfe(SHA)['inline_keyboard']:
            for k in reihe:
                self.assertLessEqual(len(k['callback_data'].encode()), 64)

    def test_ablehnen_sperrt_genau_diese_datei(self):
        # Vor dem Bau: Knopfdruecke wurden gar nicht abgeholt, nichts gesperrt.
        bewertung.video_merken(77, SHA, SKRIPT)
        tg = self.abholen(knopfdruck(1, 'nein'))
        self.assertTrue(lernen.abgelehnt(SHA))
        self.assertFalse(lernen.abgelehnt('cd' * 32))
        zustand = themen.telegram_laden()
        self.assertIn('Abgelehnt', zustand['bestaetigungen'][0]['text'])
        self.assertIn('WeWork', zustand['bestaetigungen'][0]['text'])
        self.assertIn('answerCallbackQuery', [c.args[0] for c in tg.call_args_list])
        self.assertIn('callback_query', tg.call_args_list[0].kwargs['allowed_updates'])

    def test_ablehnen_ohne_zuordnung_sperrt_ueber_praefix(self):
        self.abholen(knopfdruck(2, 'nein', message_id=999))
        self.assertTrue(lernen.abgelehnt(SHA))

    def test_note_wird_gespeichert_und_gelernt(self):
        bewertung.video_merken(77, SHA, SKRIPT)
        self.abholen(knopfdruck(3, '9'))
        d = json.loads(Path('lernen/redaktion.json').read_text(encoding='utf-8'))
        e = d['nutzerfeedback'][-1]
        self.assertEqual((e['note'], e['status'], e['video_sha256']), (9, 'benotet', SHA))
        self.assertFalse(lernen.abgelehnt(SHA))
        self.assertIn('Note 9/10', ' '.join(lernen.redaktionsregeln()))

    def test_doppelter_druck_nur_einmal(self):
        self.abholen(knopfdruck(4, 'ok'))
        self.abholen(knopfdruck(4, 'ok'))
        d = json.loads(Path('lernen/redaktion.json').read_text(encoding='utf-8'))
        self.assertEqual(sum(e['id'] == 'telegram-knopf-4' for e in d['nutzerfeedback']), 1)

    def test_fremder_chat_wird_ignoriert(self):
        self.abholen(knopfdruck(5, 'nein', chat=999))
        self.assertFalse(lernen.abgelehnt(SHA))

    def test_antwort_auf_video_ist_feedback_kein_thema(self):
        bewertung.video_merken(77, SHA, SKRIPT)
        update = {'update_id': 6, 'message': {'chat': {'id': 456}, 'text': 'Musik zu laut',
                                              'reply_to_message': {'message_id': 77}}}
        with patch('themen.zuordnen') as zuordnen:
            self.abholen(update)
        zuordnen.assert_not_called()
        self.assertEqual(themen.laden(), [])
        self.assertIn('Musik zu laut', ' '.join(lernen.redaktionsregeln()))
