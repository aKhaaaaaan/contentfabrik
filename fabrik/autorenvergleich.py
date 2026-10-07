"""Identische Quellen und Aufgaben fuer Gemini/Groq; keine Produktion oder Uploads.

Zwei verdeckte KI-Pruefungen pro Skript, zusaetzlich Zahlen/Struktur. Ergebnisse
sind vorlaeufig; die menschliche Blindbewertung wird nicht erfunden.
"""
import argparse
import copy
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import time
import urllib.error
import urllib.request

import dramaturgie
import lernen
import prompts
import skript
import zahlen
from qualitaet import redaktion, STORY_KATEGORIEN

AUTOREN = ('gemini', 'groq')
VERSION = '2026-10-06.4'
GROQ_MODELL = 'openai/gpt-oss-120b'
GEMINI_MODELLE = [m for m in skript.MODELLE if 'lite' not in m.lower()]
AUTOR_SCHEMA = {'type': 'OBJECT', 'properties': {
    'thema': {'type': 'STRING'}, 'titel_zeile1': {'type': 'STRING'},
    'titel_zeile2': {'type': 'STRING'}, 'beschreibung': {'type': 'STRING'},
    'teile': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
        'text': {'type': 'STRING'}, 'szene': {'type': 'STRING'}}, 'required': ['text', 'szene']}}},
    'required': ['thema', 'titel_zeile1', 'titel_zeile2', 'beschreibung', 'teile']}
PRUEF_SCHEMA = {'type': 'OBJECT', 'properties': {
    'fakten': skript.PRUEF_SCHEMA, 'story': skript.STORY_SCHEMA}, 'required': ['fakten', 'story']}
GROQ_VERBRAUCH = []


def fehlertext(fehler):
    """Kurze Diagnose ohne Schluessel, auch bei URL-Fehlern."""
    text = str(fehler)
    for name in ('GEMINI_API_KEY', 'GROQ_API_KEY', 'GITHUB_TOKEN', 'GH_TOKEN'):
        if os.environ.get(name):
            text = text.replace(os.environ[name], '***')
    text = re.sub(r'([?&](?:key|token|api_key)=)[^&\s]+', r'\1***', text, flags=re.I)
    return text[:500]


def speichern(pfad, daten):
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix('.tmp')
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(pfad)


def schema_pruefen(d, schema, pfad='antwort'):
    art = schema['type']
    typen = {'OBJECT': dict, 'ARRAY': list, 'STRING': str, 'INTEGER': int, 'BOOLEAN': bool}
    if not isinstance(d, typen[art]) or art == 'INTEGER' and isinstance(d, bool):
        raise ValueError(f'{pfad}: falscher Typ')
    if art == 'OBJECT':
        for k in schema.get('required', []):
            if k not in d:
                raise ValueError(f'{pfad}.{k}: fehlt')
        for k, wert in d.items():
            if k in schema['properties']:
                schema_pruefen(wert, schema['properties'][k], f'{pfad}.{k}')
    if art == 'ARRAY':
        for n, wert in enumerate(d):
            schema_pruefen(wert, schema['items'], f'{pfad}[{n}]')


def angleichen(d, schema):
    """Objekt statt Text in einer Textliste zu Text machen; sonst nichts aendern.

    GEMESSEN 07.10.2026 (Run 37649294220, 5 von 5 Story-Pruefungen): GPT-OSS gab
    'schwaechen' als Objekte zurueck, Groq lehnte mit HTTP 400 ab, obwohl die
    mitgeschickte Antwort gueltiges JSON war - beide Kanaele ohne Video.
    """
    art = schema['type']
    if art == 'STRING' and isinstance(d, dict):
        return ' - '.join(str(v) for v in d.values() if isinstance(v, (str, int, float))
                          and not isinstance(v, bool))
    if art == 'OBJECT' and isinstance(d, dict):
        return {k: angleichen(v, schema['properties'][k]) if k in schema['properties'] else v
                for k, v in d.items()}
    if art == 'ARRAY' and isinstance(d, list):
        return [angleichen(v, schema['items']) for v in d]
    return d


def groq_schema(schema):
    """Dasselbe fachliche Schema als geschlossenes JSON Schema fuer Groq."""
    d = {'type': schema['type'].lower()}
    if schema['type'] == 'OBJECT':
        d.update(properties={k: groq_schema(v) for k, v in schema['properties'].items()},
                 required=list(schema['properties']), additionalProperties=False)
    if schema['type'] == 'ARRAY':
        d['items'] = groq_schema(schema['items'])
    if 'enum' in schema:
        d['enum'] = list(schema['enum'])
    return d


def groq(prompt, schema, ausgabe_tokens=3840, deadline=None):
    key = os.environ['GROQ_API_KEY']
    auftrag = prompt
    ausgabeformat = {'type': 'json_schema', 'json_schema': {
        'name': 'contentfabrik_antwort', 'strict': True, 'schema': groq_schema(schema)}}
    # Konservative Schaetzung; tatsaechlicher Tokenverbrauch wird gespeichert.
    reserve = math.ceil((len(auftrag) + len(json.dumps(ausgabeformat))) / 3) + ausgabe_tokens
    if reserve > 7900:
        raise ValueError('Auftrag zu gross fuer das kostenlose Groq-Minutenkontingent')
    ende = min(time.monotonic() + 180, deadline if deadline is not None else float('inf'))
    while GROQ_VERBRAUCH:
        jetzt = time.monotonic()
        GROQ_VERBRAUCH[:] = [(t, n) for t, n in GROQ_VERBRAUCH if jetzt - t < 61]
        if sum(n for _, n in GROQ_VERBRAUCH) + reserve <= 8000:
            break
        warte = min(60, max(0.1, 61 - (jetzt - GROQ_VERBRAUCH[0][0])))
        if warte + 5 >= ende - time.monotonic():
            raise RuntimeError('Groq-Minutenreserve passt nicht in die verbleibende Frist')
        print(f'Groq-Kontingent: {warte:.1f} Sekunden warten', flush=True)
        time.sleep(warte)
    for versuch in range(2):
        rest = ende - time.monotonic()
        if rest <= 0:
            raise RuntimeError('Groq-Zeitlimit erreicht')
        req = urllib.request.Request('https://api.groq.com/openai/v1/chat/completions',
            data=json.dumps({'model': GROQ_MODELL, 'include_reasoning': False,
                'reasoning_effort': 'low', 'max_completion_tokens': ausgabe_tokens,
                'response_format': ausgabeformat,
                'messages': [{'role': 'user', 'content': auftrag}]}).encode(),
            headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
                     'User-Agent': 'Contentfabrik-Autorenvergleich/1.0'})
        try:
            with urllib.request.urlopen(req, timeout=min(45 if deadline is not None else 120, rest)) as r:
                antwort = json.load(r)
            usage = antwort.get('usage', {})
            GROQ_VERBRAUCH.append((time.monotonic(), usage.get('total_tokens', reserve)))
            choice = antwort['choices'][0]
            if choice.get('finish_reason') != 'stop':
                grund = choice.get('finish_reason')
                grund = grund if grund in ('length', 'content_filter', 'tool_calls', 'function_call') else 'unbekannt'
                raise ValueError(f'Groq-Antwort nicht vollstaendig (finish_reason={grund})')
            d = json.loads(choice['message']['content'])
            schema_pruefen(d, schema)
            return d, GROQ_MODELL, usage
        except urllib.error.HTTPError as e:
            try:
                error = json.loads(e.read()).get('error', {})
                detail = fehlertext(error.get('message', ''))
                fehl = error.get('failed_generation')
                if isinstance(fehl, str):
                    # Nur Syntaxmessung; keine internen Gedanken oder Rohantwort veroeffentlichen.
                    detail += f' Ausgabezeichen={len(fehl)}'
                    try:
                        json.loads(fehl)
                        detail += ' JSON-Syntax=gueltig'
                    except json.JSONDecodeError as j:
                        detail += f' JSON-Syntax={j.msg} Position={j.pos}'
            except Exception:
                detail, fehl = 'Keine strukturierte Fehlerbeschreibung', None
            if e.code == 400 and isinstance(fehl, str):
                # Gueltiges JSON mit nur falscher Form: lokal angleichen und normal pruefen.
                try:
                    d = angleichen(json.loads(fehl), schema)
                    schema_pruefen(d, schema)
                    GROQ_VERBRAUCH.append((time.monotonic(), reserve))
                    return d, GROQ_MODELL, {}
                except (ValueError, KeyError, TypeError):
                    pass
            if e.code == 429 and versuch == 0:
                if ende - time.monotonic() <= 65:
                    raise RuntimeError('Groq-Minutenlimit; keine Zeit fuer erneute Anfrage') from None
                time.sleep(60)
                continue
            raise RuntimeError(f'Groq HTTP {e.code}: {detail}') from None
    raise RuntimeError('Groq-Anfrage nicht abgeschlossen')


def anfrage(provider, prompt, schema, ausgabe_tokens=3840):
    if provider == 'groq':
        return groq(prompt, schema, ausgabe_tokens)
    if provider != 'gemini':
        raise ValueError('Unbekannter Anbieter')
    vorher = copy.deepcopy(skript.VERBRAUCH)
    d, modell = skript.gemini(prompt, schema, modelle=GEMINI_MODELLE)
    schema_pruefen(d, schema)
    neu = skript.VERBRAUCH[modell]
    alt = vorher.get(modell, [0, 0, 0])
    return d, modell, {'anfragen': neu[0] - alt[0], 'prompt_tokens': neu[1] - alt[1],
                      'completion_tokens': neu[2] - alt[2]}


def autor_prompt(fall, regeln):
    return ('Write an original English Short for general viewers. ' + prompts.DATEN + prompts.FAKTEN
        + prompts.SPRECHEN + '\nUse 190-220 spoken words in 8-10 short parts. '
          'The first sentence is at most 9 words. Every part adds supported information. '
          'Make the opening question specific; give a concrete answer before the ending. '
          'Explain practical use and a documented limitation for a tool; for a business tell '
          'the real obstacle, response and consequence. No ranking, invented crisis or metrics. '
        + dramaturgie.interaktion({'videoformat': 'short'})
        + '\nEach szene describes one matching illustrative shot in 12-25 English words. '
          'Use our original channel presenter at the beginning and again during the story, '
          'a lively painted urban game-poster look; do not copy game characters or portray '
          'fictional illustrations as actual founder events. Title promises are factual claims. '
          'Do not claim a tool is free or commercially unrestricted without source evidence. '
        + '\nTASK DATA:\n' + json.dumps({'channel': fall['kanal'], 'topic': fall['thema'],
              'quality_lessons': regeln[:3], 'sources': fall['quellen']}, ensure_ascii=False))


def struktur(entwurf):
    teile = entwurf['teile']
    text = ' '.join(t['text'] for t in teile)
    fehler = []
    worte = len(text.split())
    if not 190 <= worte <= 220:
        fehler.append(f'Wortbudget: {worte} statt 190-220')
    if not 8 <= len(teile) <= 10:
        fehler.append('Anzahl Sprechphasen ausserhalb 8-10')
    if any(not t['text'].strip() for t in teile):
        fehler.append('Leere Sprechphase')
    erster = re.split(r'[.!?]', teile[0]['text'])[0] if teile else ''
    if len(erster.split()) > 9:
        fehler.append('Erster Satz laenger als neun Woerter')
    # Ein echter gesprochener Dreifach-Aufruf, nicht drei beliebige Woerter in Quellen.
    cta = re.compile(r'\blike\s*[,;]?\s*(?:and\s+)?share\s*[,;]?\s*(?:and\s+)?save\b', re.I)
    matches = list(cta.finditer(text))
    if len(matches) != 1 or not cta.search(' '.join(t['text'] for t in teile[-2:])):
        fehler.append('Genau ein like/share/save-Aufruf am Ende erforderlich')
    return fehler, worte


def pruef_prompt(fall, entwurf):
    return ('Independently assess the supplied draft; you do not know its author. '
        + prompts.DATEN + prompts.FAKTEN + prompts.NOTEN
        + 'Return {fakten:{ok,probleme},story:{note,kategorien,schwaechen,besserer_hook}}. '
          'Check title, description and all spoken claims against ONLY the same supplied sources. '
          'ok=false for any unsupported/exaggerated claim; quote the exact clause and mismatch. '
          'Do not assess illustrative szene fields as historical claims. '
          'For story assess hook, spannung, ueberraschung, tempo, aufloesung, teilbarkeit '
          'on 1-10. Quiet clear storytelling can be excellent; no invented stakes required. '
          'Check that the opening is answered concretely, the narrative progresses and one '
          'spoken like/share/save request follows the payoff. Report material weaknesses with '
          'a quoted sentence and a feasible same-facts fix. Suggestions are not evidence. '
          'An empty weakness list is acceptable. Do not predict audience performance.\n'
        + json.dumps({'sources': fall['quellen'], 'draft': {k: entwurf[k] for k in
                     ('thema', 'titel_zeile1', 'titel_zeile2', 'beschreibung')},
                     'narration': [t['text'] for t in entwurf['teile']]}, ensure_ascii=False))


def urteilsgruende(pruefung):
    schema_pruefen(pruefung, PRUEF_SCHEMA)
    fakten = pruefung['fakten']
    gruende = []
    if fakten['ok'] is not True or fakten['probleme']:
        gruende.append('Faktenpruefung nicht bestanden')
    gruende += redaktion(pruefung['story'], STORY_KATEGORIEN, 'Skript')[1]
    return gruende


def main(faelle, ziel, anzahl=3):
    ziel = Path(ziel)
    daten = json.loads(Path(faelle).read_text(encoding='utf-8'))
    gruppen = {}
    for f in daten['faelle']:
        gruppen.setdefault(f['kanal'], []).append(f)
    ausgewaehlt = [f for gruppe in gruppen.values() for f in gruppe[:anzahl]]
    for fall in ausgewaehlt:
        quelltext = '\n'.join(q['text'] for q in fall['quellen'])
        if hashlib.sha256(quelltext.encode()).hexdigest() != fall['quellen_sha256']:
            raise ValueError('Quellenpaket seit Vorbereitung veraendert')
    speichern(ziel / 'faelle.json', {'faelle': ausgewaehlt})
    bericht = {'run_id': os.environ.get('GITHUB_RUN_ID'), 'commit': os.environ.get('GITHUB_SHA'),
        'datum_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'prompt_version': prompts.VERSION, 'vergleich_version': VERSION,
        'status': 'laeuft', 'kandidaten': [],
        'menschliche_bewertung': None, 'standardautor_geaendert': False}
    for fall in ausgewaehlt:
        gemeinsam = autor_prompt(fall, lernen.laden(fall['kanal']).get('regeln', []))
        auftrag = ziel / 'auftraege' / (fall['id'] + '.txt')
        auftrag.parent.mkdir(parents=True, exist_ok=True)
        auftrag.write_text(gemeinsam, encoding='utf-8')
        prompt_sha = hashlib.sha256(gemeinsam.encode()).hexdigest()
        reihenfolge = list(AUTOREN)
        random.SystemRandom().shuffle(reihenfolge)
        for label, autor in zip(('A', 'B'), reihenfolge):
            ident = f"{fall['id']}-{label}"
            basis = {'id': ident, 'kanal': fall['kanal'], 'fall': fall['id'], 'label': label,
                     'autor': autor, 'autor_modell': None, 'prompt_sha256': prompt_sha,
                     'quellen_sha256': fall['quellen_sha256'], 'status': 'offen',
                     'strukturfehler': [], 'pruefungen': {}, 'menschliche_bewertung': None}
            bericht['kandidaten'].append(basis)
            print(f"Autorvergleich: {ident} / {autor}", flush=True)
            try:
                start = time.monotonic()
                entwurf, modell, usage = anfrage(autor, gemeinsam, AUTOR_SCHEMA)
                basis.update(autor_modell=modell, autor_verbrauch=usage,
                             autor_sekunden=round(time.monotonic() - start, 2))
                entwurf['videoformat'] = 'short'
                basis['strukturfehler'], basis['woerter'] = struktur(entwurf)
                basis['zahlen_unbelegt'] = zahlen.unbelegt(entwurf,
                    [f"{q.get('name', '')} {q['text']}" for q in fall['quellen']])
                speichern(ziel / 'entwuerfe' / f'{ident}.json', entwurf)
                blind = ziel / 'blind' / f'{ident}.md'
                blind.parent.mkdir(parents=True, exist_ok=True)
                blind.write_text(f"# {fall['thema']} / Fassung {label}\n\n"
                    + entwurf['titel_zeile1'] + ' / ' + entwurf['titel_zeile2'] + '\n\n'
                    + '\n\n'.join(t['text'] for t in entwurf['teile']) + '\n', encoding='utf-8')
                p = pruef_prompt(fall, entwurf)
                for pruefer in AUTOREN:
                    try:
                        start = time.monotonic()
                        urteil, m, u = anfrage(pruefer, p, PRUEF_SCHEMA, 2048)
                        basis['pruefungen'][pruefer] = {'modell': m, 'urteil': urteil,
                            'sperrgruende': urteilsgruende(urteil), 'verbrauch': u,
                            'sekunden': round(time.monotonic() - start, 2)}
                    except Exception as e:
                        basis['pruefungen'][pruefer] = {'fehler': type(e).__name__,
                                                      'diagnose': fehlertext(e),
                                                      'sperrgruende': ['Pruefung nicht verfuegbar']}
                ok = (not basis['strukturfehler'] and not basis['zahlen_unbelegt']
                      and len(basis['pruefungen']) == 2
                      and all(not q['sperrgruende'] for q in basis['pruefungen'].values()))
                basis['status'] = 'ki_vorpruefung_bestanden' if ok else 'gesperrt_oder_pruefung_fehlt'
            except Exception as e:
                # Kurze geschwaerzte Diagnose, keine Zugangsdaten ausgeben.
                basis.update(status='autorausfall', fehler=type(e).__name__, diagnose=fehlertext(e))
            finally:
                speichern(ziel / 'bericht.json', bericht)
            print(f"Autorvergleich: {ident} / {basis['status']}", flush=True)
    geschrieben = sum(b['autor_modell'] is not None for b in bericht['kandidaten'])
    vollstaendig = (geschrieben == len(bericht['kandidaten']) and geschrieben > 0
        and all(len(b['pruefungen']) == 2 and all('fehler' not in p for p in b['pruefungen'].values())
                for b in bericht['kandidaten']))
    bericht['status'] = ('ausgewertet_ki_mensch_offen' if vollstaendig else
        'teilvergleich_pruefungen_unvollstaendig' if geschrieben else 'keine_verwertbaren_entwuerfe')
    speichern(ziel / 'bericht.json', bericht)
    zeilen = ['# Autorenvergleich: vorlaeufige KI-Pruefung', '',
        '| Fall | Fassung | Autor / Modell | Woerter | Status |', '|---|---|---|---|---|']
    for b in bericht['kandidaten']:
        zeilen.append(f"| {b['fall']} | {b['label']} | {b['autor']} / {b['autor_modell']} | "
                      f"{b.get('woerter', '-')} | {b['status']} |")
    zeilen += ['', 'Keine menschliche Bewertung erfolgt; kein Standardautor geaendert.',
               'Quellen/Autor-Auftraege je Paar identisch; beide Anbieter pruefen beide Fassungen.',
               'Keine Video-Produktion, Telegram-Zustellung oder Plattform-Veroeffentlichung.']
    (ziel / 'bericht.md').write_text('\n'.join(zeilen) + '\n', encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write('\n'.join(zeilen))


def diagnose(ziel, faelle=None, anbieter=AUTOREN):
    """Verfuegbarkeit und Minimal-JSON pruefen; keine Quellen oder Videos."""
    ergebnis = {'datum_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'run_id': os.environ.get('GITHUB_RUN_ID'), 'anbieter': {}}
    for provider in anbieter:
        key = os.environ['GEMINI_API_KEY' if provider == 'gemini' else 'GROQ_API_KEY']
        url = ('https://generativelanguage.googleapis.com/v1beta/models?key=' + key
               if provider == 'gemini' else 'https://api.groq.com/openai/v1/models')
        headers = {'Authorization': 'Bearer ' + key} if provider == 'groq' else {}
        d = ergebnis['anbieter'][provider] = {}
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                modelle = json.load(r)
            if provider == 'gemini':
                d['modelle'] = [m['name'].removeprefix('models/') for m in modelle.get('models', [])
                    if 'generateContent' in m.get('supportedGenerationMethods', [])]
            else:
                d['modelle'] = [m['id'] for m in modelle.get('data', [])]
        except Exception as e:
            d['modellabfrage_fehler'] = fehlertext(e)
        try:
            data, modell, usage = anfrage(provider,
                'Return ONLY JSON: {"ok":true,"probleme":[]}. This is a connectivity test.',
                skript.PRUEF_SCHEMA, 1024)
            d.update(minimal_json=data, modell=modell, verbrauch=usage)
        except Exception as e:
            d['minimal_json_fehler'] = fehlertext(e)
        if faelle:
            fall = json.loads(Path(faelle).read_text(encoding='utf-8'))['faelle'][0]
            try:
                data, modell, usage = anfrage(provider,
                    autor_prompt(fall, lernen.laden(fall['kanal']).get('regeln', [])), AUTOR_SCHEMA)
                speichern(Path(ziel) / ('diagnose-autor-' + provider + '.json'), data)
                d.update(autor_modell=modell, autor_verbrauch=usage,
                         autor_struktur=struktur(data)[0], autor_woerter=struktur(data)[1])
            except Exception as e:
                d['autor_fehler'] = fehlertext(e)
        print(json.dumps({provider: d}, ensure_ascii=False), flush=True)
    speichern(Path(ziel) / 'diagnose.json', ergebnis)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--faelle', default='vergleiche/autoren/faelle.json')
    parser.add_argument('--ziel', default='ausgabe/autorenvergleich')
    parser.add_argument('--anzahl', type=int, choices=(1, 2, 3), default=3)
    parser.add_argument('--diagnose', action='store_true')
    parser.add_argument('--diagnose-autor', action='store_true')
    parser.add_argument('--diagnose-anbieter', choices=AUTOREN)
    parser.add_argument('--diagnose-alternativen', action='store_true')
    args = parser.parse_args()
    if args.diagnose:
        if args.diagnose_alternativen:
            GEMINI_MODELLE[:] = ['gemini-2.5-pro', 'gemini-2.5-flash']
        diagnose(args.ziel, args.faelle if args.diagnose_autor else None,
                 (args.diagnose_anbieter,) if args.diagnose_anbieter else AUTOREN)
    else:
        main(args.faelle, args.ziel, args.anzahl)
