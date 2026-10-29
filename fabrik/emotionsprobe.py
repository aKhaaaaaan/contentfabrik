"""Hoerprobe: wie weit laesst sich die Stimme hochschrauben? (Nutzer 29.10.2026: "Wir brauchen noch mehr
Emotionen", "Noch mehr Uebertreibung, weiter hochschrauben".)

Je Kanal (eigene Stimme) dieselbe echte Passage in drei Stufen:
  1 = heute (Kanalstil, kurze Pause vor der Wendung)
  2 = Laute im Text (offizielle Gemini-TTS-Tags in spitzen Klammern: <gasp>, <whispers>, <long pause> ...)
  3 = Regie je Abschnitt (Hook, Spannung, Wendung, Aufloesung je eigener Stil) plus Laute
  4 = lustig hochgeschraubt (Nutzer: "Machen wir lustiger aber auch da hoch schrauben"): ironisch, Kichern
Nichts wird automatisch umgestellt; der Nutzer antwortet in Telegram.

Aufruf: python fabrik/emotionsprobe.py proben/
"""
import io
import json
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import stimme_gemini  # noqa: E402

# Echte gelieferte Skripte (Bristol Myers Squibb 28.10., Claude Code TV OS 26.10.) mit ihren Abschnitten.
PASSAGEN = {
    'business-origin-stories': [
        ('hook', 'One fire nearly ended Squibb, and failed. Its Brooklyn lab burned on Christmas Eve, 1858.'),
        ('beleg', 'Doctors and surgeons subscribed $2,100, so Squibb reopened in 1859 and flourished.'),
        ('wendung', 'Bristol-Myers made wartime penicillin, then faced Squibb in civilian antibiotics. Who won?'),
        ('aufloesung', "Neither. In 1989, the rivals merged, carrying Squibb's name into Bristol-Myers Squibb."),
        ('aufloesung', 'The fire failed. Be sure to like, share and save this video.')],
    'ai-tools-explained': [
        ('hook', 'Your smart TV feels stuck in the past. Could Claude Code write its replacement operating system?'),
        ('erklaerung', "Anthropic's docs call Claude Code an agentic coding environment. It reads your files, "
                       'runs commands and makes changes while you watch.'),
        ('wendung', 'What about cost? A third-party test found Claude Code sends roughly 33,000 tokens before your '
                    'prompt. OpenCode sent 7,000.'),
        ('aufloesung', 'Verdict: a Claude Code TV OS is unproven. Context fills fast.'),
        ('aufloesung', 'Be sure to like, share and save this video.')],
}
# Laute nur an festen Stellen: nie vor dem ersten Wort (Hook-Regel: Wirkung auf Wort 1).
LAUTE = {'wendung': '<long pause> <whispers> ', 'aufloesung': '<gasp> '}
REGIE = {
    'hook': 'shocked disbelief, urgent and loud, as if breaking huge news to a friend, hits every number hard',
    'beleg': 'fast, tense and conspiratorial, the pressure keeps rising',
    'erklaerung': 'fast, tense and conspiratorial, the pressure keeps rising',
    'frage': 'leaning in, hushed and secretive, dying to know the answer',
    'wendung': 'slow, hushed and ominous at first, then the question explodes with suspense',
    'aufloesung': 'huge release, triumphant and amazed, almost laughing with disbelief',
}
# Komik nur in der Stimme, nie im Text: Fakten bleiben woertlich.
LUSTIG = {
    'hook': 'comedic disbelief, like a stand-up comedian who cannot believe this really happened',
    'beleg': 'playful and sarcastic, mock-serious, enjoying how absurd it is',
    'erklaerung': 'playful and sarcastic, mock-serious, enjoying how absurd it is',
    'frage': 'teasing, cheeky, eyebrows raised',
    'wendung': 'dramatic fake suspense like a game-show host, then cheeky',
    'aufloesung': 'bursting out laughing at the irony, warm and delighted',
}
LAUTE_LUSTIG = {'beleg': '<chuckle> ', 'erklaerung': '<chuckle> ', 'wendung': '<long pause> ',
                'aufloesung': '<laugh> '}


def texte(teile, laute, tabelle=None):
    aus = []
    for i, (beat, satz) in enumerate(teile):
        vor = (tabelle or LAUTE).get(beat, '') if laute and i else ('<short pause> ' if i and beat == 'wendung' else '')
        if beat == 'aufloesung' and i and teile[i - 1][0] == 'aufloesung':
            vor = ''  # nur einmal staunen, der Like-Aufruf bleibt klar
        aus.append(vor + satz)
    return aus


def zusammen(wavs):
    stuecke, rate = [], None
    for wav in wavs:
        with wave.open(io.BytesIO(wav)) as w:
            rate = w.getframerate()
            stuecke.append(w.readframes(w.getnframes()))
    puffer = io.BytesIO()
    with wave.open(puffer, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b''.join(stuecke))
    return puffer.getvalue()


def main(aus):
    aus = Path(aus)
    aus.mkdir(parents=True, exist_ok=True)
    liste, nr = [], 0
    for kanal, teile in PASSAGEN.items():
        wahl = json.loads(Path(f'kanaele/{kanal}.json').read_text(encoding='utf-8'))['erzaehlstimme']
        stimme, stil = wahl['stimme'], wahl['stil']
        kurz = 'Business' if kanal.startswith('business') else 'KI'
        stufen = [('heute', lambda: stimme_gemini.sprechen(' '.join(texte(teile, False)), stimme, stil)[0]),
                  ('Laute im Text', lambda: stimme_gemini.sprechen(
                      ' '.join(texte(teile, True)), stimme, stil + ', even more exaggerated')[0]),
                  ('Regie je Abschnitt + Laute', lambda: zusammen(
                      [stimme_gemini.sprechen(t, stimme, f'{stil}; THIS PART: {REGIE.get(b, "")}')[0]
                       for (b, _), t in zip(teile, texte(teile, True))])),
                  ('lustig hochgeschraubt', lambda: zusammen(
                      [stimme_gemini.sprechen(t, stimme, f'{stil}; THIS PART: {LUSTIG.get(b, "")}')[0]
                       for (b, _), t in zip(teile, texte(teile, True, LAUTE_LUSTIG))]))]
        for name, machen in stufen:
            nr += 1
            try:
                wav = machen()
            except RuntimeError as e:
                print(f'Probe {nr} ({kurz} {name}) nicht erzeugt: {str(e)[:300]}')
                continue
            datei = f'{nr}_{kurz}_{name.split()[0].lower()}.wav'
            (aus / datei).write_bytes(wav)
            liste.append({'nr': nr, 'datei': datei, 'name': f'{kurz} {stimme}: {name}'})
            print(f'Probe {nr}: {kurz} {name}')
    hinweis = ('🎙️ Emotions-Probe: je Kanal dieselbe echte Passage in 4 Stufen. 1/5 = heute, 2/6 = mit Lauten '
               '(Staunen, Fluestern, Pause), 3/7 = jede Phase eigene Regie (Schock, Spannung, Fluestern, Triumph), '
               '4/8 = lustig hochgeschraubt (ironisch, Kichern, Lachen). '
               'Antworte hier z. B.: Stimme: 3 und 8 - dann baue ich das ein.')
    (aus / 'proben.json').write_text(json.dumps({'herkunft': 'Emotionsprobe', 'hinweis': hinweis, 'proben': liste},
                                                ensure_ascii=False, indent=1), encoding='utf-8')
    return 0 if liste else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
