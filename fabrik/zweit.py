"""Zweitpruefer: ein Modell einer ANDEREN Firma prueft die Fakten (Groq, kostenlos).

GEMELDET 04.10.2026: „Fuer die komplette Pipeline brauchen wir richtige
kostenlose hoehere Modelle." GEPRUEFT: Ein kostenloses Modell, das klar besser
schreibt als Gemini Flash, gibt es nicht (Gemini Pro: Gratis-Kontingent 0).
Der echte Gewinn: Zwei Modelle verschiedener Firmen uebersehen seltener
denselben Fehler. Gemini schreibt, GPT-OSS-120B (Groq) prueft unabhaengig,
die Zahlenprobe (zahlen.py) prueft obendrauf.

Grenzen Groq-Gratistarif (GEPRUEFT): 1.000 Anfragen/Tag, 200.000 Tokens/Tag,
8.000 Tokens/Minute. Darum bekommt der Pruefer nur die Quellabschnitte, die zu
den geprueften Saetzen passen (auszug), nicht den ganzen Artikel.
Fehlt GROQ_API_KEY oder ist Groq nicht erreichbar: None (kein Abbruch).
"""
import json, os, re, time, urllib.error, urllib.request
import prompts

MODELLE = ['openai/gpt-oss-120b', 'qwen/qwen3.8-27b']
GRENZE_ZEICHEN = 14000  # ~3.500 Tokens Quelle + Skript + Antwort < 8.000 Tokens/Minute


def auszug(quelle, text, grenze=GRENZE_ZEICHEN):
    """Die Absaetze der Quelle, die Namen, Zahlen und Woerter mit dem Text teilen -
    in Originalreihenfolge, bis zur Zeichengrenze."""
    if len(quelle) <= grenze:
        return quelle
    merkmale = lambda s: {w.lower() for w in re.findall(r'\b(?:[A-Z][\w.-]+|\d[\d,.]*)\b', s)}
    ziel = merkmale(text)
    absaetze = [a for a in re.split(r'\n+', quelle) if a.strip()]
    rang = sorted(range(len(absaetze)), key=lambda i: -len(merkmale(absaetze[i]) & ziel))
    nimm, laenge = set(), 0
    for i in rang:
        if laenge + len(absaetze[i]) > grenze:
            continue
        nimm.add(i); laenge += len(absaetze[i])
    return '\n'.join(absaetze[i] for i in sorted(nimm))


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
