"""Eine redaktionelle Vorlage mit heute gelesener Primaerquelle, ohne Noten."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
import trends

URL = 'https://huggingface.co/Qwen/Qwen-Image-2.1'


def main():
    quelle = trends._hole(URL + '/raw/main/README.md').decode('utf-8')
    saetze = [
        ('hook', 'illustration', 'three unlettered creative objects on a desk: a cutout silhouette, a floral picture with a circle annotation, a row of miniature portrait frames; no people or hands',
         'A beautiful AI picture is only the beginning. What happens when you need a clean cutout, a specific change, or the same person again?'),
        ('frage', 'karte', 'brief identification of Qwen Image model, no popularity metrics',
         'Qwen-Image two point one brings generation and editing into one model. Let us check three features before you build a workflow around it.'),
        ('beleg', 'demo', 'native transparent image examples from the source showcase, distinct stickers',
         'First, transparent images. The model can generate an image with an alpha channel, or extract a subject from a photograph. Think cutouts and separate visual layers.'),
        ('erklaerung', 'illustration', 'an original creator arranging isolated paper cutout layers on a clean desk',
         'There is a detail to save: its transparency example explicitly asks for an RGBA image, an alpha channel and a transparent background. That is the documented prompt pattern.'),
        ('beleg', 'illustration', 'artist indicating one selected area of an unlettered illustration with a colored ring',
         'Second, targeted edits. You can indicate a local change with a circle, painted annotation or separate mask. The request can point to a specific area.'),
        ('beleg', 'demo', 'the source example group photograph made from six portrait references',
         'Third, reference images. It supports up to ten, with identity preservation for people and products. The showcase includes a group photograph built from six portrait references.'),
        ('wendung', 'illustration', 'original presenter examining a plain folder before adding it to a creative project',
         'Before you use it, check the license. The model is released under the Qwen Research License, linked on its model page. That deserves a look.'),
        ('aufloesung', 'illustration', 'the same original presenter in a confident head-and-shoulders portrait beside a wall displaying three unlettered visual cards: cutout, selection ring, portraits; hands outside frame',
         'So check transparency, targeted editing and references, rather than judging one pretty image. Be sure to like, share and save this video.'),
    ]
    s = {'kanal': 'AI Tools Explained', 'thema': 'Qwen Image: beyond a pretty picture',
         'titel': ['Beyond A *Pretty* *Picture*', 'Three Workflow Checks'],
         'stimme': 'am_michael', 'tempo': 1.08, 'titel_farbe': '#20D2BE',
         'videoformat': 'short', 'format': 'erklaerung', 'laenge_s': [62, 90],
         'untertitel_profil': 'ruhig', 'musik': True, 'musik_suche': ['curious electronic pulse'],
         'belege': [{'quelle': 'Hugging Face: original model card', 'name': 'Qwen/Qwen-Image-2.1',
                     'url': URL, 'text': quelle}],
         'teile': [{'beat': b, 'bildmodus': m, 'szene': scene, 'text': text,
                    'suche': 'creative image workflow', 'quelle_url': URL} for b, m, scene, text in saetze],
         'hashtags': ['AIToolsExplained', 'AIImages', 'QwenImage'],
         'beschreibung': 'Three source-supported workflow checks for Qwen-Image-2.1. Examples from the linked model card. Source: ' + URL,
         'herkunft': 'Redaktionelle Vorlage, echte unabhaengige Pruefung vor Bau erforderlich.'}
    ziel = Path('piloten/qwen-bildworkflow.json')
    s['teile'][0]['figur'] = False
    ziel.write_text(json.dumps(s, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Quellengebundene Vorlage; Woerter:', sum(len(t['text'].split()) for t in s['teile']))


if __name__ == '__main__':
    main()
