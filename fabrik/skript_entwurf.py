"""Ungepruefte Autorenarbeit fortsetzen; niemals als freigegebenes Skript verwenden."""
import time
from pathlib import Path
import ki_speicher
import prompts

TTL = 6 * 3600


def pfad(profil):
    return Path('verlauf/skript-entwuerfe') / (Path(profil).stem + '.json')


def kontext(profil, thema, quellen, schema):
    return ki_speicher.hashwert([Path(profil).read_text(encoding='utf-8'), thema,
        sorted(q.get('url', '') for q in quellen), schema, prompts.VERSION])


def laden(profil, thema, quellen, schema):
    d = ki_speicher.lesen_json(pfad(profil))
    try:
        e = d['entwurf']
        if d.get('version') == 1 and d.get('status') == 'ungeprueft' \
                and d['kontext'] == kontext(profil, thema, quellen, schema) \
                and 0 <= time.time() - d['zeit'] < TTL and ki_speicher.schema_ok(e, schema) \
                and d['sha'] == ki_speicher.hashwert(e) and isinstance(d['modell'], str):
            return e, d['modell']
    except (KeyError, TypeError, ValueError, OSError):
        pass
    return None


def sichern(profil, thema, quellen, schema, entwurf, modell):
    if not ki_speicher.schema_ok(entwurf, schema):
        return False
    ki_speicher.speichern(pfad(profil), {'version': 1, 'status': 'ungeprueft', 'zeit': time.time(),
        'kontext': kontext(profil, thema, quellen, schema), 'entwurf': entwurf, 'modell': modell,
        'sha': ki_speicher.hashwert(entwurf)})
    return True


def erledigen(profil):
    pfad(profil).unlink(missing_ok=True)
