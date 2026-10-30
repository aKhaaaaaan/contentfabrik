"""Mehrere echte Einstellungen je Sprechphase; Ton und Wortzeiten bleiben erhalten."""
import copy
import hashlib
import json
import math
import os
import re
from pathlib import Path
import dramaturgie
import prompts

# Nutzerentscheidung 15.10.2026: Bild-Prompts als Kanalvorlage mit Variablen statt freier Szenentexte -
# praezise, pruefbar und fuer neue Kanaele/Themen ohne Sonderregeln skalierbar. Die KI fuellt nur kurze
# Felder, der Code setzt den Prompt nach kanaele/<slug>.json 'bildvorlage' zusammen.
EINSTELLUNGEN = ['close-up', 'medium shot', 'wide shot', 'detail shot', 'over-the-shoulder shot']
VORLAGE_FELDER = ('motiv', 'aktion', 'ort', 'epoche', 'einstellung')

SCHEMA = {'type': 'OBJECT', 'properties': {'einstellungen': {'type': 'ARRAY', 'items': {
    'type': 'OBJECT', 'properties': {
        'index': {'type': 'INTEGER'}, 'bildmodus': {'type': 'STRING', 'enum': ['foto', 'stock', 'illustration', 'karte', 'demo', 'figur', 'asset']},
        'asset': {'type': 'STRING'},
        'figur': {'type': 'BOOLEAN'},
        'suche': {'type': 'STRING'}, 'szene': {'type': 'STRING'}, 'motiv': {'type': 'STRING'},
        'aktion': {'type': 'STRING'}, 'ort': {'type': 'STRING'}, 'epoche': {'type': 'STRING'},
        'details': {'type': 'STRING'},
        'einstellung': {'type': 'STRING', 'enum': EINSTELLUNGEN}},
    'required': ['index', 'bildmodus', 'suche', 'szene', 'motiv']}}}, 'required': ['einstellungen']}


def motivziel(s):
    if dramaturgie.videoformat(s) == 'lang':
        return 0
    import kanalstandard
    profil = kanalstandard.nach_name(s.get('kanal')) or {}
    wert = profil.get('short_motive_min', 0)
    if type(wert) is not int or not 0 <= wert <= 40:
        raise ValueError('short_motive_min muss eine ganze Zahl zwischen 0 und 40 sein')
    return wert


def feste_regie(s):
    """Vollstaendige feste Regie: jede Phase hat eine komplette bildfolge, die den Bildplan bestimmt."""
    return bool(s.get('teile')) and all(
        t.get('bildfolge') and all(all(v.get(k) for k in ('bildmodus', 'suche', 'szene', 'motiv'))
                                  for v in t['bildfolge']) for t in s['teile'])


def slots(s, laengen, woerter):
    ziel = 8 if dramaturgie.videoformat(s) == 'lang' else 4.5
    anzahlen = [max(1, math.ceil(d / ziel)) for d in laengen]
    minimum = motivziel(s) if sum(laengen) >= 30 else 0
    redaktionell = len(s['teile']) == len(laengen) and feste_regie(s)
    if redaktionell:
        # Eine fertige Regie verteilt ihre Motive bewusst auf die Sprechphasen.
        # Der automatische Dichteausgleich verschob zuvor einen Slot in eine
        # andere Phase und verlangte dort ein nicht vorgesehenes neunzehntes Bild.
        anzahlen = [len(t['bildfolge']) for t in s['teile']]
        if sum(anzahlen) < minimum:
            raise ValueError('Redaktionelle Bildfolge unterschreitet die Mindestzahl der Motive')
        for i,(d,n) in enumerate(zip(laengen,anzahlen)):
            if d/n > (10 if dramaturgie.videoformat(s) == 'lang' else 6):
                raise ValueError(f'Phase {i}: redaktionelle Bildfolge haelt ein Motiv zu lange')
    if not redaktionell and dramaturgie.videoformat(s) == 'short' and woerter:
        return satz_slots(s, laengen, woerter, minimum)
    # Die laengste Einstellung teilen, ohne Sprechphasen oder Wortzeiten zu veraendern.
    while not redaktionell and anzahlen and sum(anzahlen) < minimum:
        phase = max(range(len(laengen)), key=lambda i: laengen[i] / anzahlen[i])
        anzahlen[phase] += 1
    aus, start = [], 0.0
    for phase, (t, dauer) in enumerate(zip(s['teile'], laengen)):
        anzahl = anzahlen[phase]
        for j in range(anzahl):
            a, b = start + dauer * j / anzahl, start + dauer * (j + 1) / anzahl
            text = ' '.join(w['w'] for w in woerter if a <= (w['s'] + w['e']) / 2 < b)
            aus.append({'index': len(aus), 'phase': phase, 's': a, 'dauer_s': b - a,
                        'text': text or t['text'], 'phase_text': t['text']})
        start += dauer
    return aus


def satz_slots(s, laengen, woerter, minimum=0, kurz=1.5, lang=6.0):
    """Nutzerentscheidung 15.10.2026: ein Motiv je gesprochenem Satz statt fester 18.

    Bei 18 Motiven in 45 s wechselte das Bild alle 2,5 s; kein Satzfetzen liess sich wortgenau
    bebildern (Louis Vuitton 2/18 beim strengen Pruefer). Saetze ueber 6 s werden geteilt, Saetze
    unter 1,5 s an den Nachbarn gehaengt. Sprechphasen und Wortzeiten bleiben unveraendert.
    """
    roh, start = [], 0.0
    for phase, (t, dauer) in enumerate(zip(s['teile'], laengen)):
        ende = start + dauer
        ws = [w for w in woerter if start <= (w['s'] + w['e']) / 2 < ende]
        a, satz = start, []
        for k, w in enumerate(ws):
            satz.append(w['w'])
            if re.search(r'[.!?]["\')]*$', w['w']) or k == len(ws) - 1:
                b = ws[k + 1]['s'] if k + 1 < len(ws) else ende
                roh.append({'phase': phase, 's': a, 'e': b if k + 1 < len(ws) else ende,
                            'text': ' '.join(satz), 'phase_text': t['text']})
                a, satz = b, []
        if not ws:
            roh.append({'phase': phase, 's': start, 'e': ende, 'text': t['text'], 'phase_text': t['text']})
        start = ende
    # Zu kurze Saetze innerhalb derselben Phase an den Vorgaenger (sonst Nachfolger) haengen.
    zus = []
    for x in roh:
        if zus and x['e'] - x['s'] < kurz and zus[-1]['phase'] == x['phase']:
            zus[-1].update(e=x['e'], text=zus[-1]['text'] + ' ' + x['text'])
        elif zus and zus[-1]['e'] - zus[-1]['s'] < kurz and zus[-1]['phase'] == x['phase']:
            x = dict(x, s=zus[-1]['s'], text=zus[-1]['text'] + ' ' + x['text']); zus[-1] = x
        else:
            zus.append(dict(x))
    # Lange Saetze teilen; fehlen dann noch Motive, den laengsten weiter teilen.
    teile = [max(1, math.ceil((x['e'] - x['s']) / lang - 1e-9)) for x in zus]
    while sum(teile) < minimum and zus:
        i = max(range(len(zus)), key=lambda j: (zus[j]['e'] - zus[j]['s']) / teile[j])
        teile[i] += 1
    aus = []
    for x, n in zip(zus, teile):
        for j in range(n):
            a = x['s'] + (x['e'] - x['s']) * j / n
            b = x['s'] + (x['e'] - x['s']) * (j + 1) / n
            text = x['text'] if n == 1 else (' '.join(w['w'] for w in woerter if a <= (w['s'] + w['e']) / 2 < b)
                                             or x['text'])
            aus.append({'index': len(aus), 'phase': x['phase'], 's': a, 'dauer_s': b - a,
                        'text': text, 'phase_text': x['phase_text']})
    return aus


ETAPPE = 30


def aktuelles_feedback(regeln, maximal=2500):
    """Neueste optionale Redaktionshinweise, ganze Eintraege im Textbudget."""
    aus, zeichen = [], 0
    for regel in reversed(regeln):
        if not isinstance(regel, str):
            continue
        if zeichen + len(regel) > maximal:
            break
        aus.append(regel)
        zeichen += len(regel)
    return list(reversed(aus))


def etappen(zeitplan, groesse=ETAPPE):
    """GEMESSEN 08.10.2026 (Langvideo-Pilot 37826232160): fuer ~80 Einstellungen lieferte das
    Lite-Modell nur 24 -> 'deckt nicht alle Sprechphasen ab', Versuch verloren. Lange Plaene
    darum in Etappen; ein Short (<= 30 Einstellungen) bleibt EIN Auftrag wie bisher."""
    return [zeitplan[i:i + groesse] for i in range(0, len(zeitplan), groesse)] or [[]]


# GEMELDET 10.10.2026 (Business-Short Netflix): „Die Motive passen wenig zu den Woertern."
# Gemessen: "streams overtook DVD shipments" -> jemand oeffnet einen DVD-Umschlag; "$7.99 a month"
# -> Kalender; Like/Share-Satz -> Blick auf die Uhr. Den Plan machte Flash-Lite (schwaechstes Modell).
# Planen jetzt mit starken Modellen zuerst, Lite nur als Rueckfall; danach eine Bezugspruefung.
PLANEN = ['gemini-3.8-flash', 'gemini-flash-latest', 'gemini-3.6-flash', 'gemini-3.5-flash',
          'gemini-flash-lite-latest', 'gemini-3.5-flash-lite']
BEZUG_MIN = 7
BEZUG_SCHEMA = {'type': 'OBJECT', 'properties': {'pruefung': {'type': 'ARRAY', 'items': {
    'type': 'OBJECT', 'properties': {'index': {'type': 'INTEGER'}, 'note': {'type': 'INTEGER'},
                                     'motiv': {'type': 'STRING'}, 'szene': {'type': 'STRING'},
                                     'suche': {'type': 'STRING'}, 'aktion': {'type': 'STRING'},
                                     'details': {'type': 'STRING'}},
    'required': ['index', 'note', 'motiv', 'szene', 'suche']}}}, 'required': ['pruefung']}


# GEMESSEN 16.10.2026 (Business Airbnb 38873412464 Einstellung 6, VW-Langvideo Einstellung 47): der Auftrag
# beschrieb BEIDE Kanalfiguren, der Planer malte die KI-Figur (Lederjacke, cyan Brille) in Business-Szenen.
# Jetzt nennt der Auftrag nur die eigene Figur; fremde_figur() faengt verbliebene Verwechslungen ab.
FIGUR = {'Business Origin Stories': 'blue-eyed man with fedora, grey suit, dark tie and gold pocket watch',
         'AI Tools Explained': 'black-haired man with black leather jacket and cyan glowing glasses'}
FIGUR_MERKMALE = {'Business Origin Stories': r'\b(?:fedora|pocket watch)\b',
                  'AI Tools Explained': r'\b(?:leather jacket|cyan(?: glowing)? glasses)\b'}


def fremde_figur(szene, kanal):
    """Beschreibt die Szene die Figur des ANDEREN Kanals?"""
    return any(re.search(muster, szene or '', re.I) for name, muster in FIGUR_MERKMALE.items()
               if kanal in FIGUR_MERKMALE and name != kanal)


def szene_aus_vorlage(d, vorlage, text='', kontext='', namen=frozenset()):
    """Bild-Prompt aus der Kanalvorlage; fehlt ein Feld oder ist es unbrauchbar, bleibt die freie Szene.

    Kostenlos geprueft: alle Felder gefuellt, Einstellungsgroesse aus der festen Liste und das Motiv
    woertlich aus dem gesprochenen Satz - sonst wuerde die Vorlage ein falsches Motiv nur sauberer malen."""
    if not vorlage or d.get('bildmodus') not in ('illustration', 'foto', 'stock'):
        return d.get('szene')
    werte = {k: re.sub(r'\s+', ' ', str(d.get(k) or '')).strip(' .,;:') for k in VORLAGE_FELDER}
    if not all(werte.values()) or werte['einstellung'] not in EINSTELLUNGEN \
            or (text and not woertlich(werte['motiv'], text, kontext, namen)):
        return d.get('szene')
    szene = vorlage.format(**werte)
    # 25.10.2026: Die ersten Codex-Motive beschrieben Material, Form und Zustand praezise.
    # Die Fuenf-Feld-Vorlage verwarf diese Details aus szene (z.B. Vinyl-Luftkammern -> normale
    # Matratze). Eigenes optionales Feld, innerhalb der 500 Zeichen fuer prompts.illustration.
    details = d.get('details')
    if isinstance(details, str) and details.strip():
        details = re.sub(r'\s+', ' ', details).strip(' .,;:')
        budget = min(180, 500 - len(szene) - len('. Visible detail: '))
        if budget > 0:
            if len(details) > budget:
                details = details[:budget].rsplit(' ', 1)[0]
            szene += '. Visible detail: ' + details
    return szene


FUELLWOERTER = {'with', 'from', 'that', 'this', 'their', 'there', 'they', 'into', 'over', 'scene', 'shot',
                'close', 'view', 'person', 'people', 'about', 'while', 'very', 'some'}


# GEMESSEN 23.10.2026 (Moderna, Lauf 39982100730): Saetze wie "million in 2018?", "Vertex in 2016" oder "it raised
# $2 billion" enthalten keinen malbaren Gegenstand. Das woertliche Motiv wurde "million in 2018", die Vorlage
# "close-up of million in 2018 as the clear focal subject" - das Bildmodell malte Bueros, Pruefer 9/13 mit 2/10.
# Fuer solche Begriffe ein fester, malbarer Stellvertreter (Satz UND ganze Sprechphase loesen ihn aus).
# Keine Stellvertreter mit Papier/Schrift (Scheck, Vertrag, Kursanzeige, Akten): Probe 23.10. - das Bildmodell malt
# Kauderwelsch-Schrift, jeder Versuch scheitert. Betraege kommen als echte Zahlenebene (bauen.zahl_momente).
STELLVERTRETER = [
    # GEMESSEN 30.10.2026 (Kongo Gumi 41103117263, 5 Bilder 2-4/10): "Then debts piled up", Verkauf an Takamatsu,
    # "sons and sons-in-law" bekamen "besorgter Mann im Buero", Handschlag, Toepfer - Pruefer: kein Bezug.
    # Vor Geld/Partner: sonst gewinnt der allgemeine Handschlag, der beim Verkauf mit 3/10 durchfiel.
    (r'\b(?:debts?|owed|owing|creditors?|insolven\w*|overspen\w*)\b',
     ['creditors crowding around a worried owner at his counter', 'bailiffs carrying furniture out of a workshop',
      'owner shaking the last coins out of an empty cash box']),
    (r'\b(?:sold|sale|sell\w*|takeover|took over|absorbed|bought out|assets)\b',
     ['new owners in suits touring the old workshop while craftsmen watch',
      'old owner handing a heavy ring of keys to a buyer at the workshop gate']),
    (r'\b(?:heirs?|sons?|daughters?|sons-in-law|son-in-law|adopt\w*|generations?|inherit\w*|passed down'
     r'|successors?|succession)\b',
     ['old master handing his tools to a young heir at a workbench',
      'several generations of one craftsman family standing together in their workshop',
      'father teaching his son a craft at a workbench']),
    (r'\$|\b(?:million|billion|raised?|raising|funding|funded|invest\w*|capital|valu\w*|money|loans?)\b',
     ['investors leaning in around a boardroom table', 'bank vault door swinging open',
      'founder shaking hands with an investor']),
    # nur Mehrzahl: "share" steht in jedem Like/Teilen-Aufruf
    (r'\b(?:shares|stocks?|ipo|nasdaq|exchange|listing|listed)\b',
     ['stock exchange trading bell', 'cheering crowd on a trading floor', 'traders raising hands on a trading floor']),
    (r'\b(?:partners?|partnership|deals?|agreements?|contracts?|merg\w*|acquir\w*|bought|licens\w*)\b',
     ['two executives shaking hands across a table', 'two executives toasting a deal',
      'two teams meeting around one lab bench']),
    # Gruender/Start nicht: "Five founders" sind selbst malbar (Probe 23.10.: wurde sonst zum leeren Schreibtisch)
    (r'\b(?:ceo|appointed|hired|promoted)\b',
     ['executive desk with leather chair', 'new chief executive walking into a boardroom']),
    (r'\b(?:trials?|safety|drugs?|vaccines?|patients?|stud(?:y|ies)|clinical)\b',
     ['rack of sealed sample vials', 'microscope and test tubes', 'scientist holding a vial up to the light']),
    # GEMESSEN 28.10.2026 (Hugo Boss / Rolls-Royce, 4 Bauversuche ohne Video): "voiced profound regret",
    # "joined the Nazi Party", "Sales rose", "board seat" bekamen das Wortmotiv "regret"/"uniform orders"/"Sales rose" -
    # der FLUX-Auftrag strich es als abstrakt, gemalt wurde ein beliebiger Mann im Raum, Pruefer 2/10.
    (r'\b(?:regrets?|apolog\w*|admitted|acknowledg\w*|statement|condemn\w*)\b',
     ['executive reading a statement at a press podium', 'press photographers crowding a podium']),
    (r'\b(?:joined|membership|uniforms?)\b',
     ['rows of finished uniforms on tailor racks', 'tailor fitting a uniform jacket on a mannequin']),
    (r'\b(?:sales|revenue|profits?|turnover|orders|grew|soared|boomed|doubled|tripled)\b',
     ['busy factory floor with stacks of finished goods', 'delivery trucks loaded with crates',
      'crowded shop counter with customers']),
    (r'\b(?:board|chairman|directors?|seat)\b',
     ['executives seated around a long boardroom table', 'new director taking a seat at a boardroom table']),
    (r'\b(?:quit|failed|blocked|halted|stopped|collapsed?|bankrupt\w*|cancel\w*)\b',
     ['empty chair at a cleared desk', 'packed cardboard boxes by a closed door', 'red stop light over a lab door']),
]


def eigennamen(s):
    """Woerter, die im Skript oder seinen Quellen nur als Eigenname vorkommen (gross, mitten im Satz).

    GEMESSEN 23.10.2026 (Probe Moderna): Mit Stellvertretern waehlte der Planer "Moderna", "Bancel", "Alexion"
    als Motiv - woertlich, aber unmalbar (keine Logos, keine echten Gesichter)."""
    texte = [t.get('text', '') for t in s.get('teile') or []] + [b.get('text', '') for b in s.get('belege') or []
                                                                   if isinstance(b, dict)] + [s.get('thema') or '']
    gross, klein = set(), set()
    for t in texte:
        for m in re.finditer(r'(?<![.!?:]\s)(?<!^)\b([A-Za-z][a-z]{2,})\b', str(t)):
            (gross if m.group(1)[0].isupper() else klein).add(m.group(1).lower()[:5])
    return frozenset(gross - klein) | {w.lower()[:5] for w in re.findall(r'[A-Za-z]{3,}', s.get('thema') or '')}


# Probe 23.10.2026: auch "Partners", "safety issues", "shares", "IPO" standen woertlich als Motiv - Begriffe ohne
# Gestalt. Wie Eigennamen: kein malbares Motiv (5-Buchstaben-Staemme wie in woertlich).
ABSTRAKT = frozenset(w[:5] for w in (
    'partners', 'partnership', 'safety', 'issues', 'shares', 'ipo', 'deal', 'deals', 'revenue', 'profit', 'profits',
    'valuation', 'funding', 'growth', 'success', 'strategy', 'sales', 'results', 'billion', 'million', 'percent',
    # 28.10.2026 (Hugo Boss): woertlich, aber unmalbar - "regret", "What changed", "Sales rose" wurden Hauptmotiv
    'regret', 'regrets', 'apology', 'statement', 'membership', 'decision', 'changed', 'change', 'what', 'why',
    'rose', 'grew', 'fell',
    # 30.10.2026 (Kongo Gumi): Schulden, Verkauf, Nachfolge - Vorgaenge ohne eigene Gestalt
    'debts', 'debt', 'sale', 'sold', 'takeover', 'assets', 'succession'))


def malbar_machen(daten, zeitplan, namen=frozenset()):
    """Unmalbare oder doppelte Motive durch einen noch freien Stellvertreter des Slots ersetzen (fest, ohne KI).

    Probe 23.10.2026 (Moderna, drei Planerlaeufe): der Planer liess "Partners"/"IPO" stehen oder nahm denselben
    Scheck zweimal - jedes Mal anders. Die Szene wird dann aus dem Stellvertreter gebaut (aktion entfaellt, die
    Kanalvorlage nimmt sonst die alte Handlung)."""
    texte = {x['index']: (x['text'], x.get('phase_text', '')) for x in zeitplan}
    benutzt, ersetzt = set(), 0
    for d in daten:
        if d.get('bildmodus') not in ('illustration', 'stock', 'foto') or d.get('index') not in texte:
            continue
        text, phase = texte[d['index']]
        motiv = str(d.get('motiv') or '').strip().lower()
        frei = [m for m in stellvertreter(f'{text} {phase}') if m not in benutzt]
        doppelt = motiv in benutzt
        if (doppelt or not woertlich(motiv, text, phase, namen)) and frei:
            d.update(motiv=frei[0], szene=', '.join(x for x in (frei[0], d.get('ort') and 'in ' + str(d['ort']),
                                                                 str(d.get('epoche') or '')) if x))
            d.pop('aktion', None)
            d.pop('details', None)  # Materialmerkmale gehoeren zum ersetzten Gegenstand
            motiv, ersetzt = frei[0], ersetzt + 1
        if motiv in stellvertreter(f'{text} {phase}'):
            benutzt.add(motiv)
    return ersetzt


def stellvertreter(text):
    """Malbare Ersatzmotive fuer Betraege, Jahre, Firmen und abstrakte Geschaeftsschritte im Text."""
    return [m for muster, motive in STELLVERTRETER if re.search(muster, text or '', re.I) for m in motive]


def woertlich(motiv, text, kontext='', namen=frozenset()):
    """Steht mindestens ein tragendes Wort des Motivs im gesprochenen Satz? Kostenlos, ohne KI.

    GEMESSEN 15.10.2026 (Airbnb, Lauf 11962532089): "They put an air mattress in their living room"
    bekam das Motiv "living room breakfast"; die KI-Bezugspruefung liess es stehen, gemalt wurde ein
    Wohnzimmer ohne Matratze, Schlusspruefer 3/10. Ein Motiv nur aus Begleitwoertern ("living room")
    zaehlt nicht: verlangt wird das konkreteste Wort, darum muss JEDES tragende Motivwort im Satz stehen."""
    stamm = lambda w: w.lower()[:5]
    gesagt = {stamm(w) for w in re.findall(r'[A-Za-z]{3,}', text or '')}
    # Ein Stellvertreter zaehlt nur als ganzes Motiv aus der Liste, kein loses Einzelwort daraus
    if (motiv or '').strip().lower() in stellvertreter(f'{text} {kontext}'):
        return True
    tragend = [w for w in re.findall(r'[A-Za-z]{3,}', motiv or '') if w.lower() not in FUELLWOERTER]
    if tragend and all(stamm(w) in namen or stamm(w) in ABSTRAKT for w in tragend):
        return False  # nur ein Firmen-/Personenname: woertlich, aber nicht malbar
    return bool(tragend) and all(stamm(w) in gesagt for w in tragend)


def bezug_pruefen(gemini, teil, daten, namen=frozenset()):
    """Vor dem Malen: zeigt jedes geplante Motiv, was in seinem Slot GESAGT wird? Schwache
    Illustrations-Motive (Note < BEZUG_MIN) werden durch einen woertlicheren Vorschlag ersetzt.
    Faellt die Pruefung aus, bleibt der Plan unveraendert (kein Abbruch)."""
    plan = {d['index']: d for d in daten}
    eintraege = [{'index': x['index'], 'spoken_words': x['text'], 'planned_motif': plan[x['index']].get('motiv'),
                  'planned_scene': plan[x['index']].get('szene'),
                  'planned_details': plan[x['index']].get('details', ''),
                  'motif_not_in_spoken_words': not woertlich(plan[x['index']].get('motiv'), x['text'],
                                                             x.get('phase_text', ''), namen),
                  'stand_ins': stellvertreter(f"{x['text']} {x.get('phase_text', '')}")}
                 for x in teil if plan.get(x['index'], {}).get('bildmodus') in ('illustration', 'stock', 'foto')]
    gesagt = {x['index']: x['text'] for x in teil}
    phase = {x['index']: x.get('phase_text', '') for x in teil}
    if not eintraege:
        return daten, 0
    try:
        d, _ = gemini(prompts.DATEN + prompts.SZENEN + BILDREGIE
                      + '\nTASK: For each slot, rate 1-10 how directly the planned image shows what its spoken words '
                        'say: the named subject, action, place or consequence a viewer hears at that moment. A loosely '
                        'related or opposite image (e.g. opening a DVD envelope while hearing that streaming overtook '
                        'DVDs) scores low. For every score below ' + str(BEZUG_MIN) + ', give a better motif (2-5 words quoted verbatim from the spoken words), '
                        'a 20-45 word painted scene that literally shows the spoken words, aktion (3-8 words: what that '
                        'motif visibly does) and 2-4 search words. For a '
                        'number, price or statistic, show the people or place it affects doing the concrete action. '
                        'When the spoken words name only an amount, date, company, person or abstract business step '
                        '(raised money, became CEO, partners, shares), nothing literal can be painted: use one of the '
                        "slot's stand_ins exactly as motif instead, shown in the story period and place; each stand-in at most "
                        'once, and paintable spoken subjects (founders, a lab, a product) beat any stand-in. '
                        'motif_not_in_spoken_words=true means the planned motif is not quoted from the spoken '
                        'words: always replace it, scoring at most ' + str(BEZUG_MIN - 1) + '. '
                        'Keep good slots unchanged (repeat their motif/scene). Return every slot.\n'
                      + json.dumps(eintraege, ensure_ascii=False), BEZUG_SCHEMA, modelle=PLANEN)
    except Exception as e:  # Pruefung ist Verbesserung, kein Pflichtschritt
        print('Bezugspruefung nicht verfuegbar:', str(e)[:100])
        return daten, 0
    ersetzt = 0
    for p_ in d.get('pruefung', []):
        alt = plan.get(p_.get('index'))
        # Ein nicht woertliches Motiv wird ersetzt, auch wenn die KI es gut benotet - aber nur durch
        # ein woertliches (sonst bliebe ein ebenso freies Motiv, nur anders formuliert).
        frei = alt and not woertlich(alt.get('motiv'), gesagt.get(p_.get('index')), phase.get(p_.get('index'), ''),
                                     namen)
        if alt and alt.get('bildmodus') in ('illustration', 'stock', 'foto') \
                and (p_.get('note', 10) < BEZUG_MIN
                     or (frei and woertlich(p_.get('motiv'), gesagt.get(p_.get('index')),
                                            phase.get(p_.get('index'), ''), namen))) \
                and p_.get('szene') and p_.get('motiv'):
            alt.update(motiv=p_['motiv'][:80], szene=p_['szene'][:400], suche=p_.get('suche') or alt.get('suche'),
                       bildmodus='illustration')
            # Neues Motiv mit alter Handlung waere widerspruechlich: ohne neue aktion die freie Szene nehmen.
            if p_.get('aktion'):
                alt['aktion'] = p_['aktion'][:80]
            else:
                alt.pop('aktion', None)
            alt.pop('details', None)
            if isinstance(p_.get('details'), str) and p_['details'].strip():
                alt['details'] = p_['details']
            ersetzt += 1
    print(f'Bezugspruefung: {ersetzt} von {len(eintraege)} Motiven woertlicher gemacht')
    return daten, ersetzt


def _planen(gemini, modelle, auftrag, indizes, fallback_prompt=None):
    """Ein Bildplan-Auftrag; bei Ueberlast oder unvollstaendiger Antwort genau ein neuer Versuch."""
    import time
    from skript import AnbieterNichtVerfuegbar
    teile = {}
    for runde in range(2):
        try:
            d, modell = gemini(auftrag, SCHEMA, modelle=modelle,
                              **({'fallback_prompt': fallback_prompt} if fallback_prompt is not None else {}))
        except AnbieterNichtVerfuegbar as e:
            # GEMESSEN 22.10.2026 (Lauf 39747394681): Gemini 503 + Zeitlimit (Sperren 5 bzw. 1 Min.), Groq lieferte
            # ungueltiges JSON -> Bau nach 58 s weg. Das ist keine Kontingentsperre: einmal warten, bis die kurze
            # Gemini-Sperre ablaeuft, dann neu. Echte Kontingentsperren brechen weiter sofort ab.
            if runde or re.search(r'429|kontingent|gesperrt|keine reserve|frist', str(e), re.I) \
                    or float(os.environ.get('CF_SCHRITT_ENDE', 'inf')) - time.monotonic() < 240:
                raise
            print('Bildplan: Anbieter kurz gestoert, neuer Versuch in 75 s -', str(e)[:120], flush=True)
            time.sleep(75)
            continue
        except RuntimeError as e:
            # GEMESSEN 08.10.2026 (Lauf 37784030675): Gemini kurz ueberlastet, der Groq-Ausweg
            # war fuer den Bildplan zu gross -> Bau weg. Nach kurzer Pause Gemini erneut.
            if runde:
                raise
            print('Bildplan: Gemini nicht erreichbar, neuer Versuch in 20 s -', str(e)[:120])
            time.sleep(20)
            continue
        daten = d['einstellungen']
        print('Gemini-Bildplan:', modell, '| Einstellungen:', len(daten), f'(erwartet {len(indizes)})')
        if [x.get('index') for x in daten] == indizes:
            return daten
        # GEMESSEN 22.10.2026 (Business Walmart): Groq lieferte 9 und dann 4 von 12 Einstellungen, der Bau brach ab.
        # Teilplaene beider Versuche zusammenlegen (je Index der erste Vorschlag); ergibt das alle, weiter.
        for x in daten:
            if x.get('index') in indizes and x.get('index') not in teile:
                teile[x['index']] = x
        if set(teile) == set(indizes):
            print('Bildplan aus Teilplaenen vollstaendig zusammengesetzt')
            return [teile[i] for i in indizes]
        print('Bildplan unvollstaendig - neuer Versuch')
    return daten  # die Pruefung unten meldet die Luecke


def teil_planen(gemini, auftrag, kontext, kompakt, teil, fallback):
    """Eine Etappe planen; bleibt sie nach zwei Versuchen lueckenhaft, die fehlenden Slots halbiert neu planen.
    GEMESSEN 25.10.2026 (Tesla-Korrektur 40181407459): Groq 0, Gemini 1 von 7 Einstellungen -> ValueError
    "nicht lueckenlos", die ganze Korrektur weg, obwohl die anderen 76 Einstellungen geplant waren."""
    indizes = [x['index'] for x in teil]
    neu = _planen(gemini, PLANEN, auftrag + json.dumps(dict(kontext, slots=teil), ensure_ascii=False),
                  indizes, fallback_prompt=fallback)
    da = {x.get('index'): x for x in neu if x.get('index') in indizes}
    fehlen = [x for x in teil if x['index'] not in da]
    if not fehlen or len(teil) <= 1:
        return [da[i] for i in indizes] if not fehlen else neu
    print(f'Bildplan: {len(fehlen)} fehlende Einstellungen in kleineren Teilen neu')
    mitte = max(1, len(fehlen) // 2)
    for haelfte in (fehlen[:mitte], fehlen[mitte:]):
        for stueck, ausweich in (groq_teile(auftrag, kompakt, haelfte) if haelfte else []):
            for x in teil_planen(gemini, auftrag, kontext, kompakt, stueck, ausweich):
                if x.get('index') in indizes:
                    da.setdefault(x['index'], x)
    return [da[i] for i in indizes] if set(da) == set(indizes) else list(da.values())


def demo_material(s):
    """Echte README-Bilder je Quellseite fuer den Bildplaner (nur Werkzeug-Seiten auf GitHub/HF)."""
    urls = []
    for t in s['teile']:
        u = t.get('quelle_url')
        if u and u not in urls and ('github.com/' in u or 'huggingface.co/' in u):
            urls.append(u)
    aus = []
    try:
        import bauen
        for u in urls[:3]:
            medien = bauen.readme_medien(u) or []
            if medien:
                # 15.10.2026: breite Screenshots liefern im Bau drei getrennte Bereiche (bauen.bildteile).
                aus.append({'source_url': u, 'media': [{'file': l.rsplit('/', 1)[-1], 'alt': a,
                                                        'animated': l.lower().endswith('.gif'),
                                                        'region_crops_if_wide': 0 if l.lower().endswith('.gif') else 3}
                                                       for l, a in medien[:8]]})
    except Exception as e:  # Netz weg: Plan ohne Liste wie bisher
        print('README-Bilder nicht abrufbar:', str(e)[:100])
    return aus


def groq_reserve(prompt):
    """Dieselbe konservative Schaetzung wie autorenvergleich.groq fuer den Bildplan."""
    import autorenvergleich as av
    fmt = {'type': 'json_schema', 'json_schema': {'name': 'contentfabrik_antwort', 'strict': True,
                                                   'schema': av.groq_schema(SCHEMA)}}
    return math.ceil((len(prompt) + len(json.dumps(fmt))) / 3) + 3072


def groq_ausweich(auftrag, kompakt, slots, grenze=7900):
    """Groq-Ausweichauftrag: optionale Teile kuerzen, bis er in die Reserve passt.

    GEMESSEN 15.10.2026 (Lauf 38708651708): Gemini ueberlastet, Groq-Bildplan 8009 > 7900 Tokens
    -> Bauabbruch. Regie, Sprechtexte, Slots und Pflichtregeln bleiben vollstaendig; gekuerzt
    werden README-Details (nur Dateinamen), aeltere Redaktionshinweise und die Bildbibliothek.
    """
    k = dict(kompakt)
    def bauen():
        return auftrag + json.dumps(dict(k, slots=slots), ensure_ascii=False, separators=(',', ':'))
    if groq_reserve(bauen()) > grenze and k.get('tool_demo_material'):
        k['tool_demo_material'] = [{'source_url': q.get('source_url'),
                                    'files': [m.get('file') for m in q.get('media', [])]}
                                   for q in k['tool_demo_material']]
    while groq_reserve(bauen()) > grenze and k.get('editorial_feedback'):
        k['editorial_feedback'] = list(k['editorial_feedback'])[:-1]
    if groq_reserve(bauen()) > grenze and k.get('illustration_library'):
        k['illustration_library'] = []
    # GEMESSEN 24.10.2026 (Langvideos Tesla 40098336155 / openshell 40098338519): Gemini-Zeitlimit, der Groq-Auftrag
    # trug alle 50 Phasen des Langvideos in jede 30er-Etappe (13.505 bzw. 15.787 > 7.900) -> beide Bauten weg.
    # Die Etappe braucht nur ihre eigenen Phasen; die Positionen bleiben, damit slot.phase weiter passt.
    if groq_reserve(bauen()) > grenze and k.get('phases'):
        eigene = {x.get('phase') for x in slots}
        k['phases'] = [p if i in eigene else {} for i, p in enumerate(k['phases'])]
    return bauen()


def groq_teile(auftrag, kompakt, teil, grenze=7900):
    """[(slots, groq_auftrag)]: die Etappe halbieren, bis jeder Groq-Ausweichauftrag in die Reserve passt.
    GEMESSEN 24.10.2026: allein die Regeln sind ~7.500 Zeichen; 30 Langvideo-Slots samt Phasen ergaben
    ~10.500 Tokens auch ohne fremde Phasen. Ein Short (eine Etappe, passt) bleibt EIN Auftrag."""
    def knapp(xs):
        return [{k: x[k] for k in ('index', 'phase', 'text', 'dauer_s', 'stand_ins') if k in x} for x in xs]
    prompt = groq_ausweich(auftrag, kompakt, knapp(teil), grenze)
    if len(teil) <= 1 or groq_reserve(prompt) <= grenze:
        return [(teil, prompt)]
    mitte = len(teil) // 2
    return groq_teile(auftrag, kompakt, teil[:mitte], grenze) + groq_teile(auftrag, kompakt, teil[mitte:], grenze)


# Verbesserungsplan 18.10.2026 Punkt 3 (Nutzer: „Ja"): roter Faden im Bild. Codex-Videos mit hoher Bindung zeigten
# einen wiederkehrenden Gegenstand; unsere Geschichten waren Bildfolgen ohne Verbindung. Nur fuer Geschichten
# (Business) - der KI-Kanal bekommt am 22.10. schon die Screenshot-Aenderung (eine Bildaenderung je Lauf).
LEITGEGENSTAND = ('Pick ONE signature object named or clearly implied in the spoken story (e.g. the first store '
                  'sign, a pocket watch, the first product) and show that same object, with the same look, in the '
                  'opening slot, at the turning point and in the resolution - each time in a new situation that '
                  'illustrates the words of that slot. Name it the same way in motiv each time. ')


# Bildregie nach den gesichteten ersten Codex-Motiven (Karten-Handwerk, transparente Kreativschichten).
# Nur Bildplanung: Skriptprofil, gepruefte Stimme und Rendercode bleiben davon unabhaengig.
BILDREGIE = (
    '\nVISUAL DIRECTION: Each shot must communicate one story beat at phone size before captions. '
    'Build it around the spoken subject performing one visible action, or a visible state/consequence. '
    'Make the exact product or process dominate; choose a close object detail, useful human interaction '
    'or location reveal according to what this sentence says. A room is context, not the whole story. '
    'For generated physical products explicitly named in narration, show the product itself with plain '
    'unlettered surfaces; this overrides the generic advice to hide writing-bearing objects, but never '
    'permits invented interfaces, writing, brand packaging or tool outputs. '
    'Fill details with 12-24 English words: the distinguishing material, shape, scale or visible state '
    'of the focal subject, then a lighting/depth cue. Describe the properties that make THIS object '
    'recognizable at its real scale: surface texture, distinct edges, layer separation or material '
    'transparency where relevant. Include only properties appropriate to the spoken subject. '
    'Describe visual texture rather than adding new historical facts, quantities, people or events. '
    'Use warm directional window or practical light, readable cool shadows and soft background depth '
    'appropriate to the setting; keep the focal subject sharp. Use one restrained color accent on it. '
    'When people are needed, prefer one active person with separated relaxed hands; add others only '
    'when the spoken action requires them. Preserve any explicitly spoken count. Let gaze and posture '
    'convey attention or effort without inventing historical emotions or drama. '
    'Vary neighbouring shots by their actual subject, process stage or visible consequence, not just '
    'camera angle. Show wear, thickness, transparency or before/after state only when supported; '
    'no split panels. For an abstract amount or date use an allowed stand-in only as a last resort, '
    'keeping the story setting and linking its details to a concrete subject in the phase. Never '
    'invent a factory, product or transaction to explain an abstract number. Exact amounts and dates '
    'are added by the video code, never painted. Keep the composition simple and the environment '
    'lived-in through a few relevant details, with calm caption areas.\n')


def vorbereiten(s, laengen, woerter, cache=None, fortschritt=None):
    """fortschritt(teilplan): sichert jede fertig geplante Etappe sofort (bauzustand.json)."""
    from skript import gemini, SEHEN
    import lernen
    import bibliothek
    from rendercache import signatur
    zeitplan = slots(s, laengen, woerter)
    key = signatur([s['teile'], laengen, s.get('bilder', []), prompts.VERSION, motivziel(s),
                    lernen.redaktionsregeln(), bibliothek.signatur().decode('utf-8'), Path(__file__).read_text(encoding='utf-8')])
    alt = (cache or {}).get('bildplan') or {}
    daten = alt.get('einstellungen') if alt.get('key') == key else None
    # Nutzer 24.10.2026: "genau da weitermachen, wo es durchgefallen ist". GEMESSEN Tesla-Langvideo 40104697671:
    # nach einem spaeteren Fehler plante Versuch 2 alle 11 Etappen neu (~20 KI-Anfragen, 15 Min. Groq-Wartezeit).
    fertig = dict(alt.get('teile') or {}) if alt.get('key') == key else {}
    # Die menschlich kontrollierte Regie ist verbindlich und braucht keinen
    # zweiten KI-Auftrag, der dieselbe Bildfolge lediglich wieder ueberschreibt.
    if daten is None and feste_regie(s):
        daten, zaehler = [], {}
        for slot in zeitplan:
            phase = slot['phase']
            j = zaehler.get(phase, 0)
            zaehler[phase] = j + 1
            vorgaben = s['teile'][phase]['bildfolge']
            if j >= len(vorgaben):
                raise ValueError(f'Phase {phase}: redaktionelle Bildfolge zu kurz fuer die gemessene Stimme')
            daten.append(dict(vorgaben[j], index=slot['index']))
        print('Redaktioneller Bildplan | Einstellungen:', len(daten))
    if daten is None:
        auftrag = (prompts.DATEN + prompts.SZENEN + BILDREGIE + '\nTASK: Plan the actual visual edit, NOT new narration. '
            'Each timed slot below needs a distinct relevant shot, within its original spoken phase. '
            f'This video requires at least {motivziel(s)} genuinely distinct visible motifs. '
            'Use each library asset and each source image at most once. Do not repeat the same '
            'office or presenter pose with only a different label, crop or zoom. '
            'Keep each szene to 20-22 English words, motiv to 2-5 words. '
            'Prefer asset for a genuinely relevant approved library illustration. Set asset to its '
            'exact id from illustration_library; use only this channel. Do not use a library image '
            'just to fill time when its subject does not match. Illustrative scenes are the visual '
            'default requested by the user; genuine demos are brief evidence of actual tool functions. '
            'Introduce the original channel presenter in the opening and bring the same identity '
            'back during the story in useful actions, not only the closing CTA. Prefer presenter '
            'library assets; for a new illustration involving our presenter set figur=true so the '
            'reference image is actually used. Our presenter: ' + FIGUR.get(s.get('kanal'), 'the channel presenter')
            + '. Never use the presenter as a named real historical founder. '
            'Use overview, object detail, visible process, comparison or outcome when supported. '
            'A zoom, different crop or title change is NOT a new motif. Never use unrelated candles, '
            'abstract loops or background-only frames to fill missing imagery. Every shot must '
            'illustrate the words spoken in that slot. For historical facts use genuine matching '
            'photos or clearly illustrative original scenes, never pretend a fictional presenter '
            'is a real founder. Illustrations: original painted urban open-world-game poster look, '
            'strong contours and cinematic light; no copied game characters, logos or scenes. '
            # 16.10.2026: themenbezogene Sonderregeln (Nintendo-Karten, Qwen-Image) entfernt - jede half
            # einem Video und verwirrte den Planer bei allen anderen; die Kanalvorlage traegt jetzt die Praezision.
            + (LEITGEGENSTAND if s.get('format') == 'geschichte' else '') +
            'Keep generated props unlettered. Prefer clear object compositions; avoid crowded hands and small shelf '
            'packaging. Vary gaze and pose naturally when a fictional presenter is useful. '
            'Use the fictional presenter only when the slot actually benefits from a presenter. '
            'For AI tools use karte only for brief identification, then demo for genuine screenshots '
            'or example outputs from that exact source URL. Do not invent a tool result using stock '
            'or illustration. Benchmark overviews and generated scientific-chart art are NOT useful demos. '
            'Do not plan the same demo example twice. '
            'When explaining abstract capabilities, illustration may show the HUMAN problem or '
            'workflow (a pile of mail, a creator arranging photographs, original presenter explaining), '
            'never a fabricated tool screen or claimed output; the description discloses AI '
            'illustrations. Do not demand demo for a repository with only benchmarks '
            'or code; its documentation is not a live demonstration. Avoid repeated cards or identical '
            'demo imagery. Every available photograph may be used only ONCE; after an archival '
            'photo use an illustrative object/action detail, not another nonexistent photograph '
            'of that same event. Do not plan foto unless the supplied metadata actually supports '
            'the spoken subject and era. foto refers to the '
            'available indexed photo metadata; illustration is useful when no genuine photo fits. '
            # Nutzerentscheidung 15.10.2026 (wortgenau): Airbnb-Satz "They put an air mattress in their living
            # room" bekam das Motiv "living room breakfast". Das Motiv kommt jetzt woertlich aus dem Satz.
            'motiv MUST quote the most concrete visible thing from the own spoken words of the slot, '
            'verbatim (e.g. words "They put an air mattress in their living room" -> motiv "air mattress"), '
            'and szene must show exactly that as the focal subject. Never a named real person or brand: '
            'use their spoken role or object instead (e.g. "roommates", "rent", "air mattress"). '
            # Modellvergleich 15.10.2026: "air mattress" wurde als normale Matratze gemalt.
            'For an object that is easily confused, describe its distinguishing look in szene (material, '
            'shape, state), e.g. "an inflated vinyl air mattress", not just "a mattress". '
            # 23.10.2026 (Moderna): "million in 2018" als Motiv ergab Bueroszenen, Pruefer 2/10.
            'When the slot words name only an amount, date, company, person or abstract business step, there is '
            "nothing literal to paint: set motiv to one of that slot's stand_ins exactly (e.g. \"it raised $2 "
            'billion" -> "bank vault door swinging open", "Partners followed" -> "two executives shaking hands across '
            'a table", "sold 27 '
            'million shares" -> "stock exchange trading bell") and show it in the story period and place. '
            'Never use an amount, year or name as motiv. Use each stand-in at most once per video, and prefer '
            'something the words themselves name and can be painted (e.g. "Five founders" -> five founders at a lab '
            'bench) over any stand-in. '
            'For illustration, foto and stock slots also fill the short fields the video code assembles '
            'into the image prompt: aktion = what the focal subject visibly does, 3-8 words from the '
            'spoken words; ort = the concrete place, 2-6 words; epoche = the period of the story '
            'moment as words (e.g. "late 2000s", "1950s post-war Japan"); einstellung = one of '
            + json.dumps(EINSTELLUNGEN) + ', varied between neighbouring slots. '
            'Return EXACTLY one entry per slot, same integer index. motiv states the distinct visible '
            'subject/action. No extra words or factual assertions in the narration.\n'
            # GEMELDET 09.10.2026 (Aurelio-Short, Nutzernote 6/10): „Fotos, die nicht mit dem Text
            # zusammenhaengen" - 21 Symbolbilder (Sparschwein, Muenzen, Schluessel), obwohl die README
            # ein demo.gif mit genau den genannten Funktionen hatte.
            'TOOL DEMO MATERIAL lists real README images/animations of the tool. When it is not empty, '
            'every slot whose narration names a concrete feature, screen, output or result of the tool '
            'MUST use demo (aim for at least half of all slots); an animated demo yields several '
            'different stills and every wide static screenshot yields three different region crops '
            '(left, centre, right part of the real interface), each usable once. A generic person at a '
            'laptop never explains a software feature. Never show symbolic props (piggy banks, coins, keys, stamps, generic '
            'paperwork) for a concrete tool feature. Use illustration for the human problem, the hook, '
            'the presenter and the call to action.\n')
        kontext = {
                'tool_demo_material': demo_material(s),
                'phases': s['teile'], 'photos': s.get('bilder', []),
                # Bibliotheksbilder sind Hochformat - im Langvideo (16:9) waeren sie beschnitten.
                'illustration_library': bibliothek.auswahl(s.get('kanal'),' '.join(t['text'] for t in s['teile']))
                                        if dramaturgie.videoformat(s) == 'short' else [],
                # Regel vom 05.10. beschreibt beide Figuren - der Auftrag nennt die eigene schon.
                'editorial_feedback': [r for r in lernen.redaktionsregeln() if not fremde_figur(r, s.get('kanal'))]}
        # Groq braucht die Bildregie, nicht lokale Dateipfade, Hashes/Sichtkontrollnotizen
        # oder mehrfach wiederholte Phasentexte in jedem Slot. Regeln/Fakten erhalten.
        kompakt = dict(kontext,
            phases=[{k: t[k] for k in ('text', 'szene', 'werkzeug', 'quelle_url', 'demo_url', 'bildmodus', 'figur')
                     if k in t} for t in s['teile']],
            illustration_library=[{k: b[k] for k in ('id', 'motiv') if k in b}
                                  for b in kontext['illustration_library']],
            editorial_feedback=aktuelles_feedback(kontext['editorial_feedback']))
        daten = []
        for etappe in etappen(zeitplan):
            # Stellvertreter je Slot (23.10.2026) - ohne sie bleibt dem Planer nur "million in 2018" als Motiv.
            etappe = [dict(x, stand_ins=stellvertreter(f"{x['text']} {x.get('phase_text', '')}")) for x in etappe]
            for teil, fallback in groq_teile(auftrag, kompakt, etappe):
                if all(str(x['index']) in fertig for x in teil):
                    print(f"Bildplan: Einstellungen {teil[0]['index']}-{teil[-1]['index']} aus vorherigem Versuch")
                    daten += [fertig[str(x['index'])] for x in teil]
                    continue
                neu = teil_planen(gemini, auftrag, kontext, kompakt, teil, fallback)
                neu, _ = bezug_pruefen(gemini, teil, neu, eigennamen(s))
                daten += neu
                if fortschritt and [d.get('index') for d in neu] == [x['index'] for x in teil]:
                    fertig.update({str(d['index']): d for d in neu})
                    fortschritt({'key': key, 'teile': fertig})
        for i, d in behaltene_einstellungen(s, alt, zeitplan).items():
            if i < len(daten):
                daten[i] = d
    if len(daten) != len(zeitplan) or [d.get('index') for d in daten] != list(range(len(zeitplan))):
        raise ValueError('Bildplan deckt nicht alle Sprechphasen lueckenlos ab')
    if not feste_regie(s):
        n = malbar_machen(daten, zeitplan, eigennamen(s))
        if n:
            print(f'Bildplan: {n} unmalbare/doppelte Motive durch Stellvertreter ersetzt')
    aus = []
    pro_phase = {}
    import kanalstandard
    vorlage = (kanalstandard.nach_name(s.get('kanal')) or {}).get('bildvorlage')
    for slot, d in zip(zeitplan, daten):
        if d.get('bildmodus') not in ('foto', 'stock', 'illustration', 'karte', 'demo', 'figur', 'grafik', 'asset') or not d.get('szene') or not d.get('motiv'):
            raise ValueError('Bildplan enthaelt eine leere oder ungueltige Einstellung')
        t = copy.deepcopy(s['teile'][slot['phase']])
        j = pro_phase.get(slot['phase'], 0)
        pro_phase[slot['phase']] = j + 1
        vorgaben = t.get('bildfolge', [])
        if j < len(vorgaben):
            d = dict(d, **vorgaben[j])
            if d.get('demo_url'):
                t['demo_url'] = d['demo_url']
            if 'grafik_variante' in d:
                t['grafik_variante'] = d['grafik_variante']
            if 'grafik_typ' in d:
                t['grafik_typ'] = d['grafik_typ']
        if d.get('bildmodus') == 'asset':
            try:
                if d.get('asset') not in {b['id'] for b in bibliothek.auswahl(
                        s.get('kanal'),' '.join(t['text'] for t in s['teile']))}:
                    raise ValueError('Bibliotheksmotiv passt nicht zum gesprochenen Thema')
                bibliothek.bild(d.get('asset'), s.get('kanal'))
                t['asset'] = d['asset']
            except ValueError:
                # GEMESSEN 08.10.2026 (Lauf 37753715598): ein fuer den Kanal nicht freigegebenes
                # Bibliotheksbild liess den ganzen Bau abbrechen. Szene stattdessen neu malen.
                d = dict(d, bildmodus='illustration')
        if 'figur' in d:
            t['figur'] = d['figur']
        t.update({k: d[k] for k in ('bildmodus', 'suche', 'szene', 'motiv')})
        szene = szene_aus_vorlage(d, vorlage, slot['text'], slot.get('phase_text', ''), eigennamen(s))
        if szene != d['szene']:
            t['szene'], t['vorlage'] = szene, True
        if fremde_figur(t['szene'], s.get('kanal')):
            print(f"Einstellung {slot['index']}: Szene beschrieb die Figur des anderen Kanals - Motivszene ohne Figur")
            t['szene'] = prompts.rueckfall_motiv(d['motiv'], d.get('suche', '')) or d['motiv']
            t['figur'] = False
        t['text'] = slot['text']
        t['_phase'] = slot['phase']
        aus.append(dict(slot, teil=t))
    return demo_vorrang(aus, demo_material(s)), {'key': key, 'einstellungen': daten,
                                                 'texte': [x['text'] for x in zeitplan]}


def behaltene_einstellungen(s, alt, zeitplan):
    """Bestandene Einstellungen einer Korrekturrunde unveraendert aus dem alten Bildplan uebernehmen.

    GEMESSEN 18.10.2026 (Lauf 39111267908): Ford Runde 1 beanstandete 6 von 13 Einstellungen; der
    Neuplan ersetzte alle 13, Runde 2 hatte 10 beanstandete. Gleiche Planzeile -> gleicher Clip-Schluessel
    -> bauen.py nimmt den geprueften Clip aus dem Cache. Nur bei gleichem Satz je Einstellung (die
    Stimme kann sich bei einer Textkorrektur verschieben) und nur mit Fehlerliste von nachbessern.py.
    """
    neu = s.get('bild_neu_einstellungen')
    alte, texte = (alt or {}).get('einstellungen') or [], (alt or {}).get('texte') or []
    if not isinstance(neu, list) or len(alte) != len(zeitplan) or len(texte) != len(zeitplan):
        return {}
    behalten = {x['index']: dict(alte[x['index']]) for x in zeitplan
                if x['index'] not in neu and texte[x['index']] == x['text']
                and isinstance(alte[x['index']], dict) and alte[x['index']].get('index') == x['index']}
    if behalten:
        print(f'Bildplan: {len(behalten)} bestandene Einstellungen behalten, neu geplant: {sorted(neu)}')
    return behalten


def demo_vorrang(aus, material):
    """Gemalte Szenen durch echte README-Bereiche ersetzen, solange welche verfuegbar sind.

    GEMESSEN 15.10.2026: Lauf 38703468700 (FinceptTerminal) zeigte 11 gemalte Laptop-Szenen,
    Pruefer 2/10. Auch mit neuem Auftrag plante das Modell nur 4x demo bei 15 echten Bereichen.
    Feste Regel statt Modellgeschmack; die letzte Einstellung (Aufruf) bleibt frei, feste
    Grafiken/Assets/Karten bleiben unberuehrt; die erste Einstellung bleibt der Kanalfigur. Welcher Bereich passt, waehlt bauen.demo_fuer.
    """
    if not material:
        return aus
    for x in aus[1:-1]:
        # Seit 15.10.2026 auch ueber die Screenshot-Kapazitaet hinaus: bauen.py setzt dann eine
        # Erklaergrafik mit den gesprochenen Begriffen statt einer gemalten Szene ein.
        t = x['teil']
        # Kanalfigur am Anfang und wiederkehrend ist Nutzervorgabe (05.10.2026) - nie ersetzen.
        if t.get('bildmodus') in ('illustration', 'stock', 'foto') and not t.get('figur'):
            t['bildmodus'] = 'demo'
            t['quelle_url'] = t.get('quelle_url') or material[0]['source_url']
    return aus


def material_id(pfad):
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()


def pruefen(daten, dauer, art='short'):
    befunde = []
    shots = daten.get('einstellungen') or []
    if not shots:
        return {'befunde': ['Kein nachweisbarer Bildablauf vorhanden']}
    ende = 0.0
    letzter, haltezeit = None, 0.0
    material = set()
    for shot in shots:
        d = shot.get('dauer_s', 0)
        if not isinstance(d, (int, float)) or isinstance(d, bool) or not math.isfinite(d) or d <= 0:
            befunde.append('Ungueltige Bilddauer')
            continue
        if abs(shot.get('s', -1) - ende) > .1:
            befunde.append('Bildablauf hat Luecke oder Ueberlappung')
        if d > (10 if art == 'lang' else 6):
            befunde.append('Einstellung zu lang ohne neues Motiv')
        if not shot.get('material_id') or shot.get('material_art') == 'hintergrund':
            befunde.append('Sprechabschnitt ohne passendes Hauptbild')
        else:
            material.add(shot['material_id'])
            haltezeit = haltezeit + d if letzter == shot['material_id'] else d
            letzter = shot['material_id']
            if haltezeit > (10 if art == 'lang' else 6):
                befunde.append('Gleiches Motiv trotz mehrerer Einstellungen zu lange gehalten')
        ende = shot.get('s', ende) + d
    minimum = math.ceil(dauer / (16 if art == 'lang' else 7))
    if art == 'short' and dauer >= 30:
        ziel = daten.get('motive_min', 0)
        if type(ziel) is not int or not 0 <= ziel <= 40:
            befunde.append('Ungueltige Mindestzahl fuer Motive')
        else:
            # Nutzerentscheidung 14.10.2026 (Option B): hoechstens EINE dokumentierte Ausnahme,
            # wenn fuer genau eine Einstellung kein eigenes Bild bestand. Alles andere zaehlt als 0.
            toleranz = daten.get('motiv_toleranz', 0)
            toleranz = toleranz if type(toleranz) is int and toleranz in (0, 1) else 0
            minimum = max(minimum, ziel - toleranz)
    if len(material) < minimum:
        befunde.append(f'Zu wenig unterschiedliche Motive: {len(material)} statt mindestens {minimum}')
    if abs(ende - dauer) > .15:
        befunde.append('Bildablauf deckt nicht die ganze Videolaenge ab')
    return {'befunde': list(dict.fromkeys(befunde)), 'einstellungen': len(shots),
            'motive': len(material), 'motive_min': minimum}
