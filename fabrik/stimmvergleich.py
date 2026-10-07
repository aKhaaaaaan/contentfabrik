"""Hoerprobe Kokoro (bisher) gegen Gemini Flash TTS mit Erzaehlregie.

GEMELDET 07.10.2026: Stories brauchen Emotion in der Stimme. Erst hoeren, dann
entscheiden: dieselbe Passage aus einem echten Vorratsskript (sonst eigener
Beispieltext) in 4 Fassungen. Der Nutzer antwortet in Telegram mit „Stimme: N"
(themen.py speichert das in themen/stimmwahl.json). Nichts wird automatisch umgestellt.

Aufruf: python fabrik/stimmvergleich.py proben/
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import stimme_gemini  # noqa: E402

BEISPIEL = ["In 2019, one office company was worth 47 billion dollars.",
            "Six weeks later, its stock market debut was cancelled.",
            "WeWork rented whole floors, split them into stylish desks, and called it a tech company.",
            "But here is the twist: the buildings were never theirs."]
# Regie in normaler Sprache (Gemini 3.8: speech_metadata.style), Text bleibt woertlich.
GEMINI = [('Charon', 'documentary narrator, calm and intimate, building quiet suspense, '
                     'slows down and lowers the voice before the twist'),
          ('Fenrir', 'energetic storyteller, curious and excited, punchy short-video pacing'),
          ('Orus', 'deep cinematic trailer voice, serious and dramatic, deliberate pauses')]


def passage():
    """Hook bis zur Wendung aus einem echten, geprueften Vorratsskript (Business)."""
    for p in sorted(Path('vorrat/business-origin-stories').glob('*.json')):
        try:
            teile = json.loads(p.read_text(encoding='utf-8'))['skript']['teile']
        except (OSError, ValueError, KeyError):
            continue
        saetze, wendung = [], None
        for i, t in enumerate(teile[:6]):
            if t.get('beat') == 'wendung' and i:
                wendung = len(saetze)
            saetze.append(t['text'].strip())
        return saetze[:5], wendung, p.stem
    return BEISPIEL, 3, 'eigener Beispieltext'


def main(aus):
    aus = Path(aus)
    aus.mkdir(parents=True, exist_ok=True)
    saetze, wendung, herkunft = passage()
    text = ' '.join(saetze)
    # Moment-Regie direkt im Text: kurze Pause vor der Wendung (nur Gemini versteht das).
    regie = ' '.join(('<short pause> ' if i == wendung else '') + s for i, s in enumerate(saetze))
    liste = []
    from kokoro_onnx import Kokoro
    k = Kokoro('modelle/kokoro-v1.0.onnx', 'modelle/voices-v1.0.bin')
    audio, rate = k.create(text, voice='bm_george', speed=1.05, lang='en-gb')
    with wave.open(str(aus / '1_kokoro.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    liste.append({'nr': 1, 'datei': '1_kokoro.wav', 'name': 'Kokoro bm_george (bisherige Stimme)'})
    for nr, (stimme, stil) in enumerate(GEMINI, 2):
        try:
            wav, modell = stimme_gemini.sprechen(regie, stimme, stil)
        except RuntimeError as e:
            print(f'Stimme {nr} ({stimme}) nicht erzeugt: {str(e)[:300]}')
            continue
        (aus / f'{nr}_gemini_{stimme}.wav').write_bytes(wav)
        liste.append({'nr': nr, 'datei': f'{nr}_gemini_{stimme}.wav',
                      'name': f'Gemini {stimme} ({modell}): {stil[:60]}'})
        print(f'Stimme {nr}: {stimme} mit {modell}')
    (aus / 'proben.json').write_text(json.dumps({'herkunft': herkunft, 'text': text, 'proben': liste},
                                                ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(liste)} Proben aus {herkunft}')
    return 0 if len(liste) > 1 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
