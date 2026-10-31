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
        # GEMESSEN 28.10.2026 (Lauf 40687018472): nach der Hook-Umstellung (prompts.VERSION 2026-10-28.1) baute
        # der Abendtest das Vorrat-Skript von 05:17 mit dem alten Hook - kein Unterschied sichtbar. Der
        # Entwurfscache verwirft bei neuer Version; der Vorrat jetzt ebenso.
        import prompts
        if eintrag.get('prompts') != prompts.VERSION:
            return False
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


def wiederholung(kanal, eintrag):
    """Frei gewaehltes Skript zu einem schon gelieferten Thema (GEMESSEN 21.10.2026: Ford zum zweiten Mal,
    zuerst 18.10. - Claude bekommt die frueheren Themen nur als Bitte)."""
    if eintrag.get('thema_eingabe'):
        return False  # ausdrueckliches Nutzer-/Trendthema entscheidet selbst
    import themen
    s = eintrag.get('skript') or {}
    return bool(themen.wiederholung_gesperrt(kanal, s.get('thema'), s.get('titel')))


def bereit(kanal_pfad):
    """thema_eingabe des aeltesten nutzbaren Vorratsskripts ('' = frei gewaehlt) oder None.

    GEMESSEN 15.10.2026 (Lauf 38703468700): Der Trend-Check waehlte Enron ohne Skript; Claude schrieb
    fuenfmal Story 5-6 und der Lauf scheiterte, waehrend das gepruefte Coca-Cola-Skript (Story 8)
    ungenutzt blieb. Die Nachtlaeufe schreiben bereits in Trend-Reihenfolge.
    """
    kanal = Path(kanal_pfad).stem
    daten = _kanal_daten(kanal_pfad)
    try:
        import themen
        offen = {x['thema'] for x in themen.laden() if x.get('kanal') == kanal
                 and x.get('status', 'bereit') == 'bereit'}
    except Exception:
        return None
    import trendcheck
    trend = trendcheck.zuschauer_themen_der_tage(kanal, MAX_TAGE_STANDARD)
    offen |= trend
    # Ein Zuschauer-Trendskript vor einem frei gewaehlten (GitHub-Neuheit) bauen, auch wenn es juenger ist.
    for _, e in sorted(eintraege(kanal), key=lambda x: (x[1].get('thema_eingabe') or '') not in trend):
        thema = e.get('thema_eingabe') or ''
        if not gueltig(e, daten) or (thema and thema not in offen) or wiederholung(kanal, e):
            continue
        if not thema and daten.get('nur_quellen'):
            import trends
            if trends.bereits_gezeigte_quellen(kanal, e['skript']):
                continue
        return thema
    return None


def nehmen(kanal_pfad, thema=''):
    """Pfad eines Ordners mit skript.json fuer den Videolauf, oder None.

    Mit Thema (Warteschlange/Telegram) nur das passende Skript; ohne Thema nur frei
    gewaehlte - sonst wuerde ein spaeter geplantes Nutzerthema vorzeitig gebaut und
    bliebe trotzdem in der Warteschlange (doppeltes Video).
    """
    kanal = Path(kanal_pfad).stem
    daten = _kanal_daten(kanal_pfad)
    for pfad, e in eintraege(kanal):
        if (e.get('thema_eingabe') or '') == (thema or '') and gueltig(e, daten) and not wiederholung(kanal, e):
            import trends
            if not thema and daten.get('nur_quellen') and trends.bereits_gezeigte_quellen(kanal, e['skript']):
                print('Vorrat uebersprungen: Quelle bereits gesendet:', e['skript'].get('thema'))
                continue
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
        elif wiederholung(kanal, e):
            print('Vorrat: Thema schon geliefert, entfernt:', pfad.name)
            pfad.unlink(missing_ok=True)
    # GEMESSEN 14.10.2026: Verbrauchte Eintraege blockierten das Nachfuellen. Yahoo stand nicht
    # mehr in der Warteschlange (nie nutzbar, Enron bekam kein Skript); das gesendete Floe Guard
    # zaehlte als "frei gewaehltes Skript vorhanden" und verhinderte jedes neue.
    try:
        import themen
        offen = {x['thema'] for x in themen.laden() if x.get('kanal') == kanal
                 and x.get('status', 'bereit') in ('bereit', 'recherche')}
        # GEMESSEN 21.10.2026 (Lauf 39547556512): Das Zuschauer-Trendthema steht in keiner Warteschlange -
        # der 05:05-Lauf loeschte das gepruefte Gemini-Skript (Story 8) von 01:05 und schrieb neu: Story 5,
        # gesperrt. bereit() kennt diese Themen schon, aufraeumen() muss dieselben behalten.
        import trendcheck
        offen |= trendcheck.zuschauer_themen_der_tage(kanal, MAX_TAGE_STANDARD)
    except Exception as fehler:
        print('Vorrat: Warteschlange nicht lesbar, nichts entfernt:', type(fehler).__name__)
        return
    for pfad, e in eintraege(kanal):
        thema = e.get('thema_eingabe') or ''
        if thema and thema not in offen:
            print('Vorrat: Thema nicht mehr in der Warteschlange, entfernt:', pfad.name)
            pfad.unlink(missing_ok=True)
        elif not thema and _zuschauer_trends(kanal):
            # 22.10.2026: frei gewaehltes GitHub-Skript („HaozheH3/awesome-rea-games") lag neben dem Trendskript.
            # Kanaele mit Zuschauer-Trends nehmen nur Trendthemen; ohne Trend waehlt der Tageslauf selbst neu.
            print('Vorrat: frei gewaehltes Thema bei Trend-Kanal entfernt:', pfad.name)
            pfad.unlink(missing_ok=True)
        elif not thema and daten.get('nur_quellen'):
            import trends
            if trends.bereits_gezeigte_quellen(kanal, e.get('skript', {})):
                print('Vorrat: Quelle bereits gesendet, entfernt:', pfad.name)
                pfad.unlink(missing_ok=True)


# GEMESSEN 31.10.2026 (skripte.yml 41153564650/41171142835/41178202588): drei Nachtlaeufe versuchten dieselben drei
# KI-Trendthemen (Story 3-7, Code 3) und ExxonMobil (Quelle zu kurz) - 0 Skripte, tagsueber dann Live-Schreiben.
GESCHEITERT = Path('verlauf/vorrat-gescheitert')
GESCHEITERT_TAGE = 3


def gescheitert(kanal, heute=None):
    """Themen, deren Vorratsskript in den letzten GESCHEITERT_TAGE Tagen durchfiel."""
    heute = heute or datetime.date.today()
    try:
        liste = json.loads((GESCHEITERT / f'{kanal}.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return set()
    return {x['thema'] for x in liste if 0 <= (heute - datetime.date.fromisoformat(x['datum'])).days
            < GESCHEITERT_TAGE}


def gescheitert_merken(kanal, thema, code, heute=None):
    heute = heute or datetime.date.today()
    pfad = GESCHEITERT / f'{kanal}.json'
    try:
        liste = json.loads(pfad.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        liste = []
    liste = [x for x in liste if (heute - datetime.date.fromisoformat(x['datum'])).days < GESCHEITERT_TAGE]
    liste.append({'datum': heute.isoformat(), 'thema': thema, 'code': code})
    GESCHEITERT.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(liste, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def offene_themen(kanal):
    """Naechste Warteschlangen-Themen ohne Vorratsskript (auch spaeter geplante), ohne kuerzlich gescheiterte."""
    return [t for t in _offene_themen(kanal) if t not in gescheitert(kanal)]


def _offene_themen(kanal):
    import themen
    vorhanden = {e.get('thema_eingabe') for _, e in eintraege(kanal)}
    offen = [x['thema'] for x in themen.laden() if x['kanal'] == kanal
             and x.get('status', 'bereit') == 'bereit' and x['thema'] not in vorhanden
             and not themen.gespraech_grund(x['thema'])]
    # GEMELDET 09.10.2026: „Themen so sortieren, was aktuell gehypt ist." Der Trend-Check des
    # Tages (derselbe, den der Videolauf danach aus verlauf/trendcheck/ wiederverwendet) legt
    # die Reihenfolge fest - das Skript fuer das heisseste Thema liegt morgens schon bereit.
    try:
        import trendcheck
        _, bericht = trendcheck.waehlen(kanal, themen=themen)
        punkte = {k['thema']: k.get('punkte') or 0 for k in (bericht or {}).get('kandidaten', [])}
        offen.sort(key=lambda t: -punkte.get(t, 0))
        # 19.10.2026: Ein Zuschauer-Trendthema (KI: YouTube/Google) steht in keiner Warteschlange - ohne
        # diese Zeile schrieb der Nachtlauf frei gewaehlt (GitHub-Neuheit) und der Tageslauf nahm dieses Skript.
        if bericht and bericht.get('zuschauer') and bericht.get('thema') not in offen + list(vorhanden):
            offen.insert(0, bericht['thema'])
        # Nutzer 21.10.2026: Trend im Fokus, auch fuer Zusatzvideos und alle Kanaele. Bester Trend zuerst,
        # dann deine Telegram-Themen, dann die weiteren Trends - frei gewaehlt (GitHub/klassische Marke) nur,
        # wenn nichts davon offen ist (fuellen() schreibt '' erst bei leerer Liste).
        trends_offen = [t for t in trendcheck.trend_themen(kanal) if t not in offen and t not in vorhanden]
        if trends_offen:
            offen = ([trends_offen[0]] + offen + trends_offen[1:]) if not (bericht or {}).get('zuschauer') \
                else (offen[:1] + trends_offen[:1] + offen[1:] + trends_offen[1:])
    except Exception as e:
        print('Trend-Reihenfolge nicht verfuegbar, Warteschlangen-Reihenfolge:', str(e)[:100])
    return offen


def _zuschauer_trends(kanal):
    try:
        import trendcheck
        return bool(trendcheck.trendquellen(kanal))
    except Exception:
        return False


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
        # GEMESSEN 22.10.2026 (01:05 UTC): Das KI-Trendthema fiel durch die Faktenpruefung, danach schrieb der
        # Nachtlauf frei gewaehlt „HaozheH3/awesome-rea-games". Nutzer 21.10.: „Nachtvorrat muss das Thema immer vom
        # YouTube Trends oder ... Google Trends holen". Kanaele mit Zuschauer-Trendquellen schreiben nachts nichts
        # frei Gewaehltes; der Tageslauf waehlt bei Bedarf selbst (Titelvorlage/Trend-Check).
        # 31.10.2026: Business waehlte danach TAGSUEBER frei (Lego, ServiceNow; 7-15 Min. je Lauf, einmal kein
        # Video). Firmenkanaele waehlen darum schon nachts frei (prompts.ANFASSBAR, skript.sperrliste); KI nicht.
        if not thema and _zuschauer_trends(kanal) and _kanal_daten(kanal_pfad).get('quelle') != 'wikipedia':
            print(f'Vorrat {kanal}: kein offenes Trendthema - nichts frei gewaehlt', flush=True)
            break
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
            if r in (2, 3):  # Fakten/Quelle oder Story: dasselbe Thema in der naechsten Nacht nicht noch einmal
                gescheitert_merken(kanal, thema, r)
            continue
        s = json.loads(ziel.read_text(encoding='utf-8'))
        import prompts
        e = {'thema_eingabe': thema, 'erstellt_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'prompts': prompts.VERSION, 'modell': s.get('modell'), 'story_note': (s.get('story') or {}).get('note'), 'skript': s}
        if not gueltig(e, _kanal_daten(kanal_pfad)):
            print('Vorrat: Pruefungen nicht bestanden - nicht aufgenommen')
            continue
        if wiederholung(kanal, e):
            print('Vorrat: Thema schon geliefert - nicht aufgenommen:', s.get('thema'))
            break  # frei gewaehlt: naechster Lauf waehlt neu
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
