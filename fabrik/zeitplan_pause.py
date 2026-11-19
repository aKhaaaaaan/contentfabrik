"""Automatik-Pause und Claude-Limit fuer automatische Starts.

Nutzer 19.11.2026: "kann ich den Auto Start auch stoppen? Wenn zum Beispiel Claude Limit erreicht ist und mein PC
nicht an ist wegen Codex, dann laeuft ja nichts, dass es sinnlos startet." Zwei Regeln, nur fuer AUTOMATISCHE Starts
(GitHub-Zeitplan oder Cloudflare-Zeitplan) - "Start KI" / "Start Business" von Hand laufen immer:
1. Pause: Befehl "Pause" im Steuerungsbot (Worker-KV), hier ueber GET <worker>/pause gelesen.
2. Claude am Abo-Limit und kein fertiges Skript (eigenes Skript, Vorrat, geprueftes Teilbau) -> Kanal auslassen.
   GEMESSEN: waehrend Claudes Pausen schrieben Gemini/Groq fuer KI kein freigabefaehiges Skript (11.-14.10.),
   am 18.11. fiel der Business-Lauf bis 15 UTC aus demselben Grund.
"""
import json
import sys
import urllib.request

from themen import WORKER  # eine Adresse fuer alle (Audit 19.11.2026)


def pausiert(timeout=10):
    """'seit <ISO>' wenn die Automatik pausiert ist, sonst None. Worker nicht erreichbar -> None (Automatik laeuft
    weiter wie bisher; eine Stoerung des Workers soll keine Videos verhindern)."""
    try:
        req = urllib.request.Request(WORKER + '/pause', headers={'User-Agent': 'contentfabrik-zeitplan'})
        d = json.load(urllib.request.urlopen(req, timeout=timeout))
    except (OSError, ValueError) as e:
        print('Pause-Abfrage beim Worker nicht moeglich (Automatik laeuft weiter):', type(e).__name__)
        return None
    return f"seit {d.get('seit')}" if d.get('pausiert') is True else None


def ohne_autor(kanal, jetzt=None):
    """Grund, den automatischen Start dieses Kanals auszulassen, oder None."""
    import claude_ki
    grund = claude_ki.pause(jetzt)
    if not grund or not grund.startswith('Claude wegen'):
        return None  # Claude frei (oder Limitdatei kaputt -> lieber versuchen)
    import entwurf_cache
    import themen
    import vorrat
    pfad = f'kanaele/{kanal}.json'
    try:
        if themen.eigenes_skript(kanal) or vorrat.bereit(pfad) is not None:
            return None
        if entwurf_cache.laden(kanal, pfad, themen.nehmen(kanal)) is not None:
            return None
    except Exception as e:  # unklarer Zustand: lieber starten als einen Tag verlieren
        print('Fertiges Skript nicht pruefbar, Kanal startet:', type(e).__name__)
        return None
    return grund + ' - kein fertiges Skript; Gemini/Groq allein schreiben kaum freigabefaehige Skripte'


if __name__ == '__main__':
    # python fabrik/zeitplan_pause.py -> Exit 3 bei Pause (fuer Workflow-Schritte)
    p = pausiert()
    print('Automatik pausiert', p if p else '- nein')
    sys.exit(3 if p else 0)
