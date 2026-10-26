"""Bildprobe: bisheriger Malauftrag gegen einen FLUX-gerechten Auftrag, gleiche Szenen, gleiches Modell.

Nutzerhinweis 26.10.2026: Die ersten Codex-Motive entstanden mit image_gen (GPT-Image); dessen Auftraege
wurden als Stilvorlage fuer FLUX uebernommen. FLUX.2 versteht aber keine Verneinung (keine Negativ-Prompts),
gewichtet fruehe Woerter staerker und baut kurze Auftraege nicht selbst aus (laut BFL, Quellen in
docs.bfl.ai/guides/prompting_guide_flux2 und help.bfl.ai, Artikel "generate quickly with FLUX.2 [klein]").
Gemessen am Bristol-Myers-Squibb-Bild 1 vom 26.10.: 211 Woerter, Szene erst ab Wort 41, zehn unerwuenschte
Dinge namentlich genannt, "golden-hour, inviting" bei einem naechtlichen Brand.

Reiner Vergleich ohne Bildpruefung und ohne Produktionseinfluss: prompts.py und illustration.py bleiben
unveraendert; der neue Auftrag lebt nur hier, bis der Nutzer die Bilder gesehen hat.
6 Szenen x 2 Auftraege = 12 Bilder mit flux-2-klein-4b (Gratiskontingent).

Aufruf: python fabrik/promptprobe.py proben/
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bildplan  # noqa: E402
import illustration  # noqa: E402
import prompts  # noqa: E402

# Echte Szenen aus den Bildplaenen des Tageslaufs 40291456997 (26.10.2026), unveraendert.
SZENEN = [
    ('business-origin-stories', 'One fire nearly ended Squibb, and failed.',
     'medium shot of One fire nearly ended as the clear focal subject, brick building catching fire rapidly, '
     'in Brooklyn street, 1850s. Visible detail: weathered red brick wall, dark smoke plumes, flickering orange '
     'flames, dark night shadow contrast'),
    ('business-origin-stories', 'Squibb pushed purity standards.',
     'close-up of purity standards as the clear focal subject, chemist inspecting clear glass vial, in laboratory '
     'workbench, 1860. Visible detail: clear glass flask, fluid transparency, worn oak workbench surface, bright '
     'directional daylight'),
    ('business-origin-stories', 'Neither. In 1989, the rivals merged,',
     'medium shot of merged as the clear focal subject, Two executives shaking hands across desk, in 1980s '
     'corporate office, late 1980s. Visible detail: Dark wool suits, polished mahogany wood grain, crisp paper '
     'documents resting on the desk, soft ambient window light'),
    ('ai-tools-explained', 'The sources answer carefully.',
     'detail shot of sources answer carefully as the clear focal subject, reviewing reference materials, in '
     'virtual interface space, present day. Visible detail: smooth wooden desk surface, textured paper edges, '
     'soft warm window light, subtle ambient shadows, clean background depth'),
    ('ai-tools-explained', 'No source shows anyone building a TV operating system with it.',
     'An engineer in a modern workshop sits at a clean workbench, carefully adjusting the thin bezel of a large '
     'television display, medium shot, warm directional spotlight.'),
    ('ai-tools-explained', 'Its first consumer launch came in May 2021, on the first-generation Nest Hub.',
     'medium shot of first consumer launch as the clear focal subject, display rests on countertop, in modern '
     'sunny kitchen, May 2021. Visible detail: Matte grey plastic housing, smooth edges, subtle ambient glow on '
     'screen, warm directional daylight, soft depth shadows'),
]

# Nur positiv beschrieben: was FLUX liest, malt es eher. Licht kommt aus der Szene statt fest "golden hour".
STIL_FLUX = ('Realistic hand-painted digital illustration in the look of open-world video game key art: '
             'lifelike faces and natural hands, rich material textures, cinematic rim light, deep contrast, '
             'soft depth of field. Lighting and mood follow the scene. Plain unmarked surfaces. '
             'Vertical frame, main action in the center, calm sky or wall at the top and floor at the bottom.')

VORLAGE = re.compile(r'^(?P<einstellung>' + '|'.join(map(re.escape, bildplan.EINSTELLUNGEN)) + r') of (?P<motiv>.+?) '
                     r'as the clear focal subject, (?P<aktion>.+?), in (?P<ort>.+?), (?P<epoche>[^.]+?)'
                     r'(?:\. Visible detail: (?P<details>.+))?$', re.S)


# Runde 2 (26.10.2026): Nutzer und Sichtung fanden ALT bei Wärme, Gesichtern und Fülle besser (Szene 4),
# NEU bei Bildtreue (kein Schriftsalat, kein Mann im Feuer). Mischung: Aufbau aus NEU, Stilworte aus ALT,
# alle Verbote positiv umformuliert. Warmes Abendlicht nur, wenn die Szene kein eigenes Licht nennt.
STIL_MISCH = ('Realistic hand-painted digital painting, open-world-game key art look: lifelike faces, thin '
              'linework only around figures, rich material textures, deep warm contrast, soft depth of field, '
              'visible brushwork. Vivid, warm, inviting and richly filled, with visible emotion in faces and '
              'gestures; where fitting lived-in streets, warm haze, buildings true to the scene period and place. '
              'Original fictional characters. One clear focal action in the central 60 percent, coherent '
              'perspective and plausible period-appropriate props. Natural anatomy, simple readable hand poses, '
              'distinct objects. Plain unmarked surfaces. Vertical frame with uncluttered top and bottom areas.')
LICHT = re.compile(r'\b(light|lighting|lit|sun\w*|night|dusk|dawn|evening|glow\w*|lamp\w*|flames?|fire|'
                   r'candle\w*|shadows?|spotlight|daylight|moon\w*)\b', re.I)
# Nur echte Bildschirme; "documents" loeste in Runde 1 Monitore im Buero von 1989 aus.
ECHTER_BILDSCHIRM = re.compile(r'\b(screens?|monitors?|displays?|dashboards?|tablets?|laptops?|terminals?|'
                               r'TVs?|televisions?)\b', re.I)


def auftrag_misch(szene):
    s = szene_flux(szene, ECHTER_BILDSCHIRM)
    licht = '' if LICHT.search(s) else ' Golden-hour rim light.'
    return f'{s}.{licht} {STIL_MISCH}'


def _gross(s):
    return s[:1].upper() + s[1:]


def szene_flux(szene, bildschirm_muster=None):
    """Vorlagenszene umstellen: Handlung zuerst, abstraktes Satzmotiv ("One fire nearly ended") raus.
    Freie Szenen sind schon Fliesstext und bleiben.

    prompts.szene_ohne_schrift() haengt bei Bildschirmen den Satz "... no letters, words, numbers or icons"
    an - genau die Woerter, die FLUX dann malt. Hier positiv: weiches abstraktes Leuchten."""
    bildschirm = bool((bildschirm_muster or prompts.BILDSCHIRM).search(szene))
    szene = prompts.szene_ohne_schrift(szene).split('. Every screen, display')[0]
    szene = szene.split('. All surfaces in the scene are plain and unmarked')[0].strip().rstrip('.')
    m = VORLAGE.match(szene)
    if m:
        teile = [f"{_gross(m['aktion'])}, in {m['ort']}, {m['epoche']}"]
        if m['details']:
            teile.append(_gross(m['details'].rstrip('.')))
        teile.append(_gross(m['einstellung']))
    else:
        teile = [szene]
    if bildschirm:
        teile.append('Screens glow with soft blurred abstract color shapes')
    return '. '.join(teile)


def auftrag_flux(szene):
    return f'{szene_flux(szene)}. {STIL_FLUX}'


def main(aus):
    aus = Path(aus)
    aus.mkdir(parents=True, exist_ok=True)
    ergebnis = []
    for n, (kanal, satz, szene) in enumerate(SZENEN, 1):
        alt = prompts.szene_ohne_schrift(szene)  # wie in illustration.bild()
        varianten = {'alt': prompts.illustration(alt, False, '', 'short', illustration.kanal_stil(kanal)),
                     'neu': auftrag_flux(szene)}
        if RUNDE == 2:
            # ALT noch einmal: FLUX zieht je Bild einen neuen Zufall, ein Bild je Variante ist eine duenne Probe.
            varianten = {'alt': varianten['alt'], 'misch': auftrag_misch(szene)}
        for name, text in varianten.items():
            roh = illustration._anfrage('flux-2-klein-4b', {'prompt': text, 'width': 768, 'height': 1360})
            eintrag = {'szene': n, 'kanal': kanal, 'satz': satz, 'variante': name, 'woerter': len(text.split()),
                       'prompt': text, 'ok': bool(roh)}
            if roh:
                eintrag['datei'] = f'{n}_{name}.jpg'
                (aus / eintrag['datei']).write_bytes(roh)
            print(n, name, eintrag['woerter'], 'Woerter', 'ok' if roh else 'kein Bild')
            ergebnis.append(eintrag)
    (aus / 'promptprobe.json').write_text(json.dumps(ergebnis, ensure_ascii=False, indent=1), encoding='utf-8')
    return 0 if any(e['ok'] for e in ergebnis) else 1


RUNDE = 2

if __name__ == '__main__':
    if sys.argv[1:] == ['--zeigen']:
        for kanal, satz, szene in SZENEN:
            print(len(auftrag_misch(szene).split()), auftrag_misch(szene), '\n')
        sys.exit(0)
    sys.exit(main(sys.argv[1]))
