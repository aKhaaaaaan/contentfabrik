"""Docling-Bildkorrektur ohne neue Stimme; Originalton und Overlays erhalten."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import bildplan
import docling_bildfolge
import ki_speicher


def audiohash(video):
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-map', '0:a:0',
                           '-c:a', 'copy', '-f', 'hash', '-hash', 'sha256', '-'],
                          check=True, capture_output=True, text=True, timeout=60).stdout.strip()


def korrigieren(original, ausgabe):
    src, out = Path(original).resolve(), Path(ausgabe).resolve()
    if src == out:
        raise ValueError('Korrektur darf das Original nicht ueberschreiben')
    s = ki_speicher.lesen_json(src / 'skript.json')
    k = ki_speicher.lesen_json(src / 'kritik.json')
    a = ki_speicher.lesen_json(src / 'bildablauf.json')
    video = src / 'short.mp4'
    sha = bildplan.material_id(video)
    if s.get('kanal') != 'AI Tools Explained' or k.get('video_sha256') != sha:
        raise ValueError('Docling-Korrektur braucht das zugeordnete Original')
    docling_bildfolge.bildfolge(s)
    slots = a.get('einstellungen', [])
    phases = [0,0,0,1,1,1,2,2,2,3,3,4,4,4,5,5,5,6]
    # Diese quellengebundene Regie gilt nur fuer diese konkrete Erklaerung.
    expected = ['PDF','copying','documented','layouts','exports','Markdown','Python package',
                'DocumentConverter','PDF','Markdown','command-line','OCR','scanned','sensitive',
                'installation','structured','AI workflows','Like']
    if len(slots) != 18 or [t.get('phase') for t in slots] != phases or \
            any(t.get('index') != i or expected[i].lower() not in
                (t.get('text', '') + ' ' + t.get('phase_text', '')).lower()
                for i,t in enumerate(slots)):
        raise ValueError('Docling-Regie passt nicht zu diesem Sprechtext')
    duration = slots[-1]['s'] + slots[-1]['dauer_s']
    if not 35 <= duration <= 45.1 or bildplan.pruefen(a, duration, 'short')['befunde']:
        raise ValueError('Original-Bildablauf ungueltig')
    out.mkdir(parents=True, exist_ok=True)
    start = time.monotonic(); lines = []
    for t in slots:
        i = t['index']; im = docling_bildfolge.grafik(out / f'g{i:02d}.jpg', i)
        frames = round((t['s'] + t['dauer_s']) * 30) - round(t['s'] * 30)
        clip = out / f'g{i:02d}.mp4'
        # Leichte Kamerabewegung plus nacheinander markierte Erklaerschritte.
        # Keine fingierten Programm-Ergebnisse oder Installationsfortschritte.
        regions = ([(65,320,350,475),(545,320,350,475)] if i in (0,1,2,4,5,8,12,15) else
                   [(85,355,780,100),(85,510,780,215)] if i in (6,7,9,10,14) else
                   [(70,330,345,430),(510,380,370,390)] if i in (3,11,13,16) else
                   [(55,370,230,350),(365,370,230,350),(675,370,230,350)])
        effects = [f"zoompan=z='1+0.04*on/{frames}':x='iw/2-iw/zoom/2':"
                   "y='ih/2-ih/zoom/2':d=1:s=960x1040:fps=30"]
        for n,(x,y,w,h) in enumerate(regions):
            begin = t['dauer_s'] * n / len(regions)
            end = t['dauer_s'] * (n+1) / len(regions)
            effects.append(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=0x20d2be@0.8:t=5:"
                           f"enable='between(t,{begin:.3f},{end:.3f})'")
        subprocess.run(['ffmpeg','-y','-v','error','-loop','1','-i',str(im),'-frames:v',str(frames),
                        '-vf',','.join(effects),'-r','30','-an','-c:v','libx264','-preset','veryfast','-crf','18',
                        '-pix_fmt','yuv420p',str(clip)],check=True,timeout=120)
        lines.append(f"file '{clip.name}'")
        t.update(material_id=bildplan.material_id(im), material_art='grafik')
    (out / 'guide-list.txt').write_text('\n'.join(lines),encoding='utf-8')
    figure = Path(__file__).resolve().parents[1] / 'figuren/ai-tools-explained.jpg'
    cta_start = slots[-1]['s']
    filters = ("[0:v][1:v]overlay=60:280:shortest=1[main];[2:v]scale=150:266[host];"
               f"[main][host]overlay=850:1040:enable='between(t,0,{slots[2]['s']+slots[2]['dauer_s']:.3f})"
               f"+between(t,{cta_start:.3f},{duration:.3f})'[v]")
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(video),'-f','concat','-safe','0','-i','guide-list.txt',
                    '-loop','1','-i',str(figure),'-filter_complex',filters,'-map','[v]','-map','0:a',
                    '-c:v','libx264','-preset','veryfast','-crf','18','-c:a','copy','-t',str(duration),
                    '-r','30','-movflags','+faststart','short.mp4'],check=True,cwd=out,timeout=300)
    audio_same = audiohash(video) == audiohash(out / 'short.mp4')
    if not audio_same:
        raise ValueError('Tonspur durch Bildkorrektur veraendert')
    ki_speicher.speichern(out / 'skript.json', s)
    ki_speicher.speichern(out / 'bildablauf.json', a)
    sources = json.loads((src / 'quellen.json').read_text(encoding='utf-8'))
    if not isinstance(sources,list):
        raise ValueError('Quellenliste fehlt')
    sources.append({'quelle':'Dokumentationsgrafik','seite':docling_bildfolge.SOURCE,
                    'hinweis':'Illustrative diagram; no measured Docling results.'})
    ki_speicher.speichern(out / 'quellen.json', sources)
    ki_speicher.speichern(out / 'korrektur-nachweis.json', {
        'original_sha256':sha, 'video_sha256':bildplan.material_id(out / 'short.mp4'),
        'audio_unveraendert':True, 'einstellungen':18, 'renderzeit_s':round(time.monotonic()-start,2),
        'bewegte_hervorhebungen':True,
        'quelle':docling_bildfolge.SOURCE})
    # Alte Video-/ASR-Noten werden nicht auf eine neue Datei umgeschrieben.
    return s


def main(original, ausgabe):
    import budget
    import kritik
    import freigabe
    from lauf import BUDGET_S
    from qualitaet import bewerten
    slug = 'ai-tools-explained'
    if budget.rest(slug, BUDGET_S) < 600:
        raise RuntimeError('Tagesbudget reicht nicht fuer Bildkorrektur und echte Neupruefung')
    reservation = budget.reservieren(slug, BUDGET_S)
    start = time.monotonic()
    os.environ['CF_SCHRITT_ENDE'] = str(start + min(1200, reservation[0]) - 180)
    status = 'fehlgeschlagen'
    try:
        s = korrigieren(original, ausgabe)
        out = Path(ausgabe)
        k = kritik.kritik(str(out/'short.mp4'), str(out/'skript.json'), str(out/'kritik.json'))
        _, reasons = bewerten(s,k)
        if reasons:
            status = 'gesperrt'
            raise RuntimeError('Neue Bildkorrektur besteht die Freigabegates nicht')
        freigabe.senden(str(out/'skript.json'), str(out/'short.mp4'))
        status = 'gesendet'
    finally:
        seconds = time.monotonic()-start
        budget.abschliessen(slug,reservation,seconds)
        ki_speicher.speichern(Path(ausgabe)/'bericht.json',{
            'kanal':slug,'datum':budget.heute(),'status':status,'sekunden':round(seconds,2),'runden':[]})


if __name__ == '__main__':
    main(sys.argv[1],sys.argv[2])
