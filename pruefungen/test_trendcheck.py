"""Trend-Check (Nutzerauftrag 09.10.2026: Themen aus Google Trends / YouTube-Viralem).

Alter Stand, den diese Tests erkennen: lauf.py nahm stur das aelteste Warteschlangen-Thema
(themen.nehmen) - ein gerade virales Thema weiter hinten oder eine Firma in den Schlagzeilen
hatte keine Chance. Ausserdem darf ein Ausfall aller Trendquellen die Nutzerliste nie still
ueberspringen.
"""
import datetime
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import themen
import trendcheck

WURZEL = Path(__file__).resolve().parents[1]
HEUTE = datetime.date(2026, 10, 10)
LISTE = [
    {'kanal': 'business-origin-stories', 'thema': 'Netflix: Wandel', 'wikipedia': 'Netflix', 'status': 'bereit'},
    {'kanal': 'business-origin-stories', 'thema': 'Enron: Aufstieg und Fall', 'wikipedia': 'Enron', 'status': 'bereit'},
    {'kanal': 'ai-tools-explained', 'thema': 'Free AI tools checked', 'trend_suche': 'free ai tools',
     'status': 'bereit'},
]


class Rechenregel(unittest.TestCase):
    def test_signale(self):
        self.assertEqual(trendcheck.punkte(), 0)
        self.assertAlmostEqual(trendcheck.punkte(yt_faktor=8), 3.0)
        self.assertEqual(trendcheck.punkte(yt_faktor=10 ** 6), 5.0)  # gedeckelt
        self.assertEqual(trendcheck.punkte(wiki_aufwind=0.9), 0)  # sinkendes Interesse zaehlt nicht
        self.assertEqual(trendcheck.punkte(wiki_aufwind=2.0), 2.5)
        self.assertEqual(trendcheck.punkte(google=True), 4.0)
        self.assertEqual(trendcheck.punkte(eigen=True), trendcheck.BONUS_EIGEN)

    def test_google_treffer_braucht_alle_kernwoerter(self):
        heute = [('mike tyson', ['Mike Tyson sent a letter']), ('enron documentary', ['New Enron film tops charts'])]
        self.assertEqual(trendcheck.google_treffer('Enron', heute), 'enron documentary')
        self.assertIsNone(trendcheck.google_treffer('Netflix', heute))
        self.assertIsNone(trendcheck.google_treffer('free ai tools', heute))


class Auswahl(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ordner = patch.object(trendcheck, 'ORDNER', Path(self.tmp.name))
        self.ordner.start()
        self.liste = patch.object(themen, 'laden', return_value=[dict(x) for x in LISTE])
        self.liste.start()

    def tearDown(self):
        self.ordner.stop(); self.liste.stop(); self.tmp.cleanup()

    def signale(self, yt, wiki, google=(), firmen=()):
        return [patch.object(trendcheck, 'yt_faktor', side_effect=lambda b, z='': (yt.get(b), [])),
                patch.object(trendcheck, 'wiki_aufwind', side_effect=lambda t, h=None: wiki.get(t)),
                patch.object(trendcheck, 'google_heute', return_value=list(google)),
                patch('trends.firmen_im_trend', return_value=list(firmen))]

    def waehle(self, kanal, *signale):
        for s in signale:
            s.start()
        try:
            return trendcheck.waehlen(kanal, HEUTE)
        finally:
            for s in signale:
                s.stop()

    def test_virales_thema_weiter_hinten_schlaegt_das_aelteste(self):
        # Alter Stand: themen.nehmen -> immer 'Netflix: Wandel'.
        thema, bericht = self.waehle('business-origin-stories', *self.signale(
            {'Netflix': 1.5, 'Enron': 12}, {'Netflix': 0.9, 'Enron': 1.6},
            google=[('enron', ['Enron documentary tops streaming charts'])]))
        self.assertEqual(thema, 'Enron: Aufstieg und Fall')
        self.assertIn('Google Trends', bericht['grund'])

    def test_trendfirma_ohne_eigenes_thema_fuehrt_zu_freier_trendwahl(self):
        thema, bericht = self.waehle('business-origin-stories', *self.signale(
            {'Skydance Corporation': 20}, {'Skydance Corporation': 3.0},
            firmen=[('Skydance Corporation', 900000, 'American media company')]))
        self.assertEqual(thema, '')  # skript.py waehlt dann unter den Firmen im Trend
        self.assertEqual(bericht['kandidaten'][0]['begriff'], 'Skydance Corporation')

    def test_ohne_jedes_signal_bleibt_die_alte_reihenfolge(self):
        with patch.object(themen, 'nehmen', return_value='Netflix: Wandel'):
            thema, bericht = self.waehle('business-origin-stories', *self.signale({}, {}))
        self.assertEqual(thema, 'Netflix: Wandel')
        self.assertIn('alte Reihenfolge', bericht['grund'])

    def test_schwaches_signal_reicht_nicht(self):
        thema, _ = self.waehle('business-origin-stories', *self.signale({'Netflix': 1.2}, {'Netflix': 1.05}))
        self.assertEqual(thema, '')

    def test_ki_thema_mit_eigenem_suchbegriff(self):
        thema, _ = self.waehle('ai-tools-explained', *self.signale({'free ai tools': 9}, {}))
        self.assertEqual(thema, 'Free AI tools checked')

    def test_ein_ergebnis_je_tag(self):
        erst, _ = self.waehle('ai-tools-explained', *self.signale({'free ai tools': 9}, {}))
        with patch.object(trendcheck, 'yt_faktor', side_effect=AssertionError('kein zweiter YouTube-Abruf')):
            zweit, _ = trendcheck.waehlen('ai-tools-explained', HEUTE)
        self.assertEqual(erst, zweit)

    def test_ausfall_kippt_den_lauf_nicht(self):
        with patch.object(themen, 'nehmen', return_value='Netflix: Wandel'):
            thema, _ = self.waehle('business-origin-stories',
                                   patch.object(trendcheck, 'bewerten', side_effect=RuntimeError('Netz weg')))
        self.assertEqual(thema, 'Netflix: Wandel')


class Suchwinkel(unittest.TestCase):
    def test_business_sucht_die_geschichte_nicht_die_trailer(self):
        # Live 09.10.: „Netflix" allein -> Serientrailer 79,5x. Titel muss den Begriff enthalten.
        videos = [{'titel': 'Stranger Things 5 | Official Trailer', 'faktor': 80, 'aufrufe': 1, 'id': 'a'},
                  {'titel': 'How Netflix Killed Blockbuster', 'faktor': 6, 'aufrufe': 1, 'id': 'b'}]
        with patch('trends.youtube_ausreisser', return_value=videos) as yt:
            faktor, _ = trendcheck.yt_faktor('Netflix', trendcheck.ZUSATZ['business-origin-stories'])
        self.assertEqual(yt.call_args.args[0], ['Netflix story'])
        self.assertEqual(faktor, 6)


class Einbau(unittest.TestCase):
    def test_lauf_nutzt_den_trendcheck(self):
        quelle = (WURZEL / 'fabrik/lauf.py').read_text(encoding='utf-8')
        self.assertIn('trendcheck.waehlen(kanal, themen=themen)', quelle)
        self.assertNotIn('thema = themen.nehmen(kanal)', quelle)

    def test_telegram_nennt_den_trendgrund(self):
        self.assertIn("os.environ['CF_TRENDGRUND']", (WURZEL / 'fabrik/lauf.py').read_text(encoding='utf-8'))
        self.assertIn('Warum heute', (WURZEL / 'fabrik/freigabe.py').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
