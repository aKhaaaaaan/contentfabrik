"""Noch ein kostenloses Video heute? Stand je Kanal aus den gespeicherten Sperren - keine KI-Anfrage.

Nutzerwunsch 21.10.2026: „Nach dem Bau von Videos moechte ich eine Nachricht, dass ich noch ein weiteres
Video kostenlos pro Kanal bauen kann oder auch nicht - dann kann ich entscheiden." Handstarts duerfen das
kostenlose Kontingent ausschoepfen; Kostenpflichtiges ist nicht eingerichtet und nur nach Zustimmung.

Grenze der Aussage: Google/Groq melden das Restkontingent nicht vorab. Gezaehlt wird, was ein Lauf als
„Tageskontingent erschoepft" gespeichert hat (verlauf/gemini-kontingent.json). Ein Lauf kann also trotz
„ja" unterwegs an ein Limit stossen - dann sagt die Fehlermeldung genau das.
"""
import datetime
import json
import os
import time
from pathlib import Path

import ki_speicher

# Nur der Gratis-Schluessel zaehlt: GEMINI_API_KEY_RESERVE bzw. GEMINI_TTS_API_KEY sind das BEZAHLTE Projekt
# (skript.reserve_schluessel, 15.10.2026) - wer dort weiterlaeuft, baut kostenpflichtig.
SCHLUESSEL = ('GEMINI_API_KEY',)


def _gesperrt(jetzt):
    """{konto: {modell, ...}} mit heute erschoepftem Tageskontingent (kurze Ueberlast zaehlt nicht)."""
    try:
        d = json.loads(ki_speicher.KONTINGENT.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    aus = {}
    for name, e in (d.get('modelle') or {}).items():
        if isinstance(e, dict) and 'Tageskontingent' in str(e.get('grund')) \
                and isinstance(e.get('bis'), (int, float)) and e['bis'] > jetzt and ':' in name:
            konto, modell = name.split(':', 1)
            aus.setdefault(konto, set()).add(modell)
    return aus


def gemini_frei(jetzt=None):
    """None, wenn Skriptpruefung UND Bildpruefung noch ein freies Gemini-Modell haben, sonst der Grund."""
    import skript
    jetzt = time.time() if jetzt is None else jetzt
    gesperrt = _gesperrt(jetzt)
    konten = [ki_speicher.konto(os.environ[s]) for s in SCHLUESSEL if os.environ.get(s)] or list(gesperrt) or ['']
    for konto in konten:
        weg = gesperrt.get(konto, set())
        if any(m not in weg for m in skript.MODELLE) and any(m not in weg for m in skript.SEHEN):
            return None
    wieder = datetime.datetime.fromtimestamp(ki_speicher.tagesreset(jetzt), datetime.timezone.utc)
    return f'Gemini-Gratiskontingent heute aufgebraucht (wieder ab {_berlin(wieder)} Uhr)'


def _berlin(zeit):
    try:
        from zoneinfo import ZoneInfo
        return zeit.astimezone(ZoneInfo('Europe/Berlin')).strftime('%H:%M')
    except Exception:
        return zeit.strftime('%H:%M UTC')


def kanal_frei(kanal):
    """None oder Grund, warum fuer diesen Kanal heute kein weiteres Gratis-Video startet."""
    import budget
    from lauf import BUDGET_S, NEUBAU_MIN_S, tagesgrenze
    rest = budget.rest(kanal, tagesgrenze(kanal, BUDGET_S))
    if rest < NEUBAU_MIN_S:
        return f'Zeitfenster aufgebraucht (noch {round(rest / 60)} Min., ein Video braucht ~20-30)'
    return None


def nachricht(kanaele):
    import illustration
    from statusmeldung import kanalname
    gemeinsam = gemini = gemini_frei()
    if illustration.KONTINGENT_LEER.exists():
        gemeinsam = gemeinsam or 'Cloudflare-Bildkontingent heute aufgebraucht (wieder ab 02:00 Uhr)'
    zeilen = []
    for k in kanaele:
        grund = gemeinsam or kanal_frei(k)
        zeilen.append(f'• {kanalname(k)}: ' + (f'nein - {grund}' if grund else 'ja'))
    text = '🆓 Heute noch ein weiteres Video kostenlos?\n' + '\n'.join(zeilen)
    if any(z.endswith(': ja') for z in zeilen):
        text += '\nStarten mit „start ki" oder „start business" an den Steuerungsbot.'
    elif gemini:
        # Nutzerwunsch 21.10.2026: auch danach weiter, aber nur ausdruecklich - das bezahlte Google-Projekt
        # traegt dann Skript- und Pruefanfragen. Ein leeres Cloudflare-Bildkontingent ist so nicht zu ersetzen.
        text += ('\nKostenpflichtig trotzdem: „start ki bezahlt" bzw. „start business bezahlt" '
                 '(bezahltes Google-Projekt, Abrechnung am Monatsende).')
    import claude_ki
    if claude_ki.pause():
        text += '\nHinweis: Claude ist gerade am Abo-Limit - das Skript schreibt dann Gemini/Groq (meist schwaecher).'
    return text + '\nSchaetzung aus gespeicherten Limits; reisst ein Limit unterwegs, kommt eine Meldung.'
