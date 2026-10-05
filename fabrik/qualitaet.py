"""Gemeinsame Zugangskontrolle fuer Lauf und Telegram-Vorschau."""
import math

SCHWELLE = 9
KATEGORIE_MIN = 8
STORY_KATEGORIEN = ('hook', 'spannung', 'ueberraschung', 'tempo', 'aufloesung', 'teilbarkeit')
VIDEO_KATEGORIEN = ('hook', 'bild_passt', 'dynamik', 'text', 'ton_stimme', 'tempo',
                    'inhalt', 'schluss_loop', 'regeln', 'story')


def note(daten):
    wert = daten.get('note') if isinstance(daten, dict) else None
    return wert if isinstance(wert, (int, float)) and not isinstance(wert, bool) \
        and math.isfinite(wert) and 1 <= wert <= 10 else None


def redaktion(daten, kategorien, art):
    gruende = []
    wert = note(daten)
    if wert is None:
        gruende.append(f'{art}-Note fehlt oder ist ungueltig')
    elif wert < SCHWELLE:
        gruende.append(f'{art}-Note {wert}/10 unter {SCHWELLE}/10')
    werte = daten.get('kategorien') if isinstance(daten, dict) else None
    if not isinstance(werte, dict):
        return wert, gruende + [f'{art}-Einzelbewertungen fehlen']
    for k in kategorien:
        v = note({'note': werte.get(k)})
        if v is None:
            gruende.append(f'{art}-Bewertung {k} fehlt oder ist ungueltig')
        elif v < KATEGORIE_MIN:
            gruende.append(f'{art}-{k} {v}/10 unter {KATEGORIE_MIN}/10')
    return wert, gruende


def skript_gruende(skript):
    gruende = []
    if not isinstance(skript, dict) or not isinstance(skript.get('pruefung'), dict) \
            or skript['pruefung'].get('ok') is not True:
        gruende.append('Faktenpruefung fehlt oder ist nicht bestanden')
    _, story = redaktion(skript.get('story') if isinstance(skript, dict) else None,
                          STORY_KATEGORIEN, 'Skript')
    return gruende + story


def technik_gruende(kritik):
    gruende = []
    technik = kritik.get('technik') if isinstance(kritik, dict) else None
    if not isinstance(technik, dict) or not isinstance(technik.get('befunde'), list):
        return ['Technik-Pruefung fehlt oder ist ungueltig']
    gruende.extend(str(b) for b in technik['befunde'])
    for feld in ('dauer_s', 'fps', 'lufs'):
        wert = technik.get(feld)
        if isinstance(wert, bool) or not isinstance(wert, (int, float)) or not math.isfinite(wert):
            gruende.append(f'Technik-Messwert {feld} fehlt oder ist ungueltig')
    return gruende


def video_bewerten(kritik):
    wert, gruende = redaktion(kritik, VIDEO_KATEGORIEN, 'Video')
    gruende += technik_gruende(kritik)
    probleme = kritik.get('probleme') if isinstance(kritik, dict) else None
    if not isinstance(probleme, list):
        gruende.append('Video-Problemliste fehlt oder ist ungueltig')
    else:
        for p in probleme:
            if not isinstance(p, dict) or p.get('schwere') not in ('leicht', 'mittel', 'schwer'):
                gruende.append('Video-Problem ohne gueltige Schwere')
            elif p['schwere'] != 'leicht':
                gruende.append(f"Offenes Problem ({p['schwere']}): {p.get('text', '')}")
    return wert, gruende


def rang(daten, kategorien=VIDEO_KATEGORIEN):
    """Bei gleicher Gesamtnote die ausgewogenere Fassung behalten."""
    wert, gruende = redaktion(daten, kategorien, 'Qualitaet')
    werte = daten.get('kategorien') if isinstance(daten, dict) else None
    werte = werte if isinstance(werte, dict) else {}
    einzeln = [note({'note': werte.get(k)}) or 0 for k in kategorien]
    return (not gruende, wert or 0, min(einzeln), sum(einzeln) / len(einzeln))


def bewerten(skript, kritik):
    """(Note oder None, Sperrgruende). Fehlende Pruefungen bestehen nie."""
    wert, gruende = video_bewerten(kritik)
    return wert, skript_gruende(skript) + gruende
