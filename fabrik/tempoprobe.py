"""Hoerprobe Tempo/Ausdruck KI-Kanal (Nutzer 06.11.2026: "die Stimme ... interessanter fuer Zuhoerer"; Hoerprobe
ausdruecklich freigegeben).

GEMESSEN 02.-06.11.2026 (verlauf/messungen): JEDES KI-Video wurde auf 45 s beschleunigt, Faktor 1.11-1.25, bei
130-135 Woertern - Pausen und Betonung der Regie werden dabei zusammengedrueckt. Dieselbe echte Passage
(KI-Short 06.11., Lauf 42187352585) in drei Fassungen:
  1 = wie heute: 130 Woerter, Regie je Abschnitt, auf 45 s beschleunigt
  2 = gekuerzt auf ~105 Woerter, natuerliches Tempo (nur beschleunigt, falls ueber 45 s)
  3 = wie 2, plus staerkere Kontraste (Schock -> Fluestern -> lange Pause -> Explosion)
Nichts wird automatisch umgestellt; der Nutzer antwortet in Telegram ("Stimme: N").
Aufruf: python fabrik/tempoprobe.py proben/
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import emotionsprobe  # noqa: E402
import stimme_gemini  # noqa: E402

ZIEL_S = 45.0
SCHLUSS = 'Which tool next? Comment, and follow for more.'
HEUTE = [
    ('hook', 'Midnight, and your inbox is winning. Three AI tools could help, but one bills you per token. Which one?'),
    ('frage', 'Gemini\'s card says "$0 / month with a Google Account." Beside it: "15 GB of cloud storage."'),
    ('beleg', 'Next tier says "2x higher usage access than Free." So more usage is the paid step.'),
    ('erklaerung', 'Claude\'s Free column says "Limited usage every 5 hours and every week." '
                   'Then: "Chat on web, desktop, and mobile."'),
    ('beleg', 'The twist: Free also lists "Search the web, create files, and run code." '
              'Paid Pro says "$20 if billed monthly."'),
    ('wendung', 'OpenAI\'s page flips it: "Prices per 1M tokens." gpt-6-luna: $0.10 input, $0.50 output. '
                'Metered, not a flat plan.'),
    ('aufloesung', 'Inbox rescued, price checked. Be sure to like, share and save this video. ' + SCHLUSS)]
# Dieselben Fakten, nur Fuellteile gestrichen (keine neue Aussage).
KURZ = [
    ('hook', 'Midnight, and your inbox is winning. Three AI tools could help, but one bills you per token.'),
    ('frage', 'Gemini\'s card says "$0 / month with a Google Account." Plus "15 GB of cloud storage."'),
    ('beleg', 'Want more? "2x higher usage" is the paid step.'),
    ('erklaerung', 'Claude Free: "Limited usage every 5 hours and every week."'),
    ('beleg', 'The twist: Free still lists "Search the web, create files, and run code." Pro? "$20 if billed monthly."'),
    ('wendung', 'And OpenAI? "Prices per 1M tokens." gpt-6-luna: ten cents input. Metered, not a flat plan.'),
    ('aufloesung', 'Inbox rescued, price checked. Be sure to like, share and save this video. ' + SCHLUSS)]
KONTRAST = {
    'hook': 'explosive comedic disbelief on the very first word, loud and fast, then a sharp stop',
    'frage': 'suddenly quiet and conspiratorial, leaning into the mic, slow and teasing',
    'beleg': 'quick, punchy, smug, hit the quoted numbers hard',
    'erklaerung': 'mock-serious newsreader, deadpan, every quote crisp',
    'wendung': 'whisper the first words, hold a long dramatic pause, then the last line explodes',
    'aufloesung': 'big triumphant grin you can hear, warm and energetic, clear call to action',
}


def dauer(wav):
    import io
    import wave
    with wave.open(io.BytesIO(wav)) as w:
        return w.getnframes() / w.getframerate()


def auf_ziel(wav, pfad):
    """Wie die Produktion: nur beschleunigen, wenn laenger als ZIEL_S (bauen.py, atempo)."""
    roh = pfad.with_suffix('.roh.wav')
    roh.write_bytes(wav)
    faktor = max(1.0, dauer(wav) / ZIEL_S)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(roh), '-filter:a', f'atempo={faktor:.3f}',
                    str(pfad)], check=True)
    roh.unlink()
    return faktor


def regie_teile(teile, stil, regie, laute):
    return emotionsprobe.zusammen([stimme_gemini.sprechen(t, 'Puck', f'{stil}; THIS PART: {regie.get(b, "")}')[0]
                                   for (b, _), t in zip(teile, emotionsprobe.texte(teile, laute))])


def main(aus):
    aus = Path(aus)
    aus.mkdir(parents=True, exist_ok=True)
    wahl = json.loads(Path('kanaele/ai-tools-explained.json').read_text(encoding='utf-8'))['erzaehlstimme']
    stil, regie = wahl['stil'], wahl.get('regie') or {}
    fassungen = [('wie heute (130 Woerter, beschleunigt)', lambda: regie_teile(HEUTE, stil, regie, True), HEUTE),
                 ('kuerzer, natuerliches Tempo', lambda: regie_teile(KURZ, stil, regie, True), KURZ),
                 ('kuerzer + starke Kontraste', lambda: regie_teile(KURZ, stil, KONTRAST, True), KURZ)]
    liste = []
    for nr, (name, machen, teile) in enumerate(fassungen, 1):
        try:
            wav = machen()
        except RuntimeError as e:
            print(f'Probe {nr} nicht erzeugt: {str(e)[:300]}')
            continue
        datei = f'{nr}_ki_tempo.wav'
        faktor = auf_ziel(wav, aus / datei)
        woerter = sum(len(t.split()) for _, t in teile)
        liste.append({'nr': nr, 'datei': datei,
                      'name': f'KI Puck: {name}, {woerter} Woerter, roh {dauer(wav):.0f} s, Tempo x{faktor:.2f}'})
        print(f'Probe {nr}: {liste[-1]["name"]}')
    hinweis = ('🎙️ Stimm-Probe KI (heutiges Video): 1 = wie heute, 130 Woerter auf 45 s beschleunigt. '
               '2 = Text etwas kuerzer, natuerliches Tempo mit echten Pausen. 3 = wie 2 mit starken Kontrasten '
               '(laut - fluestern - Pause - Explosion). Antworte hier z. B.: Stimme: 3')
    (aus / 'proben.json').write_text(json.dumps({'herkunft': 'Tempoprobe', 'hinweis': hinweis, 'proben': liste},
                                                ensure_ascii=False, indent=1), encoding='utf-8')
    return 0 if liste else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
