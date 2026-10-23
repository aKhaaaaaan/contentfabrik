"""Telegram-Meldung „Gemini wieder erreichbar", nachdem ein Videolauf an Gemini gescheitert ist.

Nutzerfrage 22.10.2026: „Bekomme ich auf Telegram eine Antwort, dass Gemini wieder erreichbar ist? Woher soll
ich das wissen?" Bis dahin kam nur die Stoerungsmeldung; wann ein Neustart lohnt, musste er raten.

merken  (video.yml, vor dem Sichern des Verlaufs): Lauf ohne Video UND Gemini war gesperrt/gestoert ->
         verlauf/gemini-wartet/<kanal>.json (je Kanal eine Datei: die Kanal-Jobs sichern nacheinander,
         eine gemeinsame Datei gaebe Git-Konflikte). Lauf mit Video -> eigene Datei weg.
pruefen (themen.yml, 5-Minuten-Takt): nur wenn Dateien da sind und hoechstens alle 15 Minuten; eine winzige
         Anfrage. Gesperrte Modelle (Tageskontingent) fragt skript._gemini gar nicht erst an - bis zum
         Tagesreset kostet das Warten also nichts. Antwortet ein Skript- UND ein Bildpruefmodell: eine
         Meldung, Dateien weg.
"""
import datetime
import json
import os
import sys
import time
from pathlib import Path

ORDNER = Path('verlauf/gemini-wartet')
TAKT_MIN = 15
VERFALL_S = 36 * 3600  # aeltere Merker sind ueberholt (der naechste Tageslauf merkt neu)
SCHEMA = {'type': 'OBJECT', 'properties': {'ok': {'type': 'BOOLEAN'}}, 'required': ['ok']}


def gemini_beteiligt(jetzt=None):
    """Hatte Gemini in diesem Lauf eine Sperre/Stoerung? (aktive Sperre, Zeitlimit < 2 h, Stoerungsmerker)"""
    import ki_speicher
    jetzt = time.time() if jetzt is None else jetzt
    d = ki_speicher.lesen_json(ki_speicher.KONTINGENT)
    if any(isinstance(e, dict) and isinstance(e.get('bis'), (int, float)) and e['bis'] > jetzt
           and e.get('grund') != 'Modell nicht verfuegbar' for e in (d.get('modelle') or {}).values()):
        return True
    if any(isinstance(t, (int, float)) and jetzt - t < 7200
           for v in (d.get('zeitlimits') or {}).values() if isinstance(v, list) for t in v):
        return True
    import stoerung
    return any(p.name.split('-', 3)[-1].startswith(('gemini', 'bildpruefung'))
               for p in stoerung.MERKER.glob('*')) if stoerung.MERKER.exists() else False


def merken(kanal, ausgabe=Path('ausgabe'), jetzt=None):
    from statusmeldung import lesen
    datei = ORDNER / f'{kanal}.json'
    if lesen(ausgabe / 'bericht.json').get('status') == 'gesendet':
        datei.unlink(missing_ok=True)
        return 'geliefert'
    if not gemini_beteiligt(jetzt):
        return 'anderer Grund'
    if datei.exists():
        return 'schon gemerkt'
    ORDNER.mkdir(parents=True, exist_ok=True)
    datei.write_text(json.dumps({'seit': time.time() if jetzt is None else jetzt,
                                 'thema': lesen(ausgabe / 'skript.json').get('thema', '')},
                                ensure_ascii=False) + '\n', encoding='utf-8')
    return 'gemerkt'


def erreichbar():
    """True, wenn ein Skript- und ein Bildpruefmodell antworten. Gesperrte Modelle werden nicht angefragt."""
    import skript
    try:
        _, modell = skript._gemini('Reply with {"ok": true}.', SCHEMA, modelle=skript.MODELLE,
                                   anfrage_s=60, antwort_s=20)
        if modell not in skript.SEHEN:
            skript._gemini('Reply with {"ok": true}.', SCHEMA, modelle=skript.SEHEN, anfrage_s=60, antwort_s=20)
        return True
    except Exception as e:
        print('Gemini noch nicht erreichbar:', type(e).__name__, str(e)[:120])
        return False


def text(merker):
    from statusmeldung import kanalname
    zeilen = []
    for kanal, m in sorted(merker.items()):
        seit = datetime.datetime.fromtimestamp(m.get('seit', 0), datetime.timezone.utc)
        try:
            from zoneinfo import ZoneInfo
            seit = seit.astimezone(ZoneInfo('Europe/Berlin'))
        except Exception:
            pass
        zeilen.append(f'• {kanalname(kanal)}' + (f' ({m["thema"]})' if m.get('thema') else '')
                      + f' - ohne Video seit {seit:%d.%m. %H:%M}')
    # Wortlaut wie kontingent.nachricht (Steuerungsbot-Befehle).
    return ('✅ Gemini ist wieder erreichbar (Skript- und Bildpruefung antworten).\n' + '\n'.join(zeilen)
            + '\nNeu starten mit „start ki" oder „start business" an den Steuerungsbot.')


def pruefen(jetzt=None, senden=None):
    jetzt = time.time() if jetzt is None else jetzt
    if not ORDNER.exists():
        return 'nichts offen'
    merker = {}
    for p in sorted(ORDNER.glob('*.json')):
        try:
            m = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            m = {}
        if jetzt - (m.get('seit') or 0) > VERFALL_S:
            p.unlink()
            continue
        merker[p.stem] = m
    if not merker:
        return 'nichts offen'
    if datetime.datetime.fromtimestamp(jetzt, datetime.timezone.utc).minute % TAKT_MIN >= 5:
        return 'nicht im Takt'
    if not erreichbar():
        return 'noch gestoert'
    if senden is None:
        import statusmeldung
        senden = statusmeldung.senden
    senden(text(merker))
    for kanal in merker:
        (ORDNER / f'{kanal}.json').unlink(missing_ok=True)
    return 'gemeldet'


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        if sys.argv[1:2] == ['merken']:
            print('Gemini-Merker:', merken(os.environ.get('KANAL', '')))
        else:
            print('Gemini wieder erreichbar?', pruefen())
    except Exception as fehler:  # darf Verlaufssicherung und Themenlauf nie kippen
        print('Gemini-Wiedermeldung uebersprungen:', type(fehler).__name__, str(fehler)[:120])
