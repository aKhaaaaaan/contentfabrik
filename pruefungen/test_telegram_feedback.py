import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from test_betrieb import TempTest
import lernen
import themen


class TelegramFeedbackTest(TempTest):
    def test_bildkritik_wird_gelernt_statt_als_thema_eingereiht(self):
        text = 'Es wurden einfach viel zu wenig Fotos verwendet'
        update = {'update_id': 123, 'message': {'chat': {'id': 456}, 'text': text}}
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': '456'}), \
                patch('themen._tg', side_effect=[{'result': [update]}, {'ok': True}, {'ok': True}]), \
                patch('themen.zuordnen') as zuordnen:
            themen.abholen()
        zuordnen.assert_not_called()
        self.assertEqual(themen.laden(), [])
        self.assertIn(text, ' '.join(lernen.redaktionsregeln()))
        lernen.nutzerfeedback(text, 'telegram-123')
        self.assertEqual(len(lernen.laden('telegram-feedback')['rueckmeldungen']), 1)

    def test_echtes_thema_und_fremder_chat_werden_nicht_als_feedback_gespeichert(self):
        self.assertFalse(themen.ist_feedback('Business: Wie Nintendo entstand'))
        self.assertTrue(themen.ist_feedback('Feedback: Bitte mehr passende Bilder'))
        update = {'update_id': 3, 'message': {'chat': {'id': 999}, 'text': 'Video langweilig'}}
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': '456'}), \
                patch('themen._tg', side_effect=[{'result': [update]}, {'ok': True}]):
            themen.abholen()
        self.assertFalse(Path('lernen/telegram-feedback.json').exists())
