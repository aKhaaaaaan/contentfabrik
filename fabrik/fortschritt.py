"""Echter Baufortschritt fuer den Steuerungsbot.

Nutzer 25.10.2026 ("Wie es aussieht hat es von vorne wieder anfangen", dann "Prozentual find ich schon besser"):
Status zeigte nur eine Uhr-Schaetzung (Minuten / 200) - ein fortgesetzter Bau sah aus wie ein Neustart.
lauf.py setzt den Stand, ein Hintergrundfaden liest bauzustand.json und meldet Prozent + Satz an den Worker.
Bewusst NICHT in bauen.py: dessen Quelltext steckt im Clip-Cache-Schluessel (jede Aenderung = alle Clips neu).
"""
import hashlib
import json
import os
import re
import threading
import time
import urllib.request

import rendercache

WORKER = 'https://contentfabrik-zeitplan.taktgeber.workers.dev'
TAKT_S = 60
MIN_ABSTAND_S = 120  # Cloudflare-KV (frei): 1.000 Schreibvorgaenge am Tag - hoechstens eine Meldung je 2 Min.
STAND = {}


def setzen(**werte):
    STAND.update(werte)


def berechnen(ordner, phase, versuch=1, basis=None):
    """(prozent, satz) aus dem Bauzustand des laufenden Versuchs."""
    vorher = f'Versuch {versuch}: ' if versuch and versuch > 1 else ''
    if phase == 'Video-Pruefung':
        return 85, vorher + 'Pruefung des fertigen Videos'
    if phase != 'Videobau':
        return 5, vorher + 'Skript'
    z = rendercache.laden(ordner) if ordner else {}
    plan = z.get('bildplan') or {}
    einstellungen = plan.get('einstellungen')
    if isinstance(einstellungen, list) and einstellungen:
        gesamt = len(einstellungen)
        fertig = min(gesamt, len(z.get('stuecke') or {}))
        alt = len((rendercache.laden(basis) if basis else {}).get('stuecke') or {})
        satz = f'Bild {fertig} von {gesamt}' + (f' ({min(alt, gesamt)} aus dem Zwischenstand)' if alt else '')
        return 20 + round(60 * fertig / gesamt), vorher + satz
    if z.get('audio'):
        geplant = len(plan.get('teile') or {})
        return 12 + min(7, geplant // 15), vorher + (f'Bildplan: {geplant} Einstellungen geplant' if geplant
                                                     else 'Stimme fertig, Bildplan beginnt')
    return 10, vorher + 'Stimme'


def schluessel(token):
    token = re.sub(r'\s+', '', re.sub(r'(?i)^bot', '', str(token or '').strip()))
    return hashlib.sha256(('cf-fortschritt:' + token).encode()).hexdigest()[:48]


def melden(kanal, prozent, satz, lauf=None, token=None, url=WORKER):
    lauf = lauf or os.environ.get('GITHUB_RUN_ID', '')
    token = token or os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if not lauf or not token:
        return False
    daten = json.dumps({'lauf': str(lauf), 'kanal': kanal, 'prozent': int(prozent), 'text': satz}).encode()
    anfrage = urllib.request.Request(url + '/fortschritt', data=daten, method='POST', headers={
        'Content-Type': 'application/json', 'X-CF-Schluessel': schluessel(token)})
    try:
        with urllib.request.urlopen(anfrage, timeout=10) as r:
            return r.status == 200
    except Exception:  # Statusanzeige darf den Bau nie stoeren
        return False


def starten(kanal):
    """Hintergrundfaden; meldet nur Aenderungen, hoechstens alle MIN_ABSTAND_S."""
    if not os.environ.get('GITHUB_RUN_ID') or not os.environ.get('TELEGRAM_BOT_TOKEN'):
        return None

    def schleife():
        letzt, letzt_zeit = None, 0.0
        while True:
            time.sleep(TAKT_S)
            try:
                if not STAND.get('phase'):
                    continue
                stand = berechnen(STAND.get('ordner'), STAND['phase'], STAND.get('versuch', 1), STAND.get('basis'))
                if stand != letzt and time.monotonic() - letzt_zeit >= MIN_ABSTAND_S:
                    if melden(kanal, *stand):
                        letzt, letzt_zeit = stand, time.monotonic()
            except Exception:
                pass

    faden = threading.Thread(target=schleife, daemon=True)
    faden.start()
    return faden
