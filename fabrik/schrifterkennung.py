"""Lokale Schrifterkennung fuer gemalte Bilder - vor der Gemini-Bildpruefung.

GEMESSEN 16.10.2026: Von 37 heute verworfenen Illustrationen scheiterten 14 an gemalter Schrift
("PAY REENT", "SEED FUNDIG", "Like/Share/Save"). Jede kostete eine Gemini-Pruefanfrage. RapidOCR
(Apache-2.0, ONNX auf der CPU, ~1 s je Bild) an 144 echten Bildern aus ausgabe/: mit den Schwellen
unten 30 von 118 abgelehnten Bildern erkannt (alle mit echter Kauderwelsch-Schrift), kein Fehlalarm
an schriftfreien Bildern; zusaetzlich zwei angenommene Bilder, deren Schrift Gemini uebersah
("LIVENCE MAPILRI", Ladenschild "BBEAIRS"). Kleine Hintergrundschrift (< 2 % Bildhoehe) bleibt
Sache des Pruefers, sonst steigen die Fehlversuche.
"""
import io
import re

MIN_SICHER = 0.7     # Erkennungssicherheit
MIN_HOEHE = 0.02     # Texthoehe relativ zur Bildhoehe
MIN_BUCHSTABEN = 4   # kuerzere Funde waren oft Ziffern/Kanten ("DS", "80")

# Positiv formuliert: die gefundenen Woerter NICHT in den naechsten Bildauftrag schreiben -
# genannte Dinge malt die Bild-KI hinein (10.10.2026).
KORREKTUR = 'Every surface is plain and unmarked, clean painted surfaces only'

_OCR = []


def _ocr():
    if not _OCR:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _OCR.append(RapidOCR())
        except Exception as e:  # fehlt die Bibliothek: wie bisher nur Gemini
            print('Lokale Schrifterkennung nicht verfuegbar:', type(e).__name__)
            _OCR.append(None)
    return _OCR[0]


def funde(ergebnis, hoehe):
    """Deutliche Schrift aus dem RapidOCR-Ergebnis [(box, text, sicherheit), ...]."""
    treffer = []
    for box, text, sicher in ergebnis or []:
        ys = [p[1] for p in box]
        if float(sicher) >= MIN_SICHER and (max(ys) - min(ys)) / hoehe >= MIN_HOEHE \
                and len(re.sub(r'[^A-Za-z]', '', str(text))) >= MIN_BUCHSTABEN:
            treffer.append(str(text))
    return treffer


def gemalte_schrift(roh):
    """Liste deutlich lesbarer Schriftstuecke im Bild (Bytes); leer, wenn keine oder OCR fehlt."""
    ocr = _ocr()
    if not ocr:
        return []
    try:
        import numpy as np
        from PIL import Image
        with Image.open(io.BytesIO(roh)) as im:
            rgb = im.convert('RGB')
        bgr = np.ascontiguousarray(np.asarray(rgb)[:, :, ::-1])
        ergebnis, _ = ocr(bgr)
        return funde(ergebnis, rgb.height)
    except Exception as e:  # nie den Bau kippen - dann entscheidet der Pruefer allein
        print('Lokale Schrifterkennung fehlgeschlagen:', type(e).__name__)
        return []
