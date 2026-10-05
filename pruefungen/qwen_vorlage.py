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
    bildbasis = 'https://qianwen-res.oss-accelerate.aliyuncs.com/Qwen-Image/image2.1/images/'
    def demo(n, motiv):
        return {'bildmodus': 'demo', 'demo_url': bildbasis + f'example-{n}.png',
                'suche': 'documented model output', 'szene': motiv, 'motiv': motiv}
    def ill(motiv):
        return {'bildmodus': 'illustration', 'suche': 'creative visual workflow', 'szene': motiv, 'motiv': motiv}
    s['teile'][0]['bildfolge'] = [demo('05', 'The actual floral portrait output from the model card'),
        ill('A simple floral picture, a plain paper star cutout and small portrait frames on a wooden desk; no people, pencils, books or lettering')]
    s['teile'][1]['bildfolge'] = [{'bildmodus': 'karte', 'suche': 'Qwen Image identification',
        'szene': 'Brief identification of the exact Qwen Image model', 'motiv': 'Exact model identification'},
        ill('Two unlettered framed paintings beside an open empty wooden frame, strong perspective and painted shading; no people or text'),
        ill('Three distinct creative objects on a workbench: a floral paper star, an annotation ring and a row of simple portrait frames; no hands or people')]
    s['teile'][2]['bildfolge'] = [demo('04', 'Actual transparent cartoon dragon sticker example from the model card'),
        demo('06', 'Actual transparent cartoon office character example from the model card'),
        ill('A plain paper star floating above three separate colored paper layers; visual explanation of layers, not a tool output, no people or writing')]
    s['teile'][5]['bildfolge'] = [
        ill('Three small original portrait paintings arranged beside an unmarked blank canvas, explanation of visual references, no writing'),
        ill('Ten small simple portrait frames arranged in two rows on a plain wall, clearly illustrative reference layout, no typography'),
        demo('15', 'The exact model-card composite: six supplied portrait references beside the group-photo example')]
    s['teile'][3]['bildfolge'] = [ill('A single simple floral sticker cutout on an unmarked transparent sheet; no people, hands or writing'),
        ill('A plain star cutout above a black and white checkerboard surface, visibly separated layers, no people or text'),
        ill('Three colored paper sheets arranged beside a plain star cutout, close overhead composition, no people or text')]
    s['teile'][4]['bildfolge'] = [ill('A simple painted landscape on unmarked paper with a red ring around one tree; no people or writing'),
        ill('A plain paper mask with one circular opening laid over a geometric floral painting; no people or text'),
        ill('A colored brush mark highlighting one area of a plain floral picture; no hands or letters')]
    s['teile'][6]['bildfolge'] = [ill('A plain closed folder next to a framed floral painting, quiet warm lighting, no text or people'),
        ill('An open blank folder on a wooden desk beside a simple magnifying glass, no hands, people or writing'),
        ill('A framed creative picture beside a plain folder and a small clock without numerals; no typography')]
    s['teile'][7]['bildfolge'] = [ill('A paper star cutout, a floral image with a red annotation circle and three portrait frames arranged on a desk, no people or text'),
        ill('Three clearly separate objects in a close overhead shot: a paper layer, a selection mask and a small portrait frame, no hands or text'),
        {'bildmodus': 'figur', 'szene': 'Existing original fictional channel presenter for the spoken CTA',
         'motiv': 'Original channel presenter', 'suche': 'original presenter'}]
    ziel.write_text(json.dumps(s, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Quellengebundene Vorlage; Woerter:', sum(len(t['text'].split()) for t in s['teile']))


if __name__ == '__main__':
    main()
