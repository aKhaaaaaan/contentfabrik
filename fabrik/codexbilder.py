"""Codex-Bilder auf Vorrat (Nutzer 12.11.2026: "Ja mach das" - Option 1, kostenlos).

Codex (image_gen ueber das ChatGPT-Abo des Nutzers) malt nur auf dessen PC. Der PC ist nicht immer an, deshalb
malt er IM VORAUS fuer die naechsten Themen (Warteschlange, Vorratsskript) und legt die Bilder als GitHub-Release
`codexbilder-<kanal>-<slug>` ab (nicht ins Repo - sonst ~1 GB/Jahr). Die Produktion holt hier vor dem Videobau
passende Bilder in die Bibliothek (assets/illustrationen/codex/, nicht committet). Der Bildplaner bietet sie wie
jedes Bibliotheksbild an ("Prefer asset for a genuinely relevant approved library illustration"), der Bildpruefer
prueft sie wie jedes Bild. Ohne Release / ohne Netz / vor dem Stichtag: nichts - der Bau laeuft wie bisher (FLUX).

Stichtag 26.11.: bis 25.11. laeuft der Kurztest (KI vs. Business) - eine neue Bildquelle wuerde ihn verfaelschen.
"""
import datetime
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

import bibliothek

# Nutzer 13.11.2026: "heute schon einbauen ... wegen GTA-Release am 19.11." (statt 26.11.). Beide Kanaele bekommen die
# Bilder gleichzeitig - der Kurztest-Vergleich KI/Business (Laenge) bleibt fair; bei der Auswertung 25.11. vermerken.
AB = datetime.date(2026, 11, 13)
PREFIX = 'codexbilder-'
ORDNER = bibliothek.ORDNER / 'codex'
QUELLE = 'Eigene KI-Illustration (Codex image_gen, vorab gemalt)'


def aktiv(heute=None):
    return (heute or datetime.date.today()) >= AB and os.environ.get('CF_CODEXBILDER', '1') != '0'


def slug(text):
    # GEMESSEN 19.11.2026: 3 fertig gemalte Pakete (Convai-NPCs, GTA Online, JPMorgan) scheiterten mit HTTP 422 "tag_name
    # is not well-formed" - nach dem Kuerzen auf 60 Zeichen endete der Tag auf "-". Erst kuerzen, dann trimmen.
    return re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')[:60].strip('-')


def _holen(url, roh=False):
    kopf = {'Accept': 'application/octet-stream' if roh else 'application/vnd.github+json',
            'User-Agent': 'contentfabrik', 'X-GitHub-Api-Version': '2022-11-28'}
    if os.environ.get('GITHUB_TOKEN'):
        kopf['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=kopf), timeout=60) as r:
        inhalt = r.read()
    return inhalt if roh else json.loads(inhalt)


def releases(repo):
    return _holen(f'https://api.github.com/repos/{repo}/releases?per_page=100')


def tag(kanal_slug, thema, videoformat='short'):
    """Release-Name. 15.11.2026 (Rockstar-Langvideo: 4 Codex-Bilder bereit, 0 genutzt): Langvideos sind 16:9, die
    Short-Bilder 9:16 - im Querformat waeren sie ein schmaler Streifen (486 von 1536 px). Langvideo-Bilder malt Codex
    deshalb eigens im Querformat, unter eigenem Namen (dasselbe Thema hat oft auch einen Short)."""
    return f"{PREFIX}{kanal_slug}-{'lang-' if videoformat == 'lang' else ''}{slug(thema)}"


def holen(kanal_slug, kanalname, thema, text, heute=None, repo=None, videoformat='short'):
    """Vorab gemalte Bilder genau dieses Themas in die Bibliothek legen; Liste der neuen IDs.
    Passend = Release-Tag codexbilder-<kanal>-<slug(thema)> ("Apple" steht in vielen Skripten - ein Wozniak-Video
    soll keine Apple-Bilder bekommen) UND ein Begriff des Releases steht im Sprechtext (bibliothek.passt_zum_text).
    Jede Datei wird gegen ihren SHA-256 aus bilder.json geprueft."""
    if not aktiv(heute):
        return []
    repo = repo or os.environ.get('GITHUB_REPOSITORY', 'aKhaaaaaan/contentfabrik')
    # 13.11. (KI 43401065863): der Autor formuliert das Thema um - deshalb zaehlt auch das Eingabethema (Liste).
    tags = {tag(kanal_slug, t, videoformat) for t in (thema if isinstance(thema, (list, tuple)) else [thema])
            if str(t or '').strip()}
    neu = []
    try:
        for rel in releases(repo):
            if rel.get('tag_name') not in tags:
                continue
            assets = {a['name']: a['url'] for a in rel.get('assets', [])}
            if 'bilder.json' not in assets:
                continue
            plan = json.loads(_holen(assets['bilder.json'], roh=True))
            begriffe = plan.get('begriffe') or []
            if not bibliothek.passt_zum_text({'nur_fuer_themen': begriffe}, text):
                continue
            for b in plan.get('bilder', []):
                name = Path(str(b.get('datei', ''))).name
                if name not in assets or not re.fullmatch(r'[a-z0-9-]+\.(?:jpg|png)', name):
                    continue
                daten = _holen(assets[name], roh=True)
                if hashlib.sha256(daten).hexdigest() != b.get('sha256'):
                    print(f'Codex-Bild {name}: Pruefsumme falsch - ausgelassen')
                    continue
                ORDNER.mkdir(parents=True, exist_ok=True)
                (ORDNER / name).write_bytes(daten)
                neu.append({'id': f'codex-{name.rsplit(".", 1)[0]}', 'datei': f'codex/{name}', 'kanal': kanalname,
                            'motiv': str(b.get('motiv', ''))[:200], 'sha256': b['sha256'],
                            'nur_fuer_themen': begriffe, 'quelle': QUELLE, 'format': videoformat,
                            # 16.11.2026: fester Platz anfang/mitte/ende (bildplan.codex_einsetzen); alte Pakete ohne
                            **({'platz': b['platz']} if b.get('platz') in ('anfang', 'mitte', 'ende') else
                               # alte 4er-Pakete: b1 war immer die Hook-Szene -> erstes Bild
                               {'platz': 'anfang'} if name.rsplit('.', 1)[0].endswith('-b1') else {}),
                            'sichtkontrolle': f"Codex {plan.get('datum', '')}; Bildpruefer im Lauf"})
    except Exception as e:  # Kuer - darf den Bau nie kippen
        print('Codex-Bilder nicht geholt:', type(e).__name__, str(e)[:120])
    if neu:
        katalog = ORDNER / 'katalog.json'
        try:
            alt = json.loads(katalog.read_text(encoding='utf-8'))['bilder']
        except (OSError, ValueError, KeyError):
            alt = []
        ids = {b['id'] for b in neu}
        katalog.write_text(json.dumps({'bilder': [b for b in alt if b['id'] not in ids] + neu}, ensure_ascii=False,
                                      indent=1), encoding='utf-8')
        print(f'Codex-Bilder (vorab gemalt): {len(neu)} fuer diesen Text in der Bibliothek')
    return [b['id'] for b in neu]
