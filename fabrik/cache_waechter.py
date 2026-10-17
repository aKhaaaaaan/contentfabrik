"""Vor einem Push warnen, wenn der Code einen gueltigen geprueften Entwurf entwerten wuerde.

GEMESSEN 14.10.2026: Ein Logging-Fix in skript.py aenderte entwurf_cache.profil_key; der
Business-Lauf verwarf den fertigen Panasonic-Teilbau (13/18 Bilder + Ton), schrieb ein neues
Skript und verbrauchte 40 vom Nutzer extra freigegebene Minuten ohne Video.
Aufruf ohne Argumente (Git pre-push-Hook): Exit 1 bei Gefahr. CF_CACHE_VERWERFEN=1 bestaetigt
eine bewusste Entwertung (z. B. geaenderte Schreib- oder Pruefregeln).
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def gefaehrdet(wurzel='.'):
    """Kanaele mit noch gueltigem Entwurf, dessen Profil nicht mehr zum aktuellen Code passt."""
    import entwurf_cache
    treffer = []
    for meta in sorted((Path(wurzel) / 'verlauf/entwuerfe').glob('*.json')):
        try:
            d = json.loads(meta.read_text(encoding='utf-8'))
            # GEMESSEN 17.10.2026: der Langvideo-Entwurf (Coca-Cola) traegt den Schluessel von
            # formate/<kanal>.json; der Waechter verglich nur mit kanaele/ und schlug falsch an.
            name = meta.stem.removesuffix('-lang')  # Langvideo-Eintrag '<kanal>-lang' (17.10.2026)
            profile = [p for p in (Path(wurzel) / 'kanaele' / (name + '.json'),
                                   Path(wurzel) / 'formate' / (name + '.json')) if p.exists()]
            frisch = 0 <= time.time() - d['erstellt'] <= (entwurf_cache.TTL_LANG if meta.stem.endswith('-lang') else entwurf_cache.TTL)
            if frisch and profile and d.get('profil') not in {entwurf_cache.profil_key(p) for p in profile}:
                treffer.append(meta.stem)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return treffer


def main():
    treffer = gefaehrdet()
    if not treffer:
        return 0
    print('CACHE-WAECHTER: Dieser Code entwertet den gueltigen geprueften Entwurf von: '
          + ', '.join(treffer) + '.\nDer naechste Lauf schreibt dann ein neues Skript und baut alle Bilder neu.\n'
          'Aendert die Aenderung KEINE Schreib-/Pruefregel: Profil in verlauf/entwuerfe nachfuehren '
          '(python fabrik/cache_waechter.py --nachfuehren) und mitpushen.\n'
          'Ist die Entwertung gewollt: CF_CACHE_VERWERFEN=1 git push', file=sys.stderr)
    return 0 if os.environ.get('CF_CACHE_VERWERFEN') == '1' else 1


def nachfuehren(wurzel='.'):
    import entwurf_cache, ki_speicher
    for kanal in gefaehrdet(wurzel):
        meta = Path(wurzel) / 'verlauf/entwuerfe' / (kanal + '.json')
        d = json.loads(meta.read_text(encoding='utf-8'))
        d['profil'] = entwurf_cache.profil_key(Path(wurzel) / 'kanaele' / (kanal + '.json'))
        ki_speicher.speichern(meta, d)
        print('Profil nachgefuehrt:', kanal)


if __name__ == '__main__':
    if sys.argv[1:] == ['--nachfuehren']:
        nachfuehren()
        sys.exit(0)
    sys.exit(main())
