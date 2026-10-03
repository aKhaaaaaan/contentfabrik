"""KI-Kritik: Gemini sieht sich das FERTIGE Video an und bewertet es.

GEMELDET: Der Nutzer liess jedes Video von Hand von Gemini Flash bewerten
(„Ich muss es staendig machen"). Jetzt passiert das automatisch nach dem Bauen;
das Ergebnis steht in der Telegram-Nachricht und in ausgabe/kritik.json.

Offizieller Weg: Gemini Files API (Video hochladen, warten bis ACTIVE, dann
generateContent mit file_data). Hochgeladene Dateien loescht das Skript danach.

Aufruf:  python fabrik/kritik.py ausgabe/short.mp4 ausgabe/skript.json ausgabe/kritik.json
"""
import json, os, sys, time, urllib.request
from pathlib import Path

from skript import gemini

BASIS = 'https://generativelanguage.googleapis.com'

# Pruefliste (Nutzer: „komplett nach Qualitaet und Standard pruefen"); jede
# Kategorie 1-10. Technisches misst der Code selbst (technik()), das kann
# Gemini aus dem Bild nicht verlaesslich.
KATEGORIEN = {
    'hook': 'first 1-3 seconds: would a scrolling viewer stop?',
    'bild_passt': 'do the visuals match what is said at every moment?',
    'dynamik': 'motion, cuts, no static or empty screens',
    'text': 'on-screen text and subtitles: readable, no overlaps, not jumping, inside the safe zone '
            '(not hidden by the platform buttons at the bottom and right)',
    'ton_stimme': 'voice clarity and naturalness, volume, no glitches',
    'tempo': 'pacing, no dead moments, no rushed parts',
    'inhalt': 'value for a normal viewer, facts look plausible, no hype claims',
    'schluss_loop': 'ending and loop into the start, call to action',
    'regeln': 'platform rules: no copyrighted material visible, no misleading claims, safe for ads',
}


def technik(video):
    """Harte Fakten per ffprobe/ffmpeg - Plattform-Standard fuer Shorts/TikTok."""
    import subprocess, re
    befunde = []
    try:
        info = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json',
                                          video], capture_output=True, text=True, check=True).stdout)
        v = next(x for x in info['streams'] if x['codec_type'] == 'video')
        a = next((x for x in info['streams'] if x['codec_type'] == 'audio'), None)
        dauer = float(info['format']['duration'])
        fps = eval(v.get('avg_frame_rate', '0/1').replace('/', '/max(1,') + ')')
        if (v['width'], v['height']) != (1080, 1920):
            befunde.append(f"Aufloesung {v['width']}x{v['height']} statt 1080x1920")
        if v.get('codec_name') != 'h264':
            befunde.append(f"Video-Codec {v.get('codec_name')} statt H.264")
        if not 23 <= fps <= 61:
            befunde.append(f'Bildrate {fps:.1f} fps')
        if not a:
            befunde.append('keine Tonspur')
        elif a.get('codec_name') != 'aac' or int(a.get('sample_rate', 0)) != 48000 or a.get('channels') != 2:
            befunde.append(f"Ton {a.get('codec_name')} {a.get('sample_rate')} Hz {a.get('channels')} Kanaele "
                           '(Soll: AAC 48 kHz Stereo - sonst Handy-Player stumm, gemessen)')
        if dauer <= 61:
            befunde.append(f'nur {dauer:.1f} s - unter 61 s keine TikTok-Verguetung')
        if dauer > 180:
            befunde.append(f'{dauer:.0f} s - laenger als ein Short (3 Min.)')
        laut = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', video, '-af', 'ebur128', '-f', 'null', '-'],
                              capture_output=True, text=True).stderr
        m = re.findall(r'I:\s+(-?[\d.]+) LUFS', laut)
        if m and not -16.5 <= float(m[-1]) <= -11.5:
            befunde.append(f'Lautheit {m[-1]} LUFS (Soll um -14)')
        return {'dauer_s': round(dauer, 1), 'fps': round(fps, 1), 'lufs': float(m[-1]) if m else None,
                'befunde': befunde}
    except Exception as e:
        return {'befunde': [f'Technik-Pruefung nicht moeglich: {str(e)[:120]}']}

SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'note': {'type': 'INTEGER'},
        'kategorien': {'type': 'OBJECT', 'properties': {k: {'type': 'INTEGER'} for k in KATEGORIEN},
                       'required': list(KATEGORIEN)},
        'staerken': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'probleme': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
            'zeit': {'type': 'STRING'},
            'art': {'type': 'STRING', 'enum': ['bild_passt_nicht', 'leeres_bild', 'standbild', 'text', 'ton',
                                                'stimme', 'tempo', 'hook', 'sonstiges']},
            'text': {'type': 'STRING'}}, 'required': ['zeit', 'art', 'text']}},
        'fazit': {'type': 'STRING'},
    },
    'required': ['note', 'staerken', 'probleme', 'fazit'],
}


def hochladen(pfad, schluessel):
    daten = Path(pfad).read_bytes()
    start = urllib.request.Request(
        f'{BASIS}/upload/v1beta/files?key={schluessel}', method='POST',
        data=json.dumps({'file': {'display_name': Path(pfad).name}}).encode(),
        headers={'X-Goog-Upload-Protocol': 'resumable', 'X-Goog-Upload-Command': 'start',
                 'X-Goog-Upload-Header-Content-Length': str(len(daten)),
                 'X-Goog-Upload-Header-Content-Type': 'video/mp4', 'Content-Type': 'application/json'})
    ziel = urllib.request.urlopen(start, timeout=60).headers['X-Goog-Upload-URL']
    datei = json.load(urllib.request.urlopen(urllib.request.Request(
        ziel, data=daten, method='POST',
        headers={'X-Goog-Upload-Command': 'upload, finalize', 'X-Goog-Upload-Offset': '0'}), timeout=600))['file']
    # Gemini verarbeitet Videos erst - bis dahin ist die Datei nicht nutzbar
    for _ in range(60):
        if datei.get('state') == 'ACTIVE':
            return datei
        if datei.get('state') == 'FAILED':
            raise RuntimeError('Gemini konnte das Video nicht verarbeiten')
        time.sleep(5)
        datei = json.load(urllib.request.urlopen(f"{BASIS}/v1beta/{datei['name']}?key={schluessel}", timeout=30))
    raise RuntimeError('Gemini-Verarbeitung dauerte zu lange')


def kritik(video, skript_pfad, aus):
    schluessel = os.environ['GEMINI_API_KEY']
    skript = json.loads(Path(skript_pfad).read_text(encoding='utf-8'))
    datei = None
    try:
        datei = hochladen(video, schluessel)
        ergebnis, modell = gemini(
            'You are a strict, experienced YouTube Shorts / TikTok editor and quality inspector. Watch this '
            f'complete faceless short (channel "{skript["kanal"]}", topic "{skript["thema"]}") as a normal '
            'viewer would, from first to last frame. Rate each category 1-10:\n'
            + '\n'.join(f'- {k}: {v}' for k, v in KATEGORIEN.items())
            + '\nThen an overall "note" 1-10 (8+ = ready to publish). List EVERY concrete problem with its '
            'timestamp (mm:ss), and real strengths. Be specific and honest, no generic advice. Answer in German.',
            SCHEMA, temperatur=0.2, dateien=[('video/mp4', datei['uri'])])
    finally:
        if datei:  # aufraeumen - nichts bleibt bei Google liegen
            try:
                urllib.request.urlopen(urllib.request.Request(
                    f"{BASIS}/v1beta/{datei['name']}?key={schluessel}", method='DELETE'), timeout=30)
            except Exception:
                pass
    ergebnis['modell'] = modell
    ergebnis['technik'] = technik(video)
    Path(aus).write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"KI-Kritik: {ergebnis['note']}/10 - {ergebnis['fazit']}")
    print('  Kategorien:', ergebnis.get('kategorien'))
    print('  Technik:', ergebnis['technik'])
    for p in ergebnis['probleme']:
        print(f"  {p['zeit']} [{p['art']}] {p['text']}")
    return ergebnis


if __name__ == '__main__':
    kritik(sys.argv[1], sys.argv[2], sys.argv[3])
