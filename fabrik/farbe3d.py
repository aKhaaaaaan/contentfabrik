"""Farblook der Blender-3D-Motive (Nutzer 12.11.2026).

Favorit des Nutzers: Blender-Render Runde 2 (24 Samples, Blender 4.2.3 LTS, "leichte Farbe"); Codex-Uebermalung
und Malfilter wirkten "zu billig". Wunsch: "Licht noch waermer und mehr farbig" -> Stufe 1 (Empfehlung, Nutzer:
"Deine Empfehlung umsetzen"): Rot +6 %, Gruen +2,4 %, Blau -10 %, Saettigung x1,25, Kontrast x1,06.
Stufe 2 (x1,45 Saettigung) kippte beim Chip ins Orange.

Aufruf: python fabrik/farbe3d.py <eingabe.jpg> <ausgabe.jpg>
"""
import sys

ROT, BLAU, SAETTIGUNG, KONTRAST = 1.06, 0.90, 1.25, 1.06


def warm(bild):
    import numpy as np
    from PIL import Image, ImageEnhance
    a = np.asarray(bild.convert('RGB')).astype(np.float32)
    a[..., 0] *= ROT
    a[..., 1] *= 1 + (ROT - 1) * 0.4
    a[..., 2] *= BLAU
    bild = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return ImageEnhance.Contrast(ImageEnhance.Color(bild).enhance(SAETTIGUNG)).enhance(KONTRAST)


if __name__ == '__main__':
    from PIL import Image
    warm(Image.open(sys.argv[1])).save(sys.argv[2], 'JPEG', quality=93)
