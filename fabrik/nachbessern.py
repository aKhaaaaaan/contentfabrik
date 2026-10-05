"""Konkrete Kritik auf Abschnitte abbilden und denselben Entwurf korrigieren.

Keine neuen Themen, Quellen-URLs, Rangnummern oder freien Code-Anweisungen.
Sprechtextaenderungen brauchen erneut Faktencheck, Zahlenprobe und Storycheck.
"""
import copy
import json
import math
from pathlib import Path
import re
import sys
import lernen
import prompts
from qualitaet import SCHWELLE, note

VISUELL = {'bild_passt_nicht', 'leeres_bild', 'standbild'}
FAMILIEN = {'bild_passt_nicht': ('bild', 'bild_passt'), 'leeres_bild': ('bild', 'dynamik'),
            'standbild': ('bild', 'dynamik'), 'text': ('untertitel', 'text'), 'ton': ('ton', 'ton_stimme'),
            'stimme': ('stimme', 'ton_stimme'), 'tempo': ('tempo', 'tempo'), 'hook': ('story', 'hook')}
SCHEMA = {'type': 'OBJECT', 'properties': {
    'bilder': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
        'index': {'type': 'INTEGER'}, 'suche': {'type': 'STRING'}, 'szene': {'type': 'STRING'},
        'bildmodus': {'type': 'STRING', 'enum': ['auto', 'foto', 'stock', 'illustration', 'karte']}},
        'required': ['index', 'suche', 'szene', 'bildmodus']}},
    'texte': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
        'index': {'type': 'INTEGER'}, 'text': {'type': 'STRING'}}, 'required': ['index', 'text']}},
}, 'required': ['bilder', 'texte']}


def zeit(text):
    m = re.search(r'(?<!\d)(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[.,](\d+))?', str(text))
    if m:
        h, minuten, sekunden, bruch = m.groups()
        if int(sekunden) >= 60 or (h and int(minuten) >= 60):
            return None
        return int(h or 0) * 3600 + int(minuten) * 60 + int(sekunden) + float('0.' + (bruch or '0'))
    m = re.fullmatch(r'\s*(\d+(?:[.,]\d+)?)\s*s\s*', str(text))
    return float(m[1].replace(',', '.')) if m else None


def abschnitte(zeittext, laengen):
    """Zeitbereich beruehrt [Start, Ende); ein Schnitt gehoert zum neuen Abschnitt."""
    if not laengen or any(isinstance(x, bool) or not isinstance(x, (int, float))
                         or not math.isfinite(x) or x <= 0 for x in laengen):
        return []
    bereich = re.split(r'\s*[-–]\s*', str(zeittext), maxsplit=1)
    start = zeit(bereich[0])
    ende = zeit(bereich[1]) if len(bereich) == 2 else None
    if start is None or start >= sum(laengen) or (len(bereich) == 2 and (ende is None or ende < start)):
        return []
    ende = max(start + 0.001, ende or start)
    t, treffer = 0, []
    for i, dauer in enumerate(laengen):
        if start < t + dauer and ende > t:
            treffer.append(i)
        t += dauer
    return treffer


def faktencheck(skript):
    from skript import gemini, PRUEF_SCHEMA, story_bewerten
    import zahlen
    belege = skript.get('belege') or []
    if not belege or any(not isinstance(q, dict) or not q.get('text') for q in belege):
        raise ValueError('Quelltexte fehlen fuer erneuten Faktencheck')
    quelle = '\n'.join(f"{q.get('name', '')}: {q['text']}" for q in belege)
    gesprochen = ' '.join(t['text'] for t in skript['teile'])
    p, _ = gemini(prompts.fakten(quelle, skript, 'corrected narration'), PRUEF_SCHEMA, temperatur=0.1)
    fehlt = zahlen.unbelegt(skript, [f"{q.get('name', '')} {q['text']}" for q in belege])
    skript['pruefung'] = p
    if p.get('ok') is not True or fehlt:
        raise ValueError('Faktencheck: ' + '; '.join(map(str, p.get('probleme', []) + fehlt)))
    import zweit
    z = zweit.pruefen(gesprochen, quelle)
    if z:
        skript['zweitpruefung'] = z
    if z and (z.get('ok') is not True or z.get('leicht')):
        raise ValueError('Zweitpruefer: ' + '; '.join(z.get('probleme', []) + z.get('leicht', [])))
    skript['pruefung'] = p
    skript['story'] = story_bewerten(skript)


def planen(skript, kritik, messung, config, kanal):
    neu = copy.deepcopy(skript)
    plan = {'aktionen': [], 'einstellungen': {}, 'offen': [], 'teile': []}
    laengen = messung.get('abschnitte_s') or []
    if len(laengen) != len(skript['teile']):
        laengen = []
    bildziele, textziele = set(), set()
    probleme = kritik.get('probleme') or []
    kategorien = kritik.get('kategorien') or {}
    # Eine Eingriffsart je Runde: anschliessend laesst sich ihr Nutzen vergleichen.
    kandidaten = {}
    for p in probleme:
        if p.get('art') in FAMILIEN:
            familie, kategorie = FAMILIEN[p['art']]
            wert = kategorien.get(kategorie, 5)
            if not isinstance(wert, (int, float)) or isinstance(wert, bool) or not math.isfinite(wert):
                wert = 5
            if familie == 'bild' and not abschnitte(p.get('zeit', ''), laengen):
                continue
            if familie == 'story' and not skript.get('belege'):
                continue
            if familie == 'stimme' and len(config.get('stimmen', [])) <= 1:
                continue
            kandidaten[familie] = min(wert, kandidaten.get(familie, 10))
    if note({'note': kategorien.get('story')}) is not None and kategorien['story'] < SCHWELLE and skript.get('belege'):
        kandidaten['story'] = min(kategorien['story'], kandidaten.get('story', 10))
    familie = min(kandidaten, key=kandidaten.get) if kandidaten else None
    plan['schwerpunkt'] = familie
    if familie:
        probleme = [p for p in probleme if FAMILIEN.get(p.get('art'), (None,))[0] == familie]
    for p in probleme:
        art = p.get('art')
        ids = abschnitte(p.get('zeit', ''), laengen)
        if art in VISUELL:
            if ids:
                bildziele.update(ids)
            else:
                plan['offen'].append('Bildproblem ohne gueltigen Zeitstempel: ' + str(p.get('text', '')))
        elif art == 'hook':
            textziele.add(0)
        elif art not in ('text', 'ton', 'stimme', 'tempo'):
            plan['offen'].append(str(p.get('text', '')))
    # Auch die schwache Story hat eine gezielte Korrektur, mit erneuter Quellenpruefung.
    if familie == 'story' and kategorien.get('story', 10) < SCHWELLE:
        textziele.update(range(len(skript['teile'])))
    if textziele and not skript.get('belege'):
        plan['offen'].append('Sprechtext bleibt erhalten: gespeicherte Quelltexte fehlen')
        textziele.clear()
    if bildziele or textziele:
        from skript import gemini, SEHEN
        hinweise = '\n'.join(str(p.get('text', '')) for p in probleme)
        if familie == 'story':
            hinweise += '\n' + '\n'.join((skript.get('story') or {}).get('schwaechen', []))
        vorschlag, _ = gemini(
            'Repair THIS faceless video, keeping its topic, source-supported facts and rank order. '
            + prompts.DATEN + prompts.FAKTEN + prompts.SPRECHEN + prompts.SZENEN +
            'Return only concrete changes, with no additional fields. '
            f'Visual changes are allowed ONLY for zero-based indices {sorted(bildziele)}. '
            f'Speech changes ONLY for indices {sorted(textziele)}; preserve all verified facts and names. '
            'Choose specific English stock-search terms and an accurate visual scene that fixes the review. '
            'Historical scenes must match the period. Illustrations are illustrative, never documentary evidence. '
            'Do not repeat the failed image approach. Never invent quotes or scenes in the speech.\n'
            f'REVIEW:\n{hinweise}\nSCRIPT:\n{json.dumps(skript, ensure_ascii=False)}\n'
            'RECENT CORRECTION RESULTS (AI scores, not audience results):\n'
            + json.dumps(lernen.laden(kanal).get('korrekturen', [])[-8:], ensure_ascii=False),
            SCHEMA, temperatur=0.2, modelle=None if textziele else SEHEN)
        for b in vorschlag.get('bilder', []):
            i = b.get('index')
            if isinstance(i, bool) or not isinstance(i, int) or i not in bildziele:
                raise ValueError('Bildkorrektur ausserhalb des beanstandeten Abschnitts')
            modus = b.get('bildmodus')
            if modus not in ('auto', 'foto', 'stock', 'illustration', 'karte'):
                raise ValueError('Unbekannter Bildmodus')
            for key in ('suche', 'szene'):
                if not isinstance(b.get(key), str) or not b[key].strip():
                    raise ValueError('Bildkorrektur ohne konkrete Such-/Szenenangabe')
                neu['teile'][i][key] = b[key].strip()[:600]
            neu['teile'][i]['bildmodus'] = modus
            plan['aktionen'].append({'art': 'bild', 'variante': modus, 'index': i})
        geaendert = False
        for t in vorschlag.get('texte', []):
            i = t.get('index')
            if isinstance(i, bool) or not isinstance(i, int) or i not in textziele \
                    or not isinstance(t.get('text'), str) or not t['text'].strip():
                raise ValueError('Ungueltige Sprechtextkorrektur')
            if t['text'].strip() != skript['teile'][i]['text']:
                neu['teile'][i]['text'] = t['text'].strip()
                geaendert = True
        if geaendert:
            faktencheck(neu)
            plan['aktionen'].append({'art': 'story', 'variante': 'quellen_geprueft'})
    arten = {p.get('art') for p in probleme}
    if 'text' in arten:
        profil = lernen.waehlen(kanal, 'untertitel', ['ruhig', 'kompakt', 'hoch'], skript.get('untertitel_profil'))
        neu['untertitel_profil'] = profil
        plan['aktionen'].append({'art': 'untertitel', 'variante': profil})
    if 'ton' in arten:
        neu['musik_pegel'], neu['effekt_pegel'] = 0.035, 0.6
        if (skript.get('musik_pegel', 0.1), skript.get('effekt_pegel', 1.0)) != (0.035, 0.6):
            plan['aktionen'].append({'art': 'ton', 'variante': 'leiser'})
    if 'stimme' in arten and len(config.get('stimmen', [])) > 1:
        stimme = lernen.waehlen(kanal, 'stimme', config['stimmen'], skript.get('stimme'))
        neu['stimme'] = stimme
        plan['aktionen'].append({'art': 'stimme', 'variante': stimme})
    if 'tempo' in arten:
        text = ' '.join(str(p.get('text', '')) for p in probleme if p.get('art') == 'tempo').lower()
        aktuell = messung.get('tempo', skript.get('tempo', 1.05))
        faktor = 0.94 if any(w in text for w in ('schnell', 'gehetzt', 'rushed', 'fast')) else 1.06
        neu['tempo'] = round(max(0.9, min(1.3, aktuell * faktor)), 3)
        if neu['tempo'] != skript.get('tempo', 1.05):
            plan['aktionen'].append({'art': 'tempo', 'variante': str(neu['tempo'])})
    plan['teile'] = [i for i, (a, b) in enumerate(zip(skript['teile'], neu['teile'])) if a != b]
    plan['einstellungen'] = {k: neu.get(k) for k in ('stimme', 'tempo', 'untertitel_profil', 'musik_pegel', 'effekt_pegel')}
    neu['prompt_version'] = prompts.VERSION
    plan['prompt_version'] = prompts.VERSION
    if not plan['aktionen']:
        return None, plan
    return neu, plan


def main(vorlage, kanal_pfad, aus):
    v, ziel = Path(vorlage), Path(aus)
    skript = json.loads((v / 'skript.json').read_text(encoding='utf-8'))
    kritik = json.loads((v / 'kritik.json').read_text(encoding='utf-8'))
    messung = json.loads((v / 'messung.json').read_text(encoding='utf-8'))
    config = json.loads(Path(kanal_pfad).read_text(encoding='utf-8'))
    neu, plan = planen(skript, kritik, messung, config, Path(kanal_pfad).stem)
    ziel.mkdir(parents=True, exist_ok=True)
    (ziel / 'korrektur.json').write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding='utf-8')
    if neu is None:
        print('Keine gezielte Korrektur moeglich:', plan['offen'])
        return 2
    (ziel / 'skript.json').write_text(json.dumps(neu, indent=2, ensure_ascii=False), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
