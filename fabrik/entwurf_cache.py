"""Gepruefte Skripte und Teilbau zwischen Tagesfenstern behalten; maximal sechs Stunden."""
import json, re, shutil, time
from pathlib import Path
import ki_speicher, prompts
from qualitaet import skript_gruende

TTL = 6 * 3600


def pfade(kanal):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', kanal):
        raise ValueError('Ungueltiger Cache-Kanal')
    return Path('verlauf/entwuerfe') / f'{kanal}.json', Path('produktions-cache') / kanal


def profil_key(profil):
    code = Path(__file__).resolve().parent
    return ki_speicher.hashwert([Path(profil).read_text(encoding='utf-8'), prompts.VERSION,
        (code / 'qualitaet.py').read_text(encoding='utf-8'),
        (code / 'zahlen.py').read_text(encoding='utf-8'),
        (code / 'skript.py').read_text(encoding='utf-8')])


def laden(kanal, profil, thema):
    meta, ordner = pfade(kanal)
    try:
        d = json.loads(meta.read_text(encoding='utf-8'))
        s = d['skript']
        if d['version'] != 1 or d['thema_eingabe'] != thema or d['profil'] != profil_key(profil) \
                or not 0 <= time.time() - d['erstellt'] <= TTL or skript_gruende(s) \
                or d['skript_sha'] != ki_speicher.hashwert(s):
            return None
        ordner.mkdir(parents=True, exist_ok=True)
        (ordner / 'skript.json').write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        return ordner
    except (OSError, ValueError, KeyError, TypeError):
        return None


def sichern(kanal, profil, thema, ordner):
    meta, ziel = pfade(kanal)
    s = json.loads((Path(ordner) / 'skript.json').read_text(encoding='utf-8'))
    if skript_gruende(s):
        return False
    alt = ki_speicher.lesen_json(meta)
    sha = ki_speicher.hashwert(s)
    pruef_sha = ki_speicher.hashwert([s.get('thema'), s.get('titel'),
        [t['text'] for t in s['teile']], s.get('quellen'), s.get('belege'),
        s.get('pruefung'), s.get('story')])
    # Wiederholter Bau verlaengert die Gueltigkeit einer alten Pruefung nicht.
    erstellt = alt['erstellt'] if alt.get('pruef_sha') == pruef_sha and alt.get('erstellt') else time.time()
    ki_speicher.speichern(meta, {'version': 1, 'profil': profil_key(profil),
        'thema_eingabe': thema, 'erstellt': erstellt, 'skript_sha': sha,
        'pruef_sha': pruef_sha, 'skript': s})
    if Path(ordner).resolve() != ziel.resolve():
        ziel.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ordner, ziel, dirs_exist_ok=True)
    return True


def erledigen(kanal):
    meta, _ = pfade(kanal)
    meta.unlink(missing_ok=True)
