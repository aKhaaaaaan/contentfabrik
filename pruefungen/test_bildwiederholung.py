"""Weniger Bildwiederholungen (Aurelio 09.10.2026: 6 doppelte Bilder in 21 Einstellungen, Nutzer 6/10).

Alter Stand, den diese Tests erkennen:
- Jeder Neuversuch des Baus zaehlte Ersatzbilder ab 0; aus dem Cache uebernommene Ersatzbilder
  zaehlten nicht -> weit mehr Wiederholungen als die Grenze (Short: 2) erlaubt.
- Der Schrift-Schutz galt nur fuer Bildschirme; ein Messgeraet mit Ziffern wurde zweimal
  abgelehnt (ill_18), danach Ersatzbild.
"""
import unittest
from pathlib import Path

import test_betrieb  # noqa: F401 - setzt sys.path auf fabrik/
import prompts

WURZEL = Path(__file__).resolve().parents[1]


class Schrifttraeger(unittest.TestCase):
    def test_ziffernblatt_und_karte_bekommen_leere_flaechen(self):
        for szene in ('an analog meter dial measuring token input costs on a workbench',
                      'a woman at a cafe table holds a card', 'stacks of banknotes and a receipt'):
            with self.subTest(szene=szene):
                self.assertIn('no printed letters, digits', prompts.szene_ohne_schrift(szene))

    def test_szene_ohne_schrifttraeger_bleibt_unveraendert(self):
        self.assertEqual(prompts.szene_ohne_schrift('a calm harbor at dusk'), 'a calm harbor at dusk')


class Ersatzzaehlung(unittest.TestCase):
    def test_ersatzbilder_aus_dem_cache_zaehlen_mit(self):
        quelle = (WURZEL / 'fabrik/bauen.py').read_text(encoding='utf-8')
        self.assertIn("bild_ersatz += 1 if alt.get('ersatz') else 0", quelle)
        self.assertIn("'ersatz': bild_ersatz > ersatz0}", quelle)
        self.assertIn('ersatz0 = bild_ersatz', quelle)


class LetzterVersuch(unittest.TestCase):
    def test_vereinfachte_szene_vor_dem_ersatzbild(self):
        # Netflix-Langvideo 09.10.: 3 Bauabbrueche; mit korrekt gezaehlten Ersatzbildern waere das
        # Video gescheitert. Erst ein vereinfachter Versuch, dann Ersatzbild.
        quelle = (WURZEL / 'fabrik/bauen.py').read_text(encoding='utf-8')
        neu = quelle.index("einfach = ('One clear subject")
        ersatz = quelle.index('if not material and bild_ersatz < ersatz_max:')
        self.assertLess(neu, ersatz)
        self.assertIn("kanal_slug, False, False,", quelle[neu:neu + 700])  # ohne Kanalfigur


class Vollbild(unittest.TestCase):
    def test_langvideo_illustration_fuellt_den_bildschirm(self):
        # Nutzer 09.10. zum Netflix-Langvideo: Bilder zu klein, halber Bildschirm leer, fremder
        # unscharfer Hintergrund. Alter Stand: Querformat-Illustration als Karte auf hintergrund_holen().
        quelle = (WURZEL / 'fabrik/bauen.py').read_text(encoding='utf-8')
        # Nutzerwunsch: Motiv gross, dahinter DASSELBE Bild verschwommen (nicht hintergrund_holen()).
        stelle = quelle.index('            if ill and B > H:')
        block = quelle[stelle:stelle + 300]
        self.assertIn("karten_ebene(ill, kasten='gross')", block)
        self.assertIn('karten_filter(ill, ebene, kpfad)', block)
        self.assertNotIn('hintergrund_holen', block)

    def test_grosser_kasten_fuellt_mindestens_drei_viertel_der_breite(self):
        import bauen
        bauen.format_setzen('lang')
        try:
            x1, y1, x2, y2 = bauen.LAYOUT['gross']
            self.assertGreaterEqual((x2 - x1) / bauen.B, 0.75)
            self.assertAlmostEqual((x1 + x2) / 2, bauen.B / 2)  # mittig, keine leere Haelfte
        finally:
            bauen.format_setzen('short')


class SchriftWunsch(unittest.TestCase):
    # Pilot 37972418814: "neon pricing table with catch terms and numbers" -> 20+ Bilder verworfen.
    def test_verlangte_schrift_wird_entfernt(self):
        aus = prompts.szene_ohne_schrift('a neon pricing table with catch terms and numbers above a market stall')
        self.assertNotIn('terms', aus)
        self.assertNotIn('numbers above', aus)
        self.assertIn('blank shapes', aus)
        self.assertIn('no printed letters, digits', aus)

    def test_harmlose_szene_bleibt(self):
        self.assertEqual(prompts.szene_ohne_schrift('a calm harbor at dusk'), 'a calm harbor at dusk')

    def test_rettungsversuch_ohne_originalszene_und_schrifttraeger(self):
        quelle = (WURZEL / 'fabrik/bauen.py').read_text(encoding='utf-8')
        start = quelle.index("einfach = ('One clear subject")
        block = quelle[start:start + 500]
        self.assertIn('no object that could carry writing', block)
        self.assertNotIn('szene[:240]', block)


class KarteOhneQuelle(unittest.TestCase):
    def test_karte_ohne_karte_wird_illustration(self):
        # Pilot 37990152213: 'karte' fuer looka.com -> kein Bild versucht, 4x Bauabbruch an Einstellung 4.
        quelle = (WURZEL / 'fabrik/bauen.py').read_text(encoding='utf-8')
        i = quelle.index("if modus == 'karte' and not karte:")
        self.assertIn("modus = 'illustration'", quelle[i:i + 400])
        self.assertLess(i, quelle.index("if os.environ.get('CLOUDFLARE_AI_TOKEN') and modus in ('auto', 'illustration', 'foto')"))
        self.assertIn('auch vereinfachte Szene nicht bestanden', quelle)


class SchrifttraegerNichtPlanen(unittest.TestCase):
    def test_szenenregel_verbietet_papiere_als_motiv(self):
        # Pilot 37990152213: "floating price sheets" -> Schriftsalat, Bild verworfen.
        self.assertIn('papers, price sheets, receipts, banknotes', prompts.SZENEN)
        self.assertIn('never the written object itself', prompts.SZENEN)


class Versionen(unittest.TestCase):
    def test_pakete_sind_festgelegt(self):
        zeilen = [z.strip() for z in (WURZEL / 'requirements.txt').read_text(encoding='utf-8').splitlines()
                  if z.strip() and not z.startswith('#')]
        for z in zeilen:
            if z != 'tzdata':
                with self.subTest(z=z):
                    self.assertIn('==', z)


if __name__ == '__main__':
    unittest.main()
