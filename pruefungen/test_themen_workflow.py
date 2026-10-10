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


if __name__ == '__main__':
    unittest.main()
