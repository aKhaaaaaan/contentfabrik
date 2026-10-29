"""Zweitpruefer: ein Modell einer ANDEREN Firma prueft die Fakten (Groq, kostenlos).

GPT-OSS-120B ist auch ein moeglicher kostenloser Skriptautor; ein Vergleich
mit Gemini fuer unsere Kanaele steht noch aus (siehe KI-MODELLE.md).
Fruehere Pro-Kontingentmessungen gelten nur fuer das konkrete Projekt,
nicht pauschal fuer alle kostenlosen API-Angebote. Hier schreibt weiterhin
Gemini, GPT-OSS-120B (Groq) prueft unabhaengig und die Zahlenprobe (zahlen.py)
prueft obendrauf. Ein Zweitpruefer ist keine Garantie fehlerfreier Fakten.

Grenzen Groq-Gratistarif (GEPRUEFT): 1.000 Anfragen/Tag, 200.000 Tokens/Tag,
8.000 Tokens/Minute. Darum bekommt der Pruefer nur die Quellabschnitte, die zu
den geprueften Saetzen passen (auszug), nicht den ganzen Artikel.
Fehlt GROQ_API_KEY oder ist Groq nicht erreichbar: None (kein Abbruch).
"""
import json, os, re, time, urllib.error, urllib.request
import prompts

MODELLE = ['openai/gpt-oss-120b', 'qwen/qwen3.8-27b']
GRENZE_ZEICHEN = 14000  # ~3.500 Tokens Quelle + Skript + Antwort < 8.000 Tokens/Minute


def _saetze(absatz):
    return [s for s in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"(])', absatz.strip()) if s]


def auszug(quelle, text, grenze=GRENZE_ZEICHEN):
    """Je Satz des Textes der Quellsatz mit den meisten gemeinsamen Namen/Zahlen/Woertern,
    danach dessen Nachbarsaetze als Kontext - in Originalreihenfolge, bis zur Zeichengrenze.

    GEMESSEN 09.10.2026 (Langvideo Netflix, Run 37945779063): Die alte Auswahl ganzer Absaetze
    nach Gesamtueberschneidung mit dem 7.000-Zeichen-Skript liess den Absatz mit „Breaking Bad"
    weg; der Pruefer meldete einen woertlich belegten Satz als „nicht in der Quelle" und sperrte
    das Video viermal. Bei langen Texten passt jeder Absatz ein bisschen - darum je Satz suchen."""
    if len(quelle) <= grenze:
        return quelle
    namen = lambda s: {w.lower() for w in re.findall(r'\b(?:[A-Z][\w.-]+|\d[\d,.]*)\b', s)}
    woerter = lambda s: {w[:6] for w in re.findall(r'[a-z]{5,}', s.lower())}  # flower = flowers
    # Webseiten kommen mit harten Zeilenumbruechen mitten im Satz ("...templates are\nstarting points."): umbrochene
    # Zeilen (ohne Satzzeichen am Ende, naechste klein) wieder zu einem Satz verbinden.
    quelle = re.sub(r'(?<![.!?:;])\n(?=[a-z])', ' ', quelle)
    absaetze = [_saetze(a) for a in re.split(r'\n+', quelle) if a.strip()]
    orte = [(a, s) for a, saetze in enumerate(absaetze) for s in range(len(saetze))]
    merk = [(namen(absaetze[a][s]), woerter(absaetze[a][s])) for a, s in orte]
    # GEMESSEN 29.10.2026 (KI 40943763878): "Gemini"/"OpenAI" stehen in fast jedem Satz der eigenen Doku und zaehlten
    # dreifach - "const client = new OpenAI ();" schlug den Beleg "content ... is non-deterministic ... art and science".
    # Haeufige Namen/Woerter zaehlen weniger, seltene (Belegwoerter) voll.
    haeufig = {}
    for mn, mw in merk:
        for x in mn | {'w:' + y for y in mw}:
            haeufig[x] = haeufig.get(x, 0) + 1
    gewicht = lambda x, voll: voll if haeufig.get(x, 0) <= 3 else 1 if haeufig.get(x, 0) <= 12 else 0
    treffer = {}  # Quellsatz-Index -> beste Punktzahl
    for satz in _saetze(text.replace('\n', ' ')):
        n, w = namen(satz), woerter(satz)
        punkte = [sum(gewicht(x, 3) for x in n & mn) + sum(gewicht('w:' + y, 2) for y in w & mw) for mn, mw in merk]
        if punkte and max(punkte) < 3:  # Quelle wiederholt dieselben Woerter ueberall: ungewichtet wie bisher
            punkte = [3 * len(n & mn) + len(w & mw) for mn, mw in merk]
        # GEMESSEN 29.10.2026 (KI 40943763878): nur der EINE beste Quellsatz - die Kopfzeile "Official Google Gemini
        # ... page" schlug den echten Beleg ("...bouquets of / dried flowers? Create a list of 5 options"), der ueber
        # einen Zeilenumbruch geteilt war. Von 14.000 erlaubten Zeichen kamen 580 an; fuenf Sperren fuer belegte Saetze.
        # Jetzt die vier besten Saetze und Nachbarn auch ueber Zeilenumbrueche hinweg.
        for i in sorted(range(len(punkte)), key=lambda k: -punkte[k])[:4]:
            if punkte[i] >= 3:
                treffer[i] = max(treffer.get(i, 0), punkte[i])
    nimm, laenge = set(), 0
    # Erst die Belege (beste zuerst), dann Nachbarsaetze als Kontext.
    kandidaten = sorted(treffer, key=lambda i: -treffer[i])
    kandidaten += [j for d in (1, 2) for i in list(kandidaten) for j in (i - d, i + d) if 0 <= j < len(orte)]
    for i in kandidaten:
        a, s = orte[i]
        if i in nimm or laenge + len(absaetze[a][s]) + 1 > grenze:
            continue
        nimm.add(i); laenge += len(absaetze[a][s]) + 1
    teile = {}
    for i in sorted(nimm):
        a, s = orte[i]
        teile.setdefault(a, []).append(absaetze[a][s])
    return '\n'.join(' '.join(saetze) for saetze in teile.values())


def pruefen(text, quelle, art='YouTube Short script'):
    """Gibt {'ok': bool, 'probleme': [...], 'modell': ...} oder None (nicht verfuegbar)."""
    schluessel = os.environ.get('GROQ_API_KEY')
    if not schluessel:
        return None
    auftrag = (prompts.DATEN + prompts.FAKTEN + f'You are an independent fact checker for a {art}. Check every factual claim in the TEXT strictly '
               'against the SOURCE. A claim is a problem if the source does not support it, if it is exaggerated, '
               'if a number/date/name differs, or if it is an invented quote or scene. Ignore style. '
               'For each problem set "schwer": true if a number, date, name, place or event is WRONG or invented; '
               'false if it is only an unsupported detail or exaggeration ("immediately", "broke", "millions"). '
               'Quote the exact clause and identify the missing or contradictory source support. '
               # GEMESSEN 29.10.2026 (KI 40943763878, 5 Sperren): gemeldet wurden auch "Be sure to like, share and save",
               # "briefing a very literal intern", "Her prompt says 'help me sell flowers'" und "No earnings promised".
               'NOT claims, never list them: the request to like, share and save the video; jokes, sarcasm, '
               'analogies and clearly figurative comparisons (e.g. "like briefing a very literal intern"); clearly '
               'hypothetical viewer examples (e.g. "your prompt says \'help me sell flowers\'"); statements that '
               'something is NOT promised or NOT shown. '
               'Accurate paraphrases are acceptable; do not invent a mismatch. When the excerpt lacks '
               'evidence, state that limitation rather than claiming the event never happened. '
               'Answer as JSON: {"probleme": [{"satz": "<exact sentence>", "fehler": "<what is wrong>", '
               '"schwer": true|false}, ...]} - an empty list if everything is supported.\n\n'
               # ~4 Zeichen je Token: Quelle + Text + Antwort unter 8.000 Tokens/Minute
               f'SOURCE:\n{auszug(quelle, text, min(GRENZE_ZEICHEN, 24000 - len(text)))}\n\nTEXT:\n{text}')
    for modell in MODELLE:
        for versuch in range(2):
            try:
                r = urllib.request.Request(
                    'https://api.groq.com/openai/v1/chat/completions',
                    data=json.dumps({'model': modell, 'temperature': 0.1, 'response_format': {'type': 'json_object'},
                                     'messages': [{'role': 'user', 'content': auftrag}]}).encode(),
                    headers={'Authorization': 'Bearer ' + schluessel, 'Content-Type': 'application/json',
                             'User-Agent': 'Contentfabrik/1.0'})
                d = json.load(urllib.request.urlopen(r, timeout=120))
                a = json.loads(d['choices'][0]['message']['content'])
                # GEMESSEN 04.10.2026 (6 echte Skripte): Jede verfaelschte Jahreszahl
                # erkannt, aber 5 von 6 bestandenen Skripten gemeldet - fast immer
                # Ausschmueckungen („immediately", „broke"). Als harte Sperre fiele fast
                # alles durch. Darum: schwer (falsche Zahl/Name/Ereignis) sperrt,
                # leicht geht als Auftrag in die Story-Ueberarbeitung.
                ps = a.get('probleme')
                if not isinstance(ps, list) or any(not isinstance(p, dict) or type(p.get('schwer')) is not bool
                        or not isinstance(p.get('satz'), str) or not isinstance(p.get('fehler'), str) for p in ps):
                    raise ValueError('Unvollstaendige Zweitpruefer-Antwort')
                text_ = lambda p: f"{str(p.get('satz', ''))[:160]} - {p.get('fehler', '')}"
                schwer = [text_(p) for p in ps if p.get('schwer')]
                return {'ok': not schwer, 'probleme': schwer, 'leicht': [text_(p) for p in ps if not p.get('schwer')],
                        'modell': modell}
            except urllib.error.HTTPError as e:
                inhalt = e.read().decode(errors='replace')
                if e.code == 429 and 'per day' in inhalt.lower():
                    break  # Tageskontingent dieses Modells leer
                time.sleep(20 if e.code == 429 else 5)  # Minutengrenze: kurz warten
            except Exception:
                time.sleep(5)
    print('Zweitpruefer (Groq) nicht erreichbar - nur Gemini + Zahlenprobe')
    return None
