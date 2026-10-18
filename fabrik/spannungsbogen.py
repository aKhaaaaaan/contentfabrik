"""Spannungsbogen eines Shorts pruefen: offene Frage in der Mitte und Rueckgriff auf den Einstieg.

GEMESSEN 18.10.2026 (TikTok-Profile, Codex-Vergleich): Nintendo (959 Aufrufe) - Widerspruch im ersten Satz,
"So what did Nintendo change?" in der Mitte, Schluss "Remember that lasting deck?"; Bigarrow (436) -
"Which button?" ... "The twist: ...". Louis Vuitton (260) und Fincept (182) zaehlten Fakten der Reihe nach
auf, ohne offene Frage und ohne Rueckgriff. Nutzer: "Ja mach das" (Spannungsbogen in jedes Skript).
Reine Textregeln ohne KI; skript.py bessert einmal nach und nimmt danach hin (kein Video faellt deshalb weg).
"""
import re

AUFRUF = re.compile(r'like,? share|share and save|subscribe|follow for', re.I)
# Bigarrow: "The twist: there's no AI inside" wirkt wie die Frage - eine angekuendigte Wendung.
WENDE = re.compile(r"(?:^|[^a-z])(?:the|here's the) (?:twist|catch|surprise)(?![a-z])", re.I)
FUELL = set('about after again also another because before being could didn every first from have into '
            'just like made make many more most much never only other over really same should since some '
            'still than that their them then there these they this those through very want were what when '
            'where which while will with would your years year'.split())


def saetze(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]


def _staemme(text, ausnahmen):
    return {w[:5] for w in re.findall(r"[a-z]+", text.lower())
            if len(w) >= 4 and w not in FUELL and w[:5] not in ausnahmen}


def luecken(teile, thema=''):
    """Fehlende Teile des Bogens: 'frage_mitte' und/oder 'rueckgriff'. Leere Liste = Bogen vorhanden."""
    alle = [s for t in teile for s in saetze(str(t.get('text', '')))]
    inhalt = [s for s in alle if not AUFRUF.search(s)]
    if len(inhalt) < 4:
        return []
    fehlt = []
    # Mitte = nach dem Einstieg (erste zwei Saetze), vor dem letzten Inhaltssatz (Bigarrow: Wendung vorletzter Satz).
    if not any(s.endswith('?') or WENDE.search(s) for s in inhalt[2:-1]):
        fehlt.append('frage_mitte')
    # Nur der Markenname zaehlt nicht (steht ohnehin ueberall); Themenwoerter wie "cards" schon.
    name = _staemme(str(thema).split(':')[0], set())
    einstieg = _staemme(inhalt[0], name)
    if not einstieg & _staemme(' '.join(inhalt[-2:]), name):
        fehlt.append('rueckgriff')
    return fehlt


def auftrag(fehlt, hook):
    teile = []
    if 'frage_mitte' in fehlt:
        teile.append('Around the middle, add one short open question that the next sentences answer '
                     '(e.g. "So what did they change?"), so the viewer waits for the answer.')
    if 'rueckgriff' in fehlt:
        teile.append(f'Just before the like/share/save request, refer back to the concrete thing in the '
                     f'opening sentence ("{hook}") and show it in a new light; resolve it, do not repeat it.')
    return ('\nYour previous draft lacks a tension arc. ' + ' '.join(teile)
            + ' Keep every sourced fact, the length, the title and the engagement request.')
