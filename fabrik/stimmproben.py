"""Hoerprobe: derselbe Satz in mehreren Kokoro-Stimmen, zum Auswaehlen.

Aufruf:  python fabrik/stimmproben.py ausgabe/
"""
import sys, wave
from pathlib import Path
import numpy as np
from kokoro_onnx import Kokoro

SATZ = ("Number one: Ollama. It runs large language models on your own machine. "
        "No subscription, and your data stays with you.")
# Frauen (af/bf) und Maenner (am/bm), amerikanisch (a) und britisch (b)
STIMMEN = ['af_heart', 'af_bella', 'bf_emma', 'am_michael', 'am_fenrir', 'bm_george']

aus = Path(sys.argv[1]); aus.mkdir(parents=True, exist_ok=True)
k = Kokoro('modelle/kokoro-v1.0.onnx', 'modelle/voices-v1.0.bin')
for nr, stimme in enumerate(STIMMEN, 1):
    lang = 'en-gb' if stimme.startswith('b') else 'en-us'
    audio, rate = k.create(SATZ, voice=stimme, speed=1.05, lang=lang)
    with wave.open(str(aus / f'{nr}_{stimme}.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    print('fertig:', stimme)
