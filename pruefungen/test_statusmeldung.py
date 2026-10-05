"""Statusmeldungen fuer abgelehnte Entwuerfe ohne Versand schwacher Videos."""
import json
import os
from pathlib import Path
from unittest.mock import patch
from test_betrieb import TempTest, SKRIPT, STORY_KATEGORIEN
import statusmeldung


class StatusTest(TempTest):
    def speichern(self, skript=None, bericht=None):
        Path('ausgabe').mkdir()
        if skript is not None:
            Path('ausgabe/skript.json').write_text(json.dumps(skript), encoding='utf-8')
        if bericht is not None:
            Path('ausgabe/bericht.json').write_text(json.dumps(bericht), encoding='utf-8')

    def test_faktenfehler_hat_keine_erfundene_note_oder_zustellung(self):
        self.speichern(dict(SKRIPT, pruefung={'ok': False}, story=None))
        grund = statusmeldung.fehlergrund()
        self.assertIn('Faktenpruefung nicht bestanden', grund)
        self.assertNotIn('9/10', grund)
        self.assertNotIn('Note fehlt', grund)

    def test_story_sechs_nennt_tatsaechliche_note_und_schwelle(self):
        self.speichern(dict(SKRIPT, story={'note': 6, 'kategorien': dict.fromkeys(STORY_KATEGORIEN, 6)}))
        grund = statusmeldung.fehlergrund()
        self.assertIn('6/10', grund)
        self.assertIn('9/10', grund)
        self.assertNotIn('Faktenpruefung nicht bestanden', grund)

    def test_fehlendes_oder_kaputtes_artefakt_hat_ehrlichen_fallback(self):
        Path('ausgabe').mkdir()
        Path('ausgabe/bericht.json').write_text('kaputt', encoding='utf-8')
        self.assertIn('Cloud-Lauf fehlgeschlagen', statusmeldung.fehlergrund())

    def test_bestandenes_video_mit_versandfehler_wird_nicht_als_qualitaetsfehler_gemeldet(self):
        self.speichern(SKRIPT, {'status': 'pilot_bestanden'})
        self.assertIn('Video-Pruefung bestanden', statusmeldung.fehlergrund())
        self.assertIn('Zustellung nicht abgeschlossen', statusmeldung.fehlergrund())

    def test_start_hat_richtigen_kanal_format_thema_und_keine_fertigmeldung(self):
        text = statusmeldung.text('start', {'KANAL': 'Business', 'VIDEOFORMAT': 'lang', 'THEMA': 'Nintendo'})
        self.assertIn('Business', text)
        self.assertIn('Langvideo', text)
        self.assertIn('Nintendo', text)
        self.assertIn('gestartet', text)
        self.assertNotIn('zugestellt', text)

    def test_fehlermeldung_verwendet_uebergebenen_grund_auch_ohne_artefakte(self):
        text = statusmeldung.text('fehlgeschlagen', {'GRUND': 'Skript: 6/10', 'CF_ORIGINAL_URL': 'https://github.com/run'})
        self.assertIn('6/10', text)
        self.assertIn('Kein freigegebenes Video zugestellt', text)
        self.assertIn('https://github.com/run', text)

    def test_statusversand_bestaetigt_telegramantwort_und_sendet_keinen_film(self):
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': 'test'}), \
                patch('statusmeldung.telegram', return_value={'ok': True, 'result': {'message_id': 1}}) as tg:
            statusmeldung.senden('Beide Piloten gesperrt.')
        tg.assert_called_once_with('sendMessage', {'chat_id': 'test', 'text': 'Beide Piloten gesperrt.'})

    def test_unbestaetigte_zustellung_ist_fehler(self):
        with patch.dict(os.environ, {'TELEGRAM_CHAT_ID': 'test'}), \
                patch('statusmeldung.telegram', return_value={'ok': False}), self.assertRaises(RuntimeError):
            statusmeldung.senden('Status')

    def test_zu_lange_oder_leere_statusmeldung_sendet_nichts(self):
        with patch('statusmeldung.telegram') as tg:
            for nachricht in (' ', '🚀' * 1800):
                with self.assertRaises(ValueError):
                    statusmeldung.senden(nachricht)
        tg.assert_not_called()
