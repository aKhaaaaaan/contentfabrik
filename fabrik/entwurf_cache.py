"""Gepruefte Skripte und Teilbau zwischen Tagesfenstern behalten; maximal sechs Stunden."""
import json, re, shutil, time
from pathlib import Path
import ki_speicher, prompts
from qualitaet import skript_gruende

TTL = 6 * 3600
# GEMESSEN 17.10.2026: das Langvideo (Sa, Ersatztermin So) verlor sein geprueftes Skript nach 6 h - der
# Sonntag haette Skript und bezahlte Stimme neu erzeugt. Firmengeschichten veralten nicht ueber Nacht.
TTL_LANG = 48 * 3600


def cache_name(kanal, profil):
    """Eigener Cache-Platz fuers Langvideo ('<kanal>-lang'), damit Short und Langvideo sich nicht ueberschreiben."""
    try:
        lang = json.loads(Path(profil).read_text(encoding='utf-8')).get('videoformat') == 'lang'
    except (OSError, ValueError):
        lang = False
    return f'{kanal}-lang' if lang else kanal


def pfade(kanal):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', kanal):
        raise ValueError('Ungueltiger Cache-Kanal')
    # Nur der Eintrag in Git ist geteilt; der Teilbau-Ordner bleibt (eigener GitHub-Cache je Workflow,
    # ein neuer Pfad haette den vorhandenen Langvideo-Teilbau samt bezahlter Stimme unlesbar gemacht).
    return Path('verlauf/entwuerfe') / f'{kanal}.json', Path('produktions-cache') / kanal.removesuffix('-lang')


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
        import trends
        profil_daten = json.loads(Path(profil).read_text(encoding='utf-8'))
        if not thema and profil_daten.get('nur_quellen') and trends.bereits_gezeigte_quellen(kanal, s):
            return None
        if d['version'] != 1 or d['thema_eingabe'] != thema or d['profil'] != profil_key(profil) \
                or not 0 <= time.time() - d['erstellt'] <= (TTL_LANG if kanal.endswith('-lang') else TTL) or skript_gruende(s) \
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


# Nutzerentscheidung 17.10.2026 (wortgenau): "wenn bereits Bilder generiert werden fuer ein bestimmtes Thema und
# irgendwann durchfaellt, sollte nicht von vorne angefangen werden ... Wenn alle Bilder erfolgreich erstellt wurden
# und das Thema durch ist, dann kann es geloescht werden. Auch nur dann, wenn mir Skript und Video gefaellt und ich
# den Passt-Knopf auf Telegram druecke, dass es als Entwurf auf TikTok landet."
BILDER_HOECHSTENS_TAGE = 30  # Speicherschutz fuer Themen ohne TikTok-Knopf (Langvideo) oder ohne Klick


def bildspeicher_name(thema):
    """Ordnername je Thema: lesbar plus kurzer Hash (gleiches Thema -> gleicher Ordner)."""
    thema = str(thema or '').strip()
    lesbar = re.sub(r'[^a-z0-9]+', '-', thema.lower()).strip('-')[:50] or 'ohne-thema'
    return f"{lesbar}-{ki_speicher.hashwert(thema)[:8]}"


def bildspeicher(kanal):
    """Basisordner der geprueften Bilder je Thema (liegt im Teilbau, also im GitHub-Cache des Workflows)."""
    return pfade(kanal)[1] / 'bilder'


def freigegebene_themen(kanal_name=None):
    """Themen, deren Video der Nutzer per Telegram fuer TikTok freigegeben hat."""
    try:
        freigaben = {x.get('video_sha256') for x in json.loads(
            Path('verlauf/tiktok-freigaben.json').read_text(encoding='utf-8')) if isinstance(x, dict)}
        videos = json.loads(Path('verlauf/telegram-videos.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return set()
    return {v['thema'] for v in videos if isinstance(v, dict) and v.get('thema')
            and v.get('video_sha256') in freigaben and (kanal_name is None or v.get('kanal') == kanal_name)}


def bilder_aufraeumen(kanal, jetzt=None):
    """Bilder eines Themas erst nach der TikTok-Freigabe loeschen (sonst nach 30 Tagen). Gibt geloeschte Namen."""
    basis = bildspeicher(kanal)
    if not basis.is_dir():
        return []
    fertig = {bildspeicher_name(t) for t in freigegebene_themen()}
    grenze = (jetzt or time.time()) - BILDER_HOECHSTENS_TAGE * 86400
    weg = []
    for ordner in basis.iterdir():
        if ordner.is_dir() and (ordner.name in fertig or ordner.stat().st_mtime < grenze):
            shutil.rmtree(ordner, ignore_errors=True)
            weg.append(ordner.name)
    return weg
