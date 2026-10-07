"""Probe: Gemini-Bildmodelle als kostenloser Zweitweg neben Cloudflare FLUX.

GEMELDET 07.10.2026: „Koennen wir statt Cloudflare nicht gratis andere Anbieter
nutzen?" GEMESSEN 07.10.: Cloudflare-Gratiskontingent nach ~60-70 Bildern leer,
Figur-Einsetzen scheiterte an Einstellung 0. Gemini-Bildmodelle stehen in der
Modellliste des Projekts; ob das Gratiskontingent > 0 ist, widersprechen sich
Quellen - darum echte Probe. Kein Konto-/Projekt-Wechsel zur Limitumgehung.

Aufruf: python fabrik/bildprobe_gemini.py proben/   (schreibt proben/bildprobe.json)
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODELLE = ['gemini-2.5-flash-image', 'gemini-3.1-flash-image-preview']
SZENE = ('Use the man in the reference image as the same fictional character (same face, hat, grey suit, '
         'dark tie, gold pocket watch). New scene: he stands in a bright, empty shared office at dusk, '
         'rows of identical desks, looking at the camera with a knowing half-smile. Vertical 9:16, '
         'painted urban video-game poster illustration, bold ink contours, cinematic warm light. '
         'No text, no logos, no letters anywhere.')


def erzeugen(modell, referenz):
    teile = [{'text': SZENE}]
    if referenz.is_file():
        teile.append({'inlineData': {'mimeType': 'image/jpeg',
                                     'data': base64.b64encode(referenz.read_bytes()).decode()}})
    req = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{modell}:generateContent',
        data=json.dumps({'contents': [{'parts': teile}],
                         'generationConfig': {'responseModalities': ['IMAGE', 'TEXT']}}).encode(),
        headers={'x-goog-api-key': os.environ['GEMINI_API_KEY'], 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        return None, f'HTTP {e.code}: {e.read()[:400].decode("utf-8", "replace")}'
    for c in d.get('candidates', []):
        for p in c.get('content', {}).get('parts', []):
            if str(p.get('inlineData', {}).get('mimeType', '')).startswith('image'):
                return base64.b64decode(p['inlineData']['data']), 'ok'
    return None, 'keine Bilddaten: ' + json.dumps(d)[:300]


def main(aus):
    aus = Path(aus)
    aus.mkdir(parents=True, exist_ok=True)
    ref = Path('figuren/business-origin-stories.jpg')
    ergebnis = []
    for modell in MODELLE:
        bild, status = erzeugen(modell, ref)
        eintrag = {'modell': modell, 'status': status[:400]}
        if bild:
            (aus / f'{modell}.png').write_bytes(bild)
            eintrag['datei'] = f'{modell}.png'
        print(modell, '->', status[:200])
        ergebnis.append(eintrag)
    (aus / 'bildprobe.json').write_text(json.dumps(ergebnis, indent=1, ensure_ascii=False), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
