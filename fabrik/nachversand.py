"""Ein ueber pilot-versand nachgesendetes Video wie einen normalen Versand verbuchen.

GEMESSEN 08.11.2026: Das KI-Langvideo vom 07.11. (Lauf 42383149158, Telegram 504, nachgesendet als 2162) stand
nicht als "gesendet" im Verlauf. langvideo.faellig() hielt es deshalb fuer offen - am Montag waere dasselbe
Langvideo noch einmal gebaut worden (Kontingent, und "nie zwei Langvideos" verletzt). Ausserdem blieben
Vorratseintrag und geprueftes Entwurfs-Skript liegen. lauf.py verbucht das nur nach eigenem Versand.

Aufruf: python fabrik/nachversand.py <kanal> <artefaktordner> [datum JJJJ-MM-TT]
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _lesen(p):
    try:
        return json.loads(Path(p).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def verbuchen(kanal, ordner, datum=None):
    import entwurf_cache
    import lauf
    import vorrat
    ordner = Path(ordner)
    skript = _lesen(ordner / 'skript.json')
    if not skript.get('thema') or not skript.get('titel'):
        raise ValueError('Skript im Artefakt fehlt oder ist unvollstaendig')
    messung = _lesen(ordner / 'messung.json')
    note = _lesen(ordner / 'kritik.json').get('note')
    entwurf = os.environ.get('CF_ENTWURF') == '1'
    lauf.verlauf_eintragen(kanal, skript, 'gesendet', note, messung.get('abschnitte_s'),
                           dict(messung, entwurf=True, nachgesendet=True) if entwurf
                           else dict(messung, nachgesendet=True))
    if datum:
        # Nachtrag fuer einen frueheren Tag: das Video ging an diesem Tag raus, nicht heute.
        p = Path('verlauf') / f'{kanal}.json'
        v = json.loads(p.read_text(encoding='utf-8'))
        v[-1]['datum'] = datum
        p.write_text(json.dumps(v, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    lang = skript.get('videoformat') == 'lang'
    entwurf_cache.erledigen(f'{kanal}-lang' if lang else kanal)
    vorrat.erledigen(kanal, skript)
    print(f'Verbucht: {kanal} {"Langvideo" if lang else "Short"} "{skript["titel"]}" als gesendet')


if __name__ == '__main__':
    verbuchen(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
