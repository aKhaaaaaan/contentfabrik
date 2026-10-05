"""Sprech- und Effektaufbereitung ohne erfundene TTS-/Audio-Prompts."""
import math
import numpy as np

PEGEL = {'riser': 0.12, 'impact': 0.20, 'pop': 0.12, 'glitch': 0.10}
LAENGE = {'riser': 2.0, 'impact': 0.8, 'pop': 0.25, 'glitch': 0.35}


def sprechen(kokoro, text, stimme, tempo):
    return kokoro.create(text, voice=stimme, speed=tempo,
                         lang='en-gb' if stimme.startswith('b') else 'en-us')


def tempo_fuer(dauer, grenzen, tempo, videoformat='short', pause_s=0):
    """Gemessene Sprechdauer statt Fuelltext; nur innerhalb natuerlicher Tempi."""
    unten, oben = grenzen
    if unten <= dauer <= oben:
        return tempo
    ziel = unten if dauer < unten else oben
    if not 0 <= pause_s < min(dauer, ziel):
        return tempo
    kandidat = tempo * (dauer - pause_s) / (ziel - pause_s)
    tmin, tmax = (.9, 1.15) if videoformat == 'lang' else (.95, 1.25)
    return round(max(tmin, min(tmax, tempo * 1.2, max(tempo * .8, kandidat))), 3)


def effekt(x, art, rate):
    """Kurze Effekte, kleine Ein-/Ausblendung gegen Klicks, begrenzte Spitzen."""
    x = np.nan_to_num(np.array(x, dtype=np.float32, copy=True), nan=0, posinf=0, neginf=0)
    if not len(x):
        return x
    n = max(1, int(LAENGE.get(art, 0.65) * rate))
    # Der Hoehepunkt eines Risers bleibt am Ende, nicht im abgeschnittenen Rest.
    x = x[-n:] if art == 'riser' else x[:n]
    x *= PEGEL.get(art, 0.14) / (float(np.abs(x).max()) or 1)
    fade = min(max(1, int(rate * 0.005)), len(x) // 2)
    if fade:
        ramp = np.linspace(0, 1, fade, dtype=np.float32)
        x[:fade] *= ramp
        x[-fade:] *= ramp[::-1]
    return x


def ereignisse(saetze, dauer):
    """Keine doppelten/ungueltigen Effekte; dekorative Schnitte nicht stapeln."""
    aus, bekannt = [], set()
    letzter_schnitt = -math.inf
    gueltig = [(sek, art) for sek, art in saetze
               if isinstance(sek, (int, float)) and not isinstance(sek, bool) and math.isfinite(sek)
               and 0 <= sek < dauer and art in ('riser', 'impact', 'pop', 'whoosh')]
    for sek, art in sorted(gueltig, key=lambda e: e[0]):
        key = (round(sek, 2), art)
        if key in bekannt or (art == 'riser' and sek == 0):
            continue
        if art == 'whoosh' and sek - letzter_schnitt < 0.65:
            continue
        if art == 'whoosh':
            letzter_schnitt = sek
        bekannt.add(key)
        aus.append((sek, art))
    return aus


def begrenzen(spur):
    peak = float(np.abs(spur).max()) if len(spur) else 0
    return spur * min(1, 0.6 / peak) if peak else spur
