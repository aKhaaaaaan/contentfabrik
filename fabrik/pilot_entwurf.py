"""Redaktionelle Pilotvorlage VOR dem Render unabhaengig pruefen."""
import json
from pathlib import Path
import sys
import dramaturgie
import nachbessern
import prompts
from qualitaet import skript_gruende


def main(vorlage, profil, ziel):
    s = json.loads(Path(vorlage).read_text(encoding='utf-8'))
    c = json.loads(Path(profil).read_text(encoding='utf-8'))
    if s.get('kanal') != c['name'] or dramaturgie.videoformat(s) != dramaturgie.videoformat(c):
        raise ValueError('Vorlage passt nicht zum Kanal/Format')
    if dramaturgie.videoformat(c) != 'short':
        raise ValueError('Diese Pilotvorlage unterstuetzt ausschliesslich Shorts')
    s.pop('story', None)
    s['pruefung'] = {'ok': False, 'probleme': ['Pruefung noch nicht abgeschlossen']}
    s['prompt_version'] = prompts.VERSION
    pfad = Path(ziel)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    def speichern():
        pfad.write_text(json.dumps(s, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    speichern()
    worte = sum(len(t['text'].split()) for t in s['teile'])
    unten, oben = dramaturgie.laengen(c)
    if not int(unten * 2.75) <= worte <= int(oben * 2.9):
        raise ValueError('Short-Vorlage ausserhalb des Wortbudgets')
    try:
        nachbessern.faktencheck(s)
    except ValueError as e:
        s['pruefung'] = {'ok': False, 'probleme': [str(e)]}
        speichern()
        print('Vorlage gesperrt:', e)
        return 2
    speichern()
    gruende = skript_gruende(s)
    print('Vorlage: Story', s['story']['note'], '/10; Sperrgruende:', gruende)
    return 3 if gruende else 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:4]))
