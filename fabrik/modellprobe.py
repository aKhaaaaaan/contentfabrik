"""Bildprobe: FLUX.2 Klein 4B (bisher) gegen 9B mit der Business-Figur als Referenz.

Nutzerentscheidung 08.10.2026: erst sehen, ob 9B (~0,015 $/Bild statt ~0,002 $) die
Figur sichtbar besser in Szenen setzt, dann ggf. nur fuer Figuren-Szenen einbauen.
3 Szenen x 2 Modelle = 6 Bilder, Kosten unter 0,10 $. Bilder ungeprueft (reiner Vergleich).

Aufruf: python fabrik/modellprobe.py proben/
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import illustration  # noqa: E402
import prompts  # noqa: E402

SZENEN = [
    'The presenter stands in a sunlit rented loft office in 2010, looking over rows of empty shared desks, '
    'warm window light, medium shot',
    'The presenter walks along a busy sunlit city street toward camera, glowing skyline and warm haze '
    'behind him, low-angle wide shot',
    'The presenter signs a thick stack of lease papers at a dark wooden desk, lamp light, close-up on '
    'his hands and focused face',
]
MODELLE = ['flux-2-klein-4b', 'flux-2-klein-9b']


def main(aus):
    aus = Path(aus)
    aus.mkdir(parents=True, exist_ok=True)
    ref = illustration.FIGUREN / 'business-origin-stories.jpg'
    ergebnis = []
    for n, szene in enumerate(SZENEN, 1):
        for modell in MODELLE:
            felder = {'prompt': prompts.illustration(szene, True), 'width': 768, 'height': 1360}
            roh = illustration._anfrage(modell, felder, charakter=ref)
            eintrag = {'szene': n, 'modell': modell, 'ok': bool(roh)}
            if roh:
                datei = f'{n}_{modell}.jpg'
                (aus / datei).write_bytes(roh)
                eintrag['datei'] = datei
            print(n, modell, 'ok' if roh else 'kein Bild')
            ergebnis.append(eintrag)
    (aus / 'modellprobe.json').write_text(json.dumps(ergebnis, indent=1), encoding='utf-8')
    return 0 if any(e['ok'] for e in ergebnis) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
