"""Grundeinstellungen fuer JEDEN Kanal - neue Kanaele erben das Bewaehrte automatisch.

GEMELDET 08.10.2026: „Das Tempo bei den anderen Kanaelen und bei zukuenftigen Kanaelen auch so
anpassen ... alles anpassen, damit es hoch skalierbar ist." Ein neuer Kanal braucht nur ein
kurzes Profil (kanaele/<slug>.json mit name, format, telegram_kuerzel ...); alles Fehlende kommt
von hier. Werte im Kanalprofil haben immer Vorrang. Stand der Werte: Nutzerentscheidungen
07./08.10.2026 (Hoerprobe Orus, Tempo 1.08, gemalt, keine Stockclips, Laenge wie die Piloten).
"""
import copy
import json
from pathlib import Path

STANDARD = {
    'videoformat': 'short',
    'tagesziel': 1,
    'laenge_s': [62, 90],
    # Gemessen 08.10.: Orus ~1.9-2.0 W/s; mit Tempo 1.08 etwa 2.1.
    'woerter_pro_sekunde': 2.1,
    'stockclips': False,
    'musik_technisch': False,
    'youtube_kategorie': '27',  # Bildung
    'erzaehlstimme': {
        'anbieter': 'gemini', 'stimme': 'Orus', 'tempo': 1.08,
        'stil': 'deep cinematic storyteller voice, warm and passionate, genuine emotion and wonder, '
                'rising energy toward the payoff, dramatic pause before each reveal, clear and natural',
    },
}

ORDNER = Path('kanaele')


def mischen(standard, profil):
    """Profil ueber Standard legen; verschachtelte Abschnitte (erzaehlstimme) feldweise."""
    aus = copy.deepcopy(standard)
    for k, v in (profil or {}).items():
        if isinstance(v, dict) and isinstance(aus.get(k), dict):
            aus[k] = mischen(aus[k], v)
        else:
            aus[k] = copy.deepcopy(v)
    return aus


def profil(daten):
    return mischen(STANDARD, daten)


def alle(ordner=ORDNER):
    """{slug: vollstaendiges Profil} fuer alle Kanaele; Dateien mit '_' sind keine Kanaele."""
    aus = {}
    for p in sorted(Path(ordner).glob('*.json')):
        if p.name.startswith('_'):
            continue
        try:
            aus[p.stem] = profil(json.loads(p.read_text(encoding='utf-8')))
        except (OSError, ValueError):
            continue
    return aus


def nach_name(name, ordner=ORDNER):
    """Vollstaendiges Profil zum Anzeigenamen (skript['kanal']); unbekannt -> None."""
    return next((d for d in alle(ordner).values() if d.get('name') == name), None)
