"""Formatregeln und sprachgebundene Bildakzente, ohne weitere KI-Anfragen."""
import math
import re


def videoformat(daten):
    art = daten.get('videoformat', 'short')
    if art not in ('short', 'lang'):
        raise ValueError('videoformat muss short oder lang sein')
    return art


def laengen(daten):
    standard = [360, 600] if videoformat(daten) == 'lang' else [62, 90]
    werte = daten.get('laenge_s', standard)
    if not isinstance(werte, (list, tuple)) or len(werte) != 2 or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
            for x in werte) or not 0 < werte[0] <= werte[1]:
        raise ValueError('laenge_s braucht zwei positive, aufsteigende Sekundenwerte')
    if videoformat(daten) == 'short' and werte[1] > 180:
        raise ValueError('Mehr als 180 Sekunden brauchen videoformat lang')
    return werte


def interaktion(daten):
    gemeinsam = ('MANDATORY SPOKEN ENGAGEMENT REQUIREMENT: Every call to action explicitly asks viewers to LIKE, '
                 'SHARE and SAVE this video, all three actions. This is required in the actual '
                 'spoken narration, not only in captions, overlays or the description. Use a '
                 'direct reminder such as "Be sure to like, share and save this video." '
                 'Do not omit it or make the request conditional. Speak it as one concise, natural '
                 'English sentence, preferably at most 12 words, relevant to the story. '
                 'Count these words in the narration budget. A follow/subscribe request alone '
                 'does not satisfy this requirement. ')
    if videoformat(daten) == 'lang':
        return (gemeinsam + 'LONG FORM: Include exactly TWO calls to action: one near the beginning, '
                'after the initial hook and first useful context within the opening 20-30 seconds, '
                'and one at the end after the central answer. Each asks for all three actions. '
                'The opening sentence remains the story hook; do not open with engagement requests. '
                'Return to the story immediately after the early request; no mid-video repetitions. ')
    return (gemeinsam + 'SHORT FORM: Include exactly ONE call to action near the end, after the '
            'main payoff. It asks for all three actions. Keep the hook focused on the subject '
            'and the ending brief. ')


def auftrag(daten):
    gemeinsam = (
        'Build one clear central question and answer it honestly. Each beat must change what the '
        'viewer knows: a concrete example, evidence, consequence, useful comparison or resolution. '
        'Give small answers throughout; do not withhold all useful information until the ending. '
        'After a payoff, connect to the next unresolved question through a real consequence. '
        'No empty teasing, repeated promises, fabricated stakes or predictable list filler. '
        'Use visual contrast when the subject warrants it: object/detail, evidence/explanation, '
        'before/after with comparable sourced conditions. Let a key revelation breathe. '
        'Optional beat labels: hook, frage, beleg, erklaerung, wendung, aufloesung. '
        'Optional bildtext: an exact contiguous 2-5 word phrase copied from that part\'s narration, '
        'maximum 26 characters, identifying its crucial detail; at most one in every two parts. '
        'It appears ONLY when those words are spoken, so choose useful details, not generic hype. '
        'Optional geraeusch: 2-3 plain English words naming one literal, recognizable sound that '
        'would really be heard in that part\'s scene (e.g. cash register, crowd cheering, rain on '
        'window); at most 3 parts in a Short, never the first part; empty string when nothing fits. '
        + interaktion(daten))
    if videoformat(daten) == 'lang':
        return (gemeinsam + 'LONG FORM: Start with a specific outcome, surprising sourced detail or '
                'problem; demonstrate why it matters within the first 20-30 seconds. No logo intro '
                'or channel housekeeping. Organize 3-5 chapters, each with a local question, '
                'demonstration/evidence and mini-payoff, leading to the next chapter. Use 24-50 '
                'distinct visual beats scaled to length, not paragraphs repeated to fill time. '
                'Set name to a short useful chapter heading when a chapter begins. Move from '
                'orientation to complication, deeper understanding and the full central answer. '
                'Use occasional concise recaps only at transitions where they aid understanding. '
                'End after the delivered conclusion; no long outro. Do not apply relentless '
                'Shorts-style speed or cliffhangers to every sentence.')
    return (gemeinsam + 'SHORT FORM: The first frame must already show the subject or the problem. '
            'The first spoken sentence establishes a specific reason to watch. Keep essential '
            'context short, then progress through concrete discoveries. A short ranked entry '
            'must teach something distinct; give a practical example, not just a tool name. '
            'Pay off the opening before the ending; a natural callback is optional. '
            # GEMELDET 07.10.2026: „Wichtig ist, dass es die Leute fesselt, damit sie nicht
            # wegwischen." Rund 70 % entscheiden in den ersten 2 s (Shorts-Benchmarks 2026).
            # Der Videobau setzt an der 'wendung' Musikpause, Riser und Impact.
            'No greeting, channel name or "in this video" before the first fact. Label exactly '
            'one real turning point (the beat where the story changes) as beat wendung.')


def akzente(teile, woerter, abschnitte):
    """Nur wirklich gesprochene Phrasen im richtigen Abschnitt; keine geratenen Zeiten."""
    norm = lambda w: re.sub(r'[^\w]', '', w.casefold())
    aus, start, zuletzt = [], 0.0, -2
    for i, (teil, dauer) in enumerate(zip(teile, abschnitte)):
        ende = start + dauer
        phrase = teil.get('bildtext', '')
        tokens = phrase.split() if isinstance(phrase, str) else []
        if 2 <= len(tokens) <= 5 and len(phrase) <= 26 and i - zuletzt >= 2 \
                and not any(c in phrase for c in '\\{}\n\r'):
            gesucht = [norm(t) for t in tokens]
            gesprochen = [norm(t) for t in teil['text'].split()]
            belegt = any(gesprochen[j:j + len(tokens)] == gesucht
                         for j in range(len(gesprochen) - len(tokens) + 1))
            lokale = [w for w in woerter if start <= w['s'] < ende and w['e'] <= ende]
            if belegt:
                for j in range(len(lokale) - len(tokens) + 1):
                    treffer = lokale[j:j + len(tokens)]
                    if [norm(w['w']) for w in treffer] == gesucht \
                            and all(0 <= b['s'] - a['e'] < 0.7 for a, b in zip(treffer, treffer[1:])):
                        aus.append({'text': phrase, 's': treffer[0]['s'],
                                    'e': min(ende, max(treffer[-1]['e'] + .25, treffer[0]['s'] + 1.2)),
                                    'teil': i})
                        zuletzt = i
                        break
        start = ende
    return aus
