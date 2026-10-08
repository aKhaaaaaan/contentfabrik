"""Gemeinsame Zugangskontrolle fuer Lauf und Telegram-Vorschau."""
import math
import re

SCHWELLE = 7
KATEGORIE_MIN = 7
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
        minimum = 6 if k == 'teilbarkeit' else KATEGORIE_MIN
        v = note({'note': werte.get(k)})
        if v is None:
            gruende.append(f'{art}-Bewertung {k} fehlt oder ist ungueltig')
        elif v < minimum:
            gruende.append(f'{art}-{k} {v}/10 unter {minimum}/10')
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
    audio = kritik.get('audio_pruefung') if isinstance(kritik, dict) else None
    if not isinstance(audio, dict) or audio.get('ok') is not True or audio.get('befunde') != []:
        gruende.append('Unabhaengige Endton-/CTA-Pruefung fehlt oder ist nicht bestanden')
    else:
        import sprachpruefung
        sha = kritik.get('video_sha256')
        if not isinstance(sha, str) or len(sha) != 64 or audio.get('video_sha256') != sha:
            gruende.append('Endton-Pruefung gehoert nicht zur bewerteten Videodatei')
        if audio.get('version') != sprachpruefung.VERSION or audio.get('videoformat') not in ('short', 'lang'):
            gruende.append('Endton-Pruefung mit ungueltiger Version oder Videoformat')
        technik = kritik.get('technik')
        pruefung = sprachpruefung.cta_bewerten(audio.get('roh'), audio.get('videoformat'),
                                            technik.get('dauer_s') if isinstance(technik, dict) else None)
        gruende += pruefung['befunde']
    if isinstance(kritik, dict) and kritik.get('video_sha256'):
        import lernen
        if lernen.abgelehnt(kritik['video_sha256']):
            gruende.append('Video durch ausdrueckliches Nutzerfeedback abgelehnt')
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


ENTWURF_MIN = 5
_KI_NOTE = re.compile(r'^Video-[\w ]+ \d+/10 unter \d+/10$|^Offenes Problem \(mittel\):')


def nur_ki_geschmack(gruende):
    """True, wenn ein Video NUR an KI-Geschmacksnoten scheitert (nie an Fakten/Technik/Ton).

    GEMELDET 08.10.2026: „Deine Meinung zaehlt, nicht die der KI" - nach Tagen ohne Video
    sieht der Nutzer fertig gebaute Videos mit KI-Note 5-6/10 als markierten Entwurf und
    entscheidet selbst. Skript-, Fakten-, Technik-, Endton- und Nutzer-Sperren bleiben hart.
    """
    return bool(gruende) and all(_KI_NOTE.search(str(g)) for g in gruende)


def bewerten(skript, kritik):
    """(Note oder None, Sperrgruende). Fehlende Pruefungen bestehen nie."""
    wert, gruende = video_bewerten(kritik)
    if isinstance(kritik, dict) and isinstance(kritik.get('audio_pruefung'), dict):
        import dramaturgie
        if kritik['audio_pruefung'].get('videoformat') != dramaturgie.videoformat(skript):
            gruende.append('Endton-Pruefung fuer anderes Videoformat')
    return wert, skript_gruende(skript) + gruende
