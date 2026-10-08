"""Skript-Vorrat: Skripte VORHER schreiben und pruefen, der Videolauf baut nur noch.

GEMELDET 07.10.2026: „Schreib doch die Skripte immer vorher und lass die in der
Pipeline, bis das Generieren bereit ist, geprueft warten."
GEMESSEN 07.10.2026: Skriptphase verbrauchte bis zu 1620 s Tagesbudget (AI);
Lauf 37659694533 fand Claude am Abo-Limit, weil Pipeline und interaktive
Sitzungen dasselbe Kontingent teilen. Nachts (skripte.yml) ist es frei.

Ablage vorrat/<kanal>/<id>.json (im Repo gesichert). Ein Eintrag wird nur mit
bestandener Fakten- und Story-Pruefung (skript.py Exit 0, skript_gruende leer)
aufgenommen und erst nach erfolgreichem Versand entfernt; ein Baufehler behaelt
ihn. Vor der Nutzung wird erneut geprueft (Alter, Gates) - nichts wird blind gebaut.
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ORDNER = Path('vorrat')
ZIEL = 2  # fertige Skripte je Kanal
# Unternehmensgeschichten veralten kaum; KI-Werkzeuge schnell (neue Versionen/Preise).
MAX_TAGE = {'geschichte': 14}
MAX_TAGE_STANDARD = 3


def _kanal_daten(kanal_pfad):
    import kanalstandard
    return kanalstandard.laden(kanal_pfad)


def _max_tage(daten):
    return MAX_TAGE.get(daten.get('format'), MAX_TAGE_STANDARD)


def eintraege(kanal):
    ordner = ORDNER / kanal
    if not ordner.is_dir():
        return []
    liste = []
    for p in sorted(ordner.glob('*.json')):
        try:
            liste.append((p, json.loads(p.read_text(encoding='utf-8'))))
        except (OSError, ValueError):
            continue
    return sorted(liste, key=lambda x: x[1].get('erstellt_utc', ''))


def gueltig(eintrag, daten, jetzt=None):
    from qualitaet import skript_gruende
    jetzt = jetzt or datetime.datetime.now(datetime.timezone.utc)
    try:
        alter = jetzt - datetime.datetime.fromisoformat(eintrag['erstellt_utc'])
        s = eintrag['skript']
        # Laengengrenze der aktuellen Erzaehlstimme (z. B. Orus ~2 W/s): ein vorher fuer
        # Kokoro geschriebenes Skript wuerde zu lang (GEMESSEN 08.10.: 207 Woerter = 109 s).
        import dramaturgie, skript as skriptmodul
        # GEFUNDEN 08.10.: Short und Langvideo teilen den Vorrat-Ordner (gleicher Slug) -
        # der Langvideo-Pilot haette ein 180-Woerter-Short-Skript gebaut.
        if dramaturgie.videoformat(s) != dramaturgie.videoformat(daten):
            return False
        if dramaturgie.videoformat(daten) == 'short' and sum(len(t['text'].split()) for t in s['teile']) \
                > int(dramaturgie.laengen(daten)[1] * skriptmodul.wortrate(daten)):
            return False
        return (datetime.timedelta(0) <= alter <= datetime.timedelta(days=_max_tage(daten))
                and s.get('pruefung', {}).get('ok') is True and not skript_gruende(s))
    except (KeyError, TypeError, ValueError):
        return False


def nehmen(kanal_pfad, thema=''):
    """Pfad eines Ordners mit skript.json fuer den Videolauf, oder None.

    Mit Thema (Warteschlange/Telegram) nur das passende Skript; ohne Thema nur frei
    gewaehlte - sonst wuerde ein spaeter geplantes Nutzerthema vorzeitig gebaut und
    bliebe trotzdem in der Warteschlange (doppeltes Video).
    """
    kanal = Path(kanal_pfad).stem
    daten = _kanal_daten(kanal_pfad)
    for pfad, e in eintraege(kanal):
        if (e.get('thema_eingabe') or '') == (thema or '') and gueltig(e, daten):
            ziel = Path('vorrat-nutzung') / kanal
            shutil.rmtree(ziel, ignore_errors=True)
            ziel.mkdir(parents=True)
            (ziel / 'skript.json').write_text(json.dumps(e['skript'], ensure_ascii=False), encoding='utf-8')
            print(f'Skript aus dem Vorrat: {e.get("thema_eingabe") or e["skript"].get("thema")} '
                  f'(geschrieben {e["erstellt_utc"][:16]}, {e.get("modell", "?")})')
            return ziel
    return None


def erledigen(kanal, skript):
    """Nach erfolgreichem Versand: genau den gebauten Vorratseintrag entfernen."""
    for pfad, e in eintraege(kanal):
        if e.get('skript', {}).get('thema') == skript.get('thema') and \
                [t.get('text') for t in e['skript'].get('teile', [])] == [t.get('text') for t in skript.get('teile', [])]:
            pfad.unlink(missing_ok=True)


def aufraeumen(kanal_pfad):
    kanal = Path(kanal_pfad).stem
    daten = _kanal_daten(kanal_pfad)
    for pfad, e in eintraege(kanal):
        if not gueltig(e, daten):
            print('Vorrat: abgelaufen/ungueltig entfernt:', pfad.name)
            pfad.unlink(missing_ok=True)


def offene_themen(kanal):
    """Naechste Warteschlangen-Themen ohne Vorratsskript (auch spaeter geplante)."""
    import themen
    vorhanden = {e.get('thema_eingabe') for _, e in eintraege(kanal)}
    return [x['thema'] for x in themen.laden() if x['kanal'] == kanal
            and x.get('status', 'bereit') == 'bereit' and x['thema'] not in vorhanden]


def fuellen(kanal_pfad, frist_s=1500):
    """Bis ZIEL Skripte schreiben und pruefen. Gibt die Zahl neuer Eintraege zurueck."""
    import time
    kanal = Path(kanal_pfad).stem
    aufraeumen(kanal_pfad)
    ende = time.monotonic() + frist_s
    neu = 0
    themenliste = offene_themen(kanal)
    while len(eintraege(kanal)) < ZIEL and time.monotonic() + 300 < ende:
        # Ohne Warteschlangen-Thema waehlt skript.py selbst (AI-Kanal: aktuelle Werkzeuge).
        thema = themenliste.pop(0) if themenliste else ''
        if not thema and any(not e.get('thema_eingabe') for _, e in eintraege(kanal)):
            break  # ein frei gewaehltes Skript genuegt; Warteschlange hat Vorrang
        ziel = Path('vorrat-arbeit') / kanal / 'skript.json'
        shutil.rmtree(ziel.parent, ignore_errors=True)
        ziel.parent.mkdir(parents=True)
        print(f'Vorrat {kanal}: schreibe {thema or "(frei gewaehlt)"}', flush=True)
        try:
            r = subprocess.run([sys.executable, 'fabrik/skript.py', kanal_pfad, str(ziel), thema],
                               timeout=max(60, min(900, ende - time.monotonic()))).returncode
        except subprocess.TimeoutExpired:
            print('Vorrat: Zeitlimit beim Schreiben')
            break
        if r != 0 or not ziel.exists():
            print(f'Vorrat: Skript nicht aufgenommen (Code {r})')
            if not thema:
                break
            continue
        s = json.loads(ziel.read_text(encoding='utf-8'))
        e = {'thema_eingabe': thema, 'erstellt_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'modell': s.get('modell'), 'story_note': (s.get('story') or {}).get('note'), 'skript': s}
        if not gueltig(e, _kanal_daten(kanal_pfad)):
            print('Vorrat: Pruefungen nicht bestanden - nicht aufgenommen')
            continue
        kennung = hashlib.sha256((thema or s.get('thema', '')).encode()).hexdigest()[:12]
        name = re.sub(r'[^a-z0-9]+', '-', (s.get('thema') or 'skript').lower())[:40].strip('-')
        (ORDNER / kanal).mkdir(parents=True, exist_ok=True)
        (ORDNER / kanal / f'{name}-{kennung}.json').write_text(
            json.dumps(e, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        neu += 1
        print(f'Vorrat {kanal}: aufgenommen ({s.get("modell")}, Story {e["story_note"]}/10)')
    return neu


if __name__ == '__main__':
    gesamt = 0
    for pfad in sys.argv[1:] or sorted(str(p) for p in Path('kanaele').glob('*.json')):
        gesamt += fuellen(pfad, int(os.environ.get('CF_VORRAT_FRIST', '1500')))
    print('Neue Vorratsskripte:', gesamt)
