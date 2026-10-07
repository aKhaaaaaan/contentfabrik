"""Eigene Skripte und Video-Links per Telegram (Nutzerwunsch 07.10.2026).
Live geprueft 07.10.: oEmbed YouTube (watch + shorts) und TikTok liefern Titel/Kanal."""
import os
from unittest.mock import patch
from test_betrieb import TempTest
import prompts
import themen

TEXT = ' '.join(['WeWork wollte Bueros wie Software verkaufen.'] * 10)


class TelegramEingangTest(TempTest):
    def abholen(self, text, update_id=10):
        update = {'update_id': update_id, 'message': {'chat': {'id': 456}, 'text': text}}
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': '456'}), \
                patch('themen._tg', return_value={'ok': True, 'result': [update]}):
            themen.abholen()
        return themen.laden(), themen.telegram_laden()['bestaetigungen']

    def test_eigenes_skript_landet_mit_text_in_warteschlange(self):
        # Vor dem Bau: 'Skript Business:' wurde als 2. Thema-Zeile/Ideenliste missverstanden.
        liste, antwort = self.abholen('Skript Business: Wie WeWork scheiterte\n' + TEXT)
        self.assertEqual(len(liste), 1)
        self.assertEqual((liste[0]['kanal'], liste[0]['thema']), ('business-origin-stories', 'Wie WeWork scheiterte'))
        self.assertEqual(liste[0]['nutzerskript'], TEXT)
        self.assertIn('Skript', antwort[0]['text'])

    def test_zu_kurzes_skript_wird_erklaert(self):
        liste, antwort = self.abholen('Skript Business: WeWork\nzu kurz')
        self.assertEqual(liste, [])
        self.assertIn('40-900', antwort[0]['text'])

    def test_link_wird_thema_ohne_fremden_text(self):
        with patch('themen.link_titel', return_value=('How WeWork lost 47 billion', 'SomeCreator')), \
                patch('themen.zuordnen') as zuordnen:
            liste, antwort = self.abholen('Business: https://www.youtube.com/shorts/aqz-KE-bpKQ')
        zuordnen.assert_not_called()
        self.assertEqual(liste[0]['thema'], 'How WeWork lost 47 billion')
        self.assertIn('do not copy', liste[0]['rechercheauftrag'])
        self.assertNotIn('nutzerskript', liste[0])
        self.assertIn('neu mit eigenen Quellen', antwort[0]['text'])

    def test_instagram_ehrlich_ablehnen(self):
        liste, antwort = self.abholen('KI: https://www.instagram.com/reel/abc123')
        self.assertEqual(liste, [])
        self.assertIn('Instagram', antwort[0]['text'])

    def test_skriptauftrag_uebernimmt_nutzertext_als_daten(self):
        kanal = {'name': 'Business Origin Stories', 'format': 'geschichte', '_nutzerskript': TEXT}
        auftrag = prompts.skript(kanal, 'WeWork', '', '', '170-216')
        self.assertIn('USER SCRIPT', auftrag)
        self.assertIn('user_script_to_adapt', auftrag)
        self.assertNotIn('USER SCRIPT', prompts.skript(dict(kanal, _nutzerskript=''), 'WeWork', '', '', '170-216'))
