"""Gesprochenen CTA im fertigen MP4-Mix erkennen, ohne Skript-/Untertitelvorgaben.

Lokale CPU-Erkennung; kein Gemini-Kontingent. Ein ASR-Befund ersetzt keinen Hoertest.
"""
import hashlib
import importlib.metadata
import json
import math
import re
import sys
from functools import lru_cache
from pathlib import Path
import dramaturgie
import ki_speicher

VERSION = 1
EINSTELLUNGEN = {'modell': 'base.en', 'device': 'cpu', 'compute_type': 'int8',
                 'language': 'en', 'word_timestamps': True, 'vad_filter': True,
                 'condition_on_previous_text': False, 'initial_prompt': None, 'beam_size': 5}


@lru_cache(maxsize=1)
def modell():
    from faster_whisper import WhisperModel
    return WhisperModel(EINSTELLUNGEN['modell'], device='cpu', compute_type='int8',
                        cpu_threads=4, download_root='modelle/whisper')


def transkribieren(video):
    segmente, info = modell().transcribe(str(video), **{k: v for k, v in EINSTELLUNGEN.items()
                                            if k not in ('modell', 'device', 'compute_type')})
    woerter = [{'w': w.word.strip(), 's': w.start, 'e': w.end, 'p': w.probability}
               for segment in segmente for w in (segment.words or [])]
    return {'woerter': woerter, 'dauer_s': info.duration, 'sprache': info.language}


def roh_ok(daten):
    if not isinstance(daten, dict) or not isinstance(daten.get('woerter'), list) or not daten['woerter']:
        return False
    dauer = daten.get('dauer_s')
    if isinstance(dauer, bool) or not isinstance(dauer, (int, float)) or not math.isfinite(dauer) or dauer <= 0:
        return False
    ende = 0
    for w in daten['woerter']:
        if not isinstance(w, dict) or not isinstance(w.get('w'), str) or not w['w'].strip():
            return False
        if any(isinstance(w.get(k), bool) or not isinstance(w.get(k), (int, float))
               or not math.isfinite(w[k]) for k in ('s', 'e', 'p')):
            return False
        if not ende <= w['s'] <= w['e'] <= dauer + .5 or not 0 <= w['p'] <= 1:
            return False
        ende = w['e']
    return True


def cta_bewerten(roh, art, dauer):
    if not roh_ok(roh) or isinstance(dauer, bool) or not isinstance(dauer, (int, float)) or not math.isfinite(dauer) \
            or dauer <= 0 or abs(roh['dauer_s'] - dauer) > 2:
        return {'ok': False, 'befunde': ['Endton-Rohtranskript fehlt, ist ungueltig oder hat eine andere Dauer'],
                'treffer': [], 'fenster': []}
    tokens = [(t, w) for w in roh['woerter'] for t in re.findall(r"[a-z]+(?:'[a-z]+)?", w['w'].lower())]
    text = ' '.join(t for t, _ in tokens)
    starts, pos = [], 0
    for t, _ in tokens:
        starts.append(pos)
        pos += len(t) + 1
    muster = r'\blike(?: this video)? (?:and )?share(?: this video)? (?:and )?save (?:this|the) video\b'
    treffer = []
    for m in re.finditer(muster, text):
        indices = [i for i, s in enumerate(starts) if m.start() <= s < m.end()]
        erkannt = [tokens[i][1] for i in indices]
        davor = ' '.join(t for t, _ in tokens[max(0, indices[0] - 7):indices[0]])
        if re.search(r'\b(?:not|never|no need|don\x27t)\b', davor) and 'forget' not in davor:
            continue
        if erkannt[-1]['e'] - erkannt[0]['s'] > 8 or min(w['p'] for w in erkannt) < .25 \
                or sum(w['p'] for w in erkannt) / len(erkannt) < .55:
            continue
        treffer.append({'von_s': round(erkannt[0]['s'], 2), 'bis_s': round(erkannt[-1]['e'], 2),
                        'text': m.group(), 'mittlere_wortwahrscheinlichkeit':
                        round(sum(w['p'] for w in erkannt) / len(erkannt), 3)})
    # Short: Schluss nach der Aufloesung; Langvideo: frueh nach dem Hook und im Schluss.
    schluss = max(0, dauer - max(20, min(60, dauer * .15)))
    fenster = ([{'name': 'anfang', 'von_s': 3, 'bis_s': min(90, dauer * .25)}] if art == 'lang' else [])
    fenster += [{'name': 'schluss', 'von_s': schluss, 'bis_s': dauer + .5}]
    befunde = []
    for f in fenster:
        f['erkannt'] = any(f['von_s'] <= t['von_s'] and t['bis_s'] <= f['bis_s'] for t in treffer)
        if not f['erkannt']:
            befunde.append(f"Gesprochenes Liken, Teilen UND Speichern im {f['name']} nicht sicher erkannt")
    return {'ok': not befunde, 'befunde': befunde, 'treffer': treffer, 'fenster': fenster}


def pruefen(video, skript, dauer, aus=None):
    pfad = Path(aus) if aus else Path(video).with_name('audio-pruefung.json')
    sha = hashlib.sha256(Path(video).read_bytes()).hexdigest()
    try:
        bibliothek = importlib.metadata.version('faster-whisper')
        alt = ki_speicher.lesen_json(pfad)
        key = ki_speicher.hashwert([VERSION, sha, EINSTELLUNGEN, bibliothek])
        wiederverwendet = alt.get('roh_key') == key and roh_ok(alt.get('roh'))
        roh = alt['roh'] if wiederverwendet else transkribieren(video)
        ergebnis = cta_bewerten(roh, dramaturgie.videoformat(skript), dauer)
        ergebnis.update(roh=roh, roh_key=key, wiederverwendet=wiederverwendet,
                        bibliothek_version=bibliothek)
    except Exception as e:
        ergebnis = {'ok': False, 'befunde': [f'Endton-Erkennung nicht moeglich ({type(e).__name__})'],
                    'treffer': [], 'fenster': []}
    ergebnis.update(version=VERSION, video_sha256=sha, einstellungen=EINSTELLUNGEN,
                    videoformat=dramaturgie.videoformat(skript), dauer_s=dauer,
                    methode='Unveraendertes ASR-Rohtranskript der fertigen MP4; keine Skriptangleichung')
    ki_speicher.speichern(pfad, ergebnis)
    return ergebnis


if __name__ == '__main__':
    skript = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    ergebnis = pruefen(sys.argv[1], skript, float(sys.argv[3]))
    print(json.dumps({k: ergebnis[k] for k in ('ok', 'treffer', 'fenster', 'befunde')}, indent=2))
    sys.exit(0 if ergebnis['ok'] else 1)
