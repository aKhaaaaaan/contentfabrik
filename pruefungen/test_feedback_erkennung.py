"""Feedback statt Themen-Idee (10.10.2026).

Alter Stand, den dieser Test erkennt: Die Nachricht „Business Stories hat leider nicht die
Ueberschrift Funktion ... waere besser" landete als Themen-Idee 8 in der Business-Warteschlange.
"""
import unittest

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import themen

FEEDBACK = ('Business Stories hat leider nicht die Überschrift Funktion wenn sie um einen Firma reden, das wäre '
            'vielleicht besser wenn da auch so ähnlich wie bei ai Tools explained Logo und Name für ganze Video '
            'erwähnt wird, sonst passt es aber es gibt weitere Luft nach oben')
THEMEN = ['Wie Netflix Blockbuster zerstörte – und dann fast selbst unterging',
          'Warum ein Milliardär sein eigenes Unternehmen zerstörte',
          'Wie ein 22-Jähriger mit einer App 700.000 $ im Jahr verdient',
          'Die Akquisition, die 50 Milliarden $ zu viel kostete',
          'Vom Garagen-Startup zum Milliardendeal - und zurück']


class Erkennung(unittest.TestCase):
    def test_echte_rueckmeldung_ist_feedback(self):
        self.assertTrue(themen.ist_feedback(FEEDBACK))

    def test_echte_themenideen_bleiben_themen(self):
        for t in THEMEN:
            with self.subTest(t=t):
                self.assertFalse(themen.ist_feedback(t))


if __name__ == '__main__':
    unittest.main()
