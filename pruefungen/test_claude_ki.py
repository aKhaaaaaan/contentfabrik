"""Claude-Autor: ein Fehlschlag darf im selben Lauf nicht viermal Zeit kosten."""
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
import claude_ki  # noqa: E402


class ClaudeSperre(unittest.TestCase):
    def setUp(self):
        claude_ki._gesperrt = None
        self.env = patch.dict('os.environ', {'CLAUDE_CODE_OAUTH_TOKEN': 'x'})
        self.env.start()
        self.which = patch.object(claude_ki.shutil, 'which', return_value='claude')
        self.which.start()

    def tearDown(self):
        claude_ki._gesperrt = None
        self.which.stop()
        self.env.stop()

    def test_zeitlimit_sperrt_weitere_versuche(self):
        # Vor dem Fix: jeder Schreibversuch rief die CLI erneut auf (4 x 240 s).
        with patch.object(claude_ki.subprocess, 'run',
                          side_effect=subprocess.TimeoutExpired('claude', 240)) as run:
            for _ in range(4):
                daten, grund = claude_ki.schreiben('p', {}, zeit=240)
                self.assertIsNone(daten)
        self.assertEqual(run.call_count, 1)
        self.assertFalse(claude_ki.verfuegbar())
        self.assertIn('abgeschaltet', grund)

    def test_erfolg_bleibt_verfuegbar(self):
        antwort = json.dumps({'is_error': False, 'result': '```json\n{"a": 1}\n```'})
        with patch.object(claude_ki.subprocess, 'run',
                          return_value=subprocess.CompletedProcess([], 0, antwort, '')) as run:
            for _ in range(2):
                self.assertEqual(claude_ki.schreiben('p', {})[0], {'a': 1})
        self.assertEqual(run.call_count, 2)
        self.assertTrue(claude_ki.verfuegbar())

    def test_unbrauchbare_antwort_sperrt(self):
        claude_ki.sperren('Antwort passt nicht zum Schema')
        self.assertFalse(claude_ki.verfuegbar())


if __name__ == '__main__':
    unittest.main()
