"""Hoerprobe zum Auswaehlen: derselbe Satz in Kokoro- und Chatterbox-Stimmen.

GEMELDET: „Nur 3 Stimmen, damit es nicht so kuenstlich klingt - oder im Netz
nach kostenlosen besseren Stimmen schauen." Kandidaten (alle gewerblich frei):
  Kokoro (Apache 2.0): die 3 vom Nutzer gewaehlten + die zwei bestbewerteten
  Chatterbox (MIT, Resemble AI): ausdrucksstark mit Emotions-Regler; als
    Stimmvorlage dienen die Kokoro-Stimmen des Nutzers (Apache 2.0) - so
    klingt es nach SEINEN Stimmen, nur lebendiger.
Misst die Rechenzeit je Probe (Chatterbox auf GitHub-CPU: ungeprueft).

Aufruf:  python fabrik/stimmproben.py proben/
"""
import sys, time, wave
from pathlib import Path
import numpy as np
from kokoro_onnx import Kokoro

# Eigener Beispielsatz (Business-Kanal), keine fremden Texte
SATZ = ("They lost almost everything on farm machines. So in a tiny movie theater canteen, "
        "they started frying potato chips. Nobody believed it would work. Today, it is a billion dollar brand.")
WOERTER = len(SATZ.split())
NUTZER = ['am_michael', 'bf_emma', 'bm_george']   # Wahl des Nutzers nach Gehoer (02.10.2026)
BESTE = ['af_heart', 'af_bella']                  # Bestnoten laut Kokoro-VOICES.md


def schreiben(pfad, audio, rate):
    with wave.open(str(pfad), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())


aus = Path(sys.argv[1]); aus.mkdir(parents=True, exist_ok=True)
k = Kokoro('modelle/kokoro-v1.0.onnx', 'modelle/voices-v1.0.bin')
nr = 0
for stimme in NUTZER + BESTE:
    nr += 1
    t = time.time()
    audio, rate = k.create(SATZ, voice=stimme, speed=1.05, lang='en-gb' if stimme.startswith('b') else 'en-us')
    schreiben(aus / f'{nr:02d}_kokoro_{stimme}.wav', audio, rate)
    print(f'{nr} kokoro {stimme}: {len(audio) / rate:.1f} s Ton, {WOERTER / (len(audio) / rate):.2f} W/s, '
          f'{time.time() - t:.1f} s Rechenzeit')

try:
    import torch, torchaudio
    from chatterbox.tts import ChatterboxTTS
    torch.set_num_threads(4)
    t = time.time()
    modell = ChatterboxTTS.from_pretrained(device='cpu')
    print(f'Chatterbox geladen in {time.time() - t:.0f} s')
    for stimme in NUTZER:
        vorlage = next(aus.glob(f'*_kokoro_{stimme}.wav'))
        for gefuehl in (0.5, 0.8):  # 0.5 = natuerlich, 0.8 = lebhaft
            nr += 1
            t = time.time()
            wav = modell.generate(SATZ, audio_prompt_path=str(vorlage), exaggeration=gefuehl, cfg_weight=0.5)
            ziel = aus / f'{nr:02d}_chatterbox_{stimme}_gefuehl{int(gefuehl * 10)}.wav'
            torchaudio.save(str(ziel), wav, modell.sr)
            dauer = wav.shape[-1] / modell.sr
            print(f'{nr} chatterbox {stimme} {gefuehl}: {dauer:.1f} s Ton, {time.time() - t:.0f} s Rechenzeit '
                  f'(Faktor {(time.time() - t) / dauer:.1f})')
except Exception as e:
    print('Chatterbox nicht moeglich:', str(e)[:300])
