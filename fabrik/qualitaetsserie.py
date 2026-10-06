"""Echte Tageslaeufe dokumentieren; KI-Pruefung ist keine menschliche Freigabe.

Keine Netzaufrufe, Uploads oder Aenderung des Versandfilters. Auch Fehlschlaege
bleiben erhalten. Kuratierte Piloten werden hier nicht erfasst.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path

from qualitaet import bewerten

DATEI = Path('verlauf/qualitaetsserie.json')
PRUEFPUNKTE = ('hook', 'spannung', 'bild', 'figur', 'stimme', 'ton', 'cta', 'fakten_technik')


def lesen(pfad, standard=None):
    return json.loads(pfad.read_text(encoding='utf-8')) if pfad.exists() else standard


def speichern(daten, pfad=DATEI):
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix('.tmp')
    tmp.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    tmp.replace(pfad)


def erfassen(kanal, ausgabe=Path('ausgabe'), pfad=DATEI):
    serie = lesen(pfad)
    if not serie or not serie.get('aktiv') or kanal not in serie['kanaele']:
        return None
    if os.environ.get('CF_PILOT') == '1':
        raise ValueError('Kuratierte oder isolierte Piloten zaehlen nicht als Tageslauf')
    run = os.environ.get('GITHUB_RUN_ID')
    attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '1')
    if not run:
        raise ValueError('Echte GitHub-Lauf-ID erforderlich')
    ausgabe = Path(ausgabe)
    bericht = lesen(ausgabe / 'bericht.json', {})
    skript = lesen(ausgabe / 'skript.json', {})
    kritik = lesen(ausgabe / 'kritik.json', {})
    bildplan = lesen(ausgabe / 'bildablauf.json', {})
    video = ausgabe / 'short.mp4'
    sha = None
    if video.is_file():
        with video.open('rb') as f:
            sha = hashlib.file_digest(f, 'sha256').hexdigest()
    version = hashlib.sha256()
    for p in sorted(Path('fabrik').glob('*.py')) + [Path('kanaele') / f'{kanal}.json']:
        if p.is_file():
            version.update(str(p).replace('\\', '/').encode())
            version.update(p.read_bytes())
    _, gruende = bewerten(skript, kritik)
    if not sha:
        gruende.append('Kein fertiges Video vorhanden')
    elif kritik.get('video_sha256') != sha:
        gruende.append('KI-Pruefung gehoert nicht zur vorliegenden Videodatei')
    slots = bildplan.get('einstellungen', [])
    eintrag = {
        'id': f'{run}.{attempt}:{kanal}', 'run_id': run, 'run_attempt': attempt, 'kanal': kanal,
        'datum_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'ereignis': os.environ.get('GITHUB_EVENT_NAME'),
        'commit': os.environ.get('GITHUB_SHA'),
        'produktionsversion': version.hexdigest(),
        'videoformat': skript.get('videoformat', 'short'),
        'thema': skript.get('thema'), 'titel': skript.get('titel'),
        'status': bericht.get('status', 'kein_produktionsbericht'),
        'video_sha256': sha,
        'video_gebaut': bool(sha),
        'ki_story_note': (skript.get('story') or {}).get('note'),
        'ki_video_note': kritik.get('note'),
        'prompt_version': kritik.get('prompt_version'),
        'sperrgruende': gruende,
        'einstellungen': len(slots),
        'unterschiedliche_motive': len({s['material_id'] for s in slots if s.get('material_id')}),
        'sichtpruefung': None,
        'bericht': bericht,
        'ki_pruefung': kritik,
        'faktenpruefung': skript.get('pruefung'),
    }
    for alt in serie['laeufe']:
        if alt['id'] == eintrag['id']:
            if alt['video_sha256'] != sha:
                raise ValueError('Gleiche Lauf-ID mit anderer Videodatei; Sichtpruefung nicht uebernehmen')
            eintrag['sichtpruefung'] = alt.get('sichtpruefung')
            eintrag['datum_utc'] = alt['datum_utc']
    serie['laeufe'] = [e for e in serie['laeufe'] if e['id'] != eintrag['id']] + [eintrag]
    speichern(serie, pfad)
    speichern(eintrag, ausgabe / 'qualitaetsserie.json')
    return eintrag


def bewertung_eintragen(ident, urteil, pfad=DATEI):
    serie = lesen(pfad)
    eintrag = next(e for e in serie['laeufe'] if e['id'] == ident)
    if not eintrag['video_gebaut']:
        raise ValueError('Ohne Video keine Sichtpruefung')
    if urteil.get('video_sha256') != eintrag['video_sha256']:
        raise ValueError('Sichtpruefung muss die konkrete Videodatei benennen')
    for feld in ('vollstaendig_angesehen', 'ohne_nachbearbeitung', 'veroeffentlichbar'):
        if not isinstance(urteil.get(feld), bool):
            raise ValueError(f'{feld}: ausdrueckliches Ja/Nein erforderlich')
    punkte = urteil.get('pruefpunkte', {})
    if any(not isinstance(punkte.get(k), bool) for k in PRUEFPUNKTE):
        raise ValueError('Alle acht Pruefpunkte mit Ja/Nein bewerten')
    note = urteil.get('note')
    if note is not None and (isinstance(note, bool) or not isinstance(note, (int, float))
                             or not math.isfinite(note) or not 1 <= note <= 10):
        raise ValueError('Menschliche Note muss zwischen 1 und 10 liegen oder null sein')
    if not isinstance(urteil.get('pruefer'), str) or not urteil['pruefer'].strip():
        raise ValueError('Menschlichen Pruefer benennen')
    eintrag['sichtpruefung'] = dict(urteil,
        erfasst_am_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    speichern(serie, pfad)


def zusammenfassung(serie):
    ergebnis = {}
    for kanal in serie['kanaele']:
        laeufe = sorted((e for e in serie['laeufe'] if e['kanal'] == kanal
                        and e['videoformat'] == 'short'), key=lambda e: (e['datum_utc'], e['id']))
        folge = 0
        letzte_version = None
        gesehen = set()
        for e in laeufe:
            if e.get('produktionsversion') != letzte_version:
                folge = 0
            letzte_version = e.get('produktionsversion')
            s = e.get('sichtpruefung') or {}
            ok = (e['status'] == 'gesendet' and not e['sperrgruende'] and e['video_gebaut']
                  and e['video_sha256'] not in gesehen
                  and s.get('video_sha256') == e['video_sha256']
                  and all(s.get(k) is True for k in ('vollstaendig_angesehen',
                                                    'ohne_nachbearbeitung', 'veroeffentlichbar'))
                  and all(s.get('pruefpunkte', {}).get(k) is True for k in PRUEFPUNKTE))
            folge = folge + 1 if ok else 0
            if e['video_sha256']:
                gesehen.add(e['video_sha256'])
        ergebnis[kanal] = {
            'laeufe': len(laeufe),
            'videos_gebaut': sum(e['video_gebaut'] for e in laeufe),
            'sichtpruefungen': sum(e.get('sichtpruefung') is not None for e in laeufe),
            'unterschiedliche_videos': len(gesehen),
            'initiale_drei_videos_gebaut': len(gesehen) >= serie['erste_videos_je_kanal'],
            'freigegeben_in_folge': folge,
            'kontrollpunkt_zehn_erreicht': folge >= serie['bestaetigungen_in_folge'],
        }
    # Dieser Kontrollpunkt schaltet keine Plattform-Veroeffentlichung frei.
    return {'kanaele': ergebnis, 'automatischer_plattform_upload': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    befehle = parser.add_subparsers(dest='befehl', required=True)
    p = befehle.add_parser('erfassen')
    p.add_argument('kanal')
    p = befehle.add_parser('bewerten')
    p.add_argument('id')
    p.add_argument('urteil', type=Path)
    befehle.add_parser('status')
    args = parser.parse_args()
    if args.befehl == 'erfassen':
        erfassen(args.kanal)
    elif args.befehl == 'bewerten':
        bewertung_eintragen(args.id, lesen(args.urteil))
    print(json.dumps(zusammenfassung(lesen(DATEI)), indent=2, ensure_ascii=False))
