"""themen.yml: Sichern darf nicht an liegengebliebenen Dateien scheitern (10.10.2026).

Alter Stand, den dieser Test erkennt: Die Trend-Check-Vorschau (manueller Start) schrieb
verlauf/trendcheck/*.json; "git pull --rebase" brach wegen ungesicherter Aenderungen ab ->
Nutzerbewertungen aus Telegram (Lauf 38050016572) wurden nicht gespeichert.
"""
import unittest
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]


class ThemenWorkflow(unittest.TestCase):
    def test_pull_mit_autostash(self):
        yml = (WURZEL / '.github/workflows/themen.yml').read_text(encoding='utf-8')
        self.assertNotIn('git pull -q --rebase ||', yml)
        self.assertEqual(yml.count('git pull -q --rebase --autostash || exit 1'), 2)


    def test_alle_fuenf_minuten_in_eigener_warteschlange(self):
        # Nutzer 10.10.: „4 Std. ist viel zu lang". Gemeinsame Gruppe mit video.yml liess die
        # Abholung hinter einem 1-2-stuendigen Videobau warten.
        yml = (WURZEL / '.github/workflows/themen.yml').read_text(encoding='utf-8')
        self.assertIn("- cron: '*/5 * * * *'", yml)
        self.assertIn('group: contentfabrik-themen', yml)
        self.assertNotIn('group: contentfabrik-zustand', yml)
        self.assertIn("github.event.schedule == '*/5 * * * *'", yml)  # Erfolgszahlen-Schritt laeuft weiter
        self.assertIn('erfolg/.letzter_abruf', yml)  # aber nur einmal je Tag


if __name__ == '__main__':
    unittest.main()
