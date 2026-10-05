"""Layoutvorschau mit echter Renderer-Geometrie; kein Video-/ASS-Render."""
import sys
from pathlib import Path
from PIL import ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
import bauen


def main(quelle, ziel):
    ziel = Path(ziel)
    ziel.mkdir(parents=True, exist_ok=True)
    for art in ('short', 'lang'):
        bauen.format_setzen(art)
        bauen.FORTSCHRITT.update(plaetze=[], aktuell=None)
        akzent = bauen.akzent_farbe({'titel_farbe': '#FFC83D'})
        img = bauen.verlauf_bild(akzent).convert('RGBA')
        img.alpha_composite(bauen.karten_ebene(quelle, kasten=True))
        img.alpha_composite(bauen.bild_fuer({}, ['A *business*', '*origin* story'], 0, 8,
                                           durchsichtig=True, akzent=akzent))
        d = ImageDraw.Draw(img)
        f, lines, cx, cy = bauen.bildtext_layout('Two different machines')
        text = '\n'.join(lines)
        w = max(d.textlength(line, font=f) for line in lines)
        h = (f.size + 12) * len(lines)
        d.rounded_rectangle((cx - w / 2 - 20, cy - h / 2 - 20, cx + w / 2 + 20, cy + h / 2 + 20),
                            radius=12, fill=(10, 14, 20, 240))
        d.multiline_text((cx, cy), text, font=f, anchor='mm', fill='white', align='center', spacing=12)
        f = bauen.schrift(64 if art == 'lang' else 96, str(bauen.SCHRIFTEN / 'Anton-Regular.ttf'))
        d.text((bauen.LAYOUT['mitte'], bauen.LAYOUT['untertitel_y']), 'THE SAME FOUNDER', font=f,
               anchor='ms', fill='white', stroke_width=4, stroke_fill='black')
        img.convert('RGB').save(ziel / f'{art}-layout.png')
    bauen.format_setzen()


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'ausgabe/gestaltung')
