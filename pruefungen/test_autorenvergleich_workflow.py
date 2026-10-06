"""Der einmalige Vergleich darf nicht jaehrlich API-Kontingent verbrauchen."""
import datetime
import os
from pathlib import Path
import textwrap
from unittest.mock import patch
from test_betrieb import TempTest

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/autorenvergleich.yml'


class VergleichTerminTest(TempTest):
    def test_echter_workflow_laesst_nur_zieldatum_oder_manuelle_starts_zu(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        code = textwrap.dedent(text.split("python - <<'PY'\n", 1)[1].split('\n          PY', 1)[0])
        original = datetime.datetime
        for event, datum, erwartet in [
            ('schedule', '2026-10-06', False),
            ('schedule', '2026-10-07', True),
            ('schedule', '2027-10-07', False),
            ('workflow_dispatch', '2027-10-07', True)]:
            with self.subTest(event=event, datum=datum):
                class Datum(original):
                    @classmethod
                    def now(cls, tz=None):
                        return original.fromisoformat(datum + 'T08:00:00+00:00')
                ziel = Path('termin.txt')
                ziel.write_text('', encoding='utf-8')
                with patch.dict(os.environ, {'EREIGNIS': event, 'GITHUB_OUTPUT': str(ziel)}), \
                     patch.object(datetime, 'datetime', Datum):
                    exec(compile(code, str(WORKFLOW), 'exec'), {})
                self.assertEqual(ziel.read_text(encoding='utf-8').strip(),
                                 'erlaubt=' + str(erwartet).lower())
