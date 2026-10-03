"""Lange Videos (Mini-Doku, 9-11 Minuten) - Schritt 1: das Skript.

GEMELDET 03.10.2026: „Ich moechte schoen Geld damit machen und nicht einfach so
hochladen." GEPRUEFT: Shorts bringen ca. 0,03-0,08 $ je 1.000 Aufrufe, lange
Videos 1-10 $ und mehr (Bildung/Technik oben) - das 20- bis 30-fache. Ab
8 Minuten erlaubt YouTube zusaetzlich Werbung mitten im Video. Darum
9-11 Minuten (1.400-1.800 gesprochene Woerter).

YouTube-Regel „inauthentic content" (verschaerft 2026): Vorlagen-Massenware,
vorgelesene Fremdtexte und Diashows ohne Mehrwert werden nicht monetarisiert.
Darum: eigene Erzaehlung mit Spannungsbogen, nur Fakten aus der Quelle, nie
deren Wortlaut - und jede Folge mit eigenem Aufbau.

Aufruf:  python fabrik/doku.py "Levi Strauss & Co." ausgabe/doku.json [--telegram]
"""
import json, os, re, sys, urllib.parse, urllib.request, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from skript import gemini, PRUEF_SCHEMA  # noqa: E402
import trends, zahlen  # noqa: E402

WOERTER = (1400, 1800)  # ~150-165 Woerter/Minute bei Tempo 1.05 -> 9-11 Minuten
MIN_QUELLE = 8000       # darunter reicht der Stoff nicht fuer 10 Minuten ohne Strecken

SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'titel': {'type': 'STRING'},
        'thumbnail_text': {'type': 'STRING'},
        'einstieg': {'type': 'STRING'},
        'kapitel': {'type': 'ARRAY', 'items': {'type': 'OBJECT', 'properties': {
            'titel': {'type': 'STRING'}, 'text': {'type': 'STRING'}, 'bild': {'type': 'STRING'}},
            'required': ['titel', 'text', 'bild']}},
        'schluss': {'type': 'STRING'},
        'beschreibung': {'type': 'STRING'},
        'tags': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
    },
    'required': ['titel', 'thumbnail_text', 'einstieg', 'kapitel', 'schluss', 'beschreibung', 'tags'],
}

# Halten ueber 10 Minuten ist etwas anderes als ueber 60 Sekunden: offene
# Fragen ueber Kapitelgrenzen, ein Wendepunkt in der Mitte, Aufloesung am Ende.
KATEGORIEN = {
    'einstieg': 'do the first 30 seconds drop the viewer into a dramatic moment and pose one big question?',
    'offene_schleifen': 'does every chapter end with an open question that makes the next chapter necessary?',
    'wendepunkt': 'is there a real turning point or reversal around the middle?',
    'menschen': 'are there concrete people with goals, obstacles and decisions (not just dates)?',
    'ueberraschung': 'at least three genuine "I did not know that" moments?',
    'tempo': 'no filler, no repetition, every paragraph moves the story forward?',
    'aufloesung': 'does the ending answer the opening question in a satisfying way?',
}
STORY_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'note': {'type': 'INTEGER'},
        'kategorien': {'type': 'OBJECT', 'properties': {k: {'type': 'INTEGER'} for k in KATEGORIEN},
                       'required': list(KATEGORIEN)},
        'schwaechen': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
    },
    'required': ['note', 'kategorien', 'schwaechen'],
}


def gesprochen(d):
    return [d['einstieg']] + [k['text'] for k in d['kapitel']] + [d['schluss']]


def woerter(d):
    return sum(len(t.split()) for t in gesprochen(d))


def auftrag(quelle):
    return (
        'Write the narration for a 9-11 minute YouTube documentary for the channel "Business Origin Stories" '
        '(how famous companies really started). Audience: curious English-speaking adults, no prior knowledge.\n'
        f'LENGTH: {WOERTER[0]}-{WOERTER[1]} spoken words in total (einstieg + all kapitel + schluss). '
        'This is checked by code.\n'
        'STRUCTURE:\n'
        # GEMESSEN 04.10.2026 (Harley-Davidson, Story 7/10): Die Folge begann mit
        # dem Gruendungsjahr und las sich wie eine Zeitleiste („menschen" 6/10,
        # Schluss eine Floskel). Profi-Dokus beginnen mit der groessten Krise
        # und erzaehlen von dort zurueck - ohne etwas zu erfinden.
        '- First find the CENTRAL CONFLICT in the whole source: the moment the company came closest to failing '
        '(bankruptcy, takeover, collapse, a fatal mistake) - often decades after the founding.\n'
        '- einstieg (70-110 words): open INSIDE that crisis (what was at stake, in concrete numbers), then jump '
        'back: "To understand how it got here, we have to go back to ..." Pose the ONE big question: did they '
        'survive, and how? No "in this video", no greeting.\n'
        '- Tell it through the decisions of named people (who decided what, what they risked, what happened). '
        'Only feelings or motives the source states.\n'
        '- 5-7 kapitel, 180-300 words each, in time order. Each has a short title (2-5 words) and ends with an '
        'open question or a hint of what goes wrong next, so the viewer must keep watching.\n'
        '- A real turning point or reversal around the middle.\n'
        '- The chapter that reaches the crisis from the einstieg is the climax: slow down, give it the most words.\n'
        '- schluss (80-140 words): answer the big question from the einstieg with a concrete fact from the source '
        '(what saved them, where they stand today), then one memorable final line that is NOT a generic '
        'platitude ("through loyalty and reinvention" is banned). No "like and subscribe" begging.\n'
        # GEMESSEN 04.10.2026: 21 von 91 Saetzen ueber 22 Woerter; Zahlen teils
        # als zerbrochene Woerter („thirty-,seven hundred three" statt 3,703).
        'STYLE: written for the ear - one idea per sentence, at most 20 words, active voice. Write numbers as '
        'digits (1903, 3,703), never as words. Concrete names, places, numbers and decisions. Explain '
        'every term a beginner would not know. No filler, no repetition, no clichés ("little did they know", '
        '"the rest is history", "game changer").\n'
        'FACTS: every factual claim MUST come from the SOURCE below. Use your own words - never copy its '
        'sentences. No invented dialogue, quotes, feelings or scenes. If the source does not say it, leave it out.\n'
        'bild: for each kapitel, 3-6 English words describing what should be on screen (for photo/footage search).\n'
        'titel: YouTube title, max 65 characters, curiosity without lying. thumbnail_text: 2-4 words.\n'
        'beschreibung: 2-3 sentences for the YouTube description (no hashtags). tags: 8-12 search tags.\n\n'
        f"SOURCE (English Wikipedia, \"{quelle['name']}\"):\n{quelle['text']}\n")


def pruefen(d, quelle):
    """Faktencheck der KI PLUS Zahlenprobe im Code (zahlen.py)."""
    p, _ = gemini('You are a strict fact checker for a documentary narration. Check every factual claim against '
                  'the SOURCE. Mark ok=false if ANY claim is not supported by the source, exaggerated, or an '
                  'invented quote/scene. List each problem briefly with the sentence it refers to.\n\n'
                  f"SOURCE:\n{quelle['text']}\n\nNARRATION:\n" + json.dumps(d, ensure_ascii=False),
                  PRUEF_SCHEMA, temperatur=0.1)
    fehlt = zahlen.unbelegt({'teile': [{'text': t} for t in gesprochen(d)]}, [quelle['name'] + ' ' + quelle['text']])
    if fehlt:
        print('Zahlenprobe: nicht in der Quelle:', fehlt)
        p = {'ok': False, 'probleme': p['probleme'] + [
            'Number not in the source - remove it or use the exact number: ' + z for z in fehlt]}
    return p


def story(d):
    s, _ = gemini('You are a senior documentary editor at a top YouTube channel. Judge ONLY whether viewers '
                  'will watch this narration to the end (retention), not the facts. Score each 1-10:\n'
                  + '\n'.join(f'- {k}: {v}' for k, v in KATEGORIEN.items())
                  + '\nOverall "note" 1-10 (strict: 9+ only for a story you would binge). List concrete '
                    'weaknesses, each with the exact sentence it refers to and how to fix it.\n\n'
                  + json.dumps(d, ensure_ascii=False), STORY_SCHEMA, temperatur=0.2)
    return s


def schreiben(text):
    """Bis zu 3 Versuche, bis die Laenge stimmt (zu kurz = keine Mid-Roll-Werbung)."""
    zusatz = ''
    for versuch in range(3):
        d, _ = gemini(text + zusatz, SCHEMA, temperatur=0.8)
        n = woerter(d)
        if WOERTER[0] <= n <= WOERTER[1] + 150 and 5 <= len(d['kapitel']) <= 7:
            return d, None
        print(f'Versuch {versuch + 1}: {n} Woerter, {len(d["kapitel"])} Kapitel')
        zusatz = (f'\nYour previous draft had {n} spoken words and {len(d["kapitel"])} chapters. It MUST have '
                  f'{WOERTER[0]}-{WOERTER[1]} words and 5-7 chapters - add depth from the source, not filler.')
    return d, f'Laenge {n} Woerter / {len(d["kapitel"])} Kapitel'


def main(artikel, aus, telegram=False):
    quelle = trends.wikipedia(artikel, grenze=30000)
    if not quelle or len(quelle['text']) < MIN_QUELLE:
        sys.exit(f"Quelle zu kurz fuer 10 Minuten: {len(quelle['text']) if quelle else 0} Zeichen")
    print(f"Quelle: {quelle['name']} ({len(quelle['text'])} Zeichen)")
    d, mangel = schreiben(auftrag(quelle))
    p = pruefen(d, quelle)
    if not p['ok'] or mangel:
        d, mangel = schreiben(auftrag(quelle) + '\nFix these problems:\n- '
                              + '\n- '.join(p['probleme'] + ([mangel] if mangel else [])))
        p = pruefen(d, quelle)
    s = story(d)
    print(f"Story: {s['note']}/10 {s['kategorien']} | {woerter(d)} Woerter | Fakten ok: {p['ok']}")
    # Ziel 10/10 (GEMELDET): mit dem konkreten Feedback neu schreiben, jede Fassung
    # muss wieder durch die Faktenpruefung - Spannung nie auf Kosten der Wahrheit.
    # Drei Runden: Text kostet kaum Rechenzeit, das Video danach ~10x mehr.
    for runde in range(3):
        if s['note'] >= 10 or not p['ok']:
            break
        neu, m = schreiben(auftrag(quelle) + '\nREWRITE for stronger retention (same facts). The editor found:\n- '
                           + '\n- '.join(s['schwaechen']) + '\nPrevious version:\n' + json.dumps(d, ensure_ascii=False))
        if m:
            continue
        p2 = pruefen(neu, quelle)
        if not p2['ok']:
            print('Neue Fassung fiel durch die Faktenpruefung - verworfen')
            continue
        s2 = story(neu)
        print(f"Story neu: {s2['note']}/10 (vorher {s['note']}) | {woerter(neu)} Woerter")
        if s2['note'] > s['note']:
            d, p, s = neu, p2, s2
    d.update({'quelle': {'name': quelle['name'], 'url': quelle['url']}, 'pruefung': p, 'story': s,
              'woerter': woerter(d), 'minuten_ca': round(woerter(d) / 155, 1)})
    Path(aus).parent.mkdir(parents=True, exist_ok=True)
    Path(aus).write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding='utf-8')
    md = Path(aus).with_suffix('.md')
    md.write_text(lesefassung(d), encoding='utf-8')
    print(f"Fertig: {d['titel']} | {d['woerter']} Woerter (~{d['minuten_ca']} Min.) | Story {s['note']}/10 | "
          f"Fakten {'ok' if p['ok'] else 'NICHT ok'}")
    if telegram:
        senden(md, d)


def lesefassung(d):
    teile = [f"# {d['titel']}", f"Thumbnail: {d['thumbnail_text']}",
             f"~{d['minuten_ca']} Minuten · {d['woerter']} Wörter · Story {d['story']['note']}/10 · "
             f"Fakten {'geprüft ✅' if d['pruefung']['ok'] else '⚠️ ' + '; '.join(d['pruefung']['probleme'])}",
             f"Quelle: {d['quelle']['url']}", '## Einstieg', d['einstieg']]
    for i, k in enumerate(d['kapitel'], 1):
        teile += [f"## {i}. {k['titel']}", f"[Bild: {k['bild']}]", k['text']]
    teile += ['## Schluss', d['schluss'], '## Was die Story-Prüfung noch bemängelt'] + \
             [f'- {w}' for w in d['story']['schwaechen']]
    return '\n\n'.join(teile) + '\n'


def senden(md, d):
    token, chat = os.environ['TELEGRAM_BOT_TOKEN'], os.environ['TELEGRAM_CHAT_ID']
    grenze = uuid.uuid4().hex
    felder = {'chat_id': chat, 'caption': f"📄 Lange Folge (Entwurf): {d['titel']}\n~{d['minuten_ca']} Min. · "
                                          f"Story {d['story']['note']}/10 · Fakten "
                                          f"{'✅' if d['pruefung']['ok'] else '⚠️'}\nZum Lesen öffnen."}
    koerper = b''.join(f'--{grenze}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                       for k, v in felder.items())
    koerper += (f'--{grenze}\r\nContent-Disposition: form-data; name="document"; filename="{md.name}"\r\n'
                'Content-Type: text/markdown\r\n\r\n').encode() + md.read_bytes() + f'\r\n--{grenze}--\r\n'.encode()
    r = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendDocument', data=koerper,
                               headers={'Content-Type': f'multipart/form-data; boundary={grenze}'})
    print('Telegram:', json.load(urllib.request.urlopen(r, timeout=60)).get('ok'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], '--telegram' in sys.argv)
