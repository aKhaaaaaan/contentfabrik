"""Chatterbox-Proben (MIT) in EIGENER Umgebung - nur fuer die Hoerprobe.

GEMESSEN 03.10.2026: „pip install chatterbox-tts" scheiterte in derselben
Umgebung wie Kokoro (feste Paketversionen beissen sich). Darum laeuft dieses
Skript mit einer eigenen venv; Vorlage sind die Kokoro-Proben des Nutzers.

Aufruf:  cb/bin/python fabrik/chatterbox_proben.py proben/
"""
import sys, time
from pathlib import Path
import torch, torchaudio
from chatterbox.tts import ChatterboxTTS

sys.path.insert(0, str(Path(__file__).parent))
SATZ = ("They lost almost everything on farm machines. So in a tiny movie theater canteen, "
        "they started frying potato chips. Nobody believed it would work. Today, it is a billion dollar brand.")
NUTZER = ['am_michael', 'bf_emma', 'bm_george']

aus = Path(sys.argv[1])
torch.set_num_threads(4)
t = time.time()
modell = ChatterboxTTS.from_pretrained(device='cpu')
print(f'Chatterbox geladen in {time.time() - t:.0f} s')
nr = 5
for stimme in NUTZER:
    vorlage = next(aus.glob(f'*_kokoro_{stimme}.wav'))
    for gefuehl in (0.5, 0.8):  # 0.5 = natuerlich, 0.8 = lebhaft
        nr += 1
        t = time.time()
        wav = modell.generate(SATZ, audio_prompt_path=str(vorlage), exaggeration=gefuehl, cfg_weight=0.5)
        torchaudio.save(str(aus / f'{nr:02d}_chatterbox_{stimme}_gefuehl{int(gefuehl * 10)}.wav'), wav, modell.sr)
        dauer = wav.shape[-1] / modell.sr
        print(f'{nr} chatterbox {stimme} {gefuehl}: {dauer:.1f} s Ton, {time.time() - t:.0f} s Rechenzeit '
              f'(Faktor {(time.time() - t) / dauer:.1f})')
