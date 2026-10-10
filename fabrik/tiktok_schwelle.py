"""Erinnerung: ab ~8.000 TikTok-Followern auf eine zusaetzliche TikTok-Fassung > 60 s umstellen.

Nutzerentscheidung 10.10.2026: Shorts 35-45 s fuer YouTube UND TikTok (Wachstum zuerst). TikTok zahlt
im Creator Rewards Program erst ab 10.000 Followern, 100.000 Aufrufen/30 Tage und nur fuer Videos
> 1 Minute (Vergleichsseiten 2026, offizielle Seite ungeprueft). Damit die Umstellung nicht vergessen
wird, liest dieser Waechter einmal taeglich die oeffentliche Followerzahl je Kanal (Profilseite,
nur lesen), speichert den Verlauf in erfolg/tiktok.json und meldet das Erreichen der Schwelle EINMAL
per Telegram. Faellt der Abruf aus (z. B. TikTok blockt den Server), passiert nichts - die
Erinnerung steht zusaetzlich in UEBERGABE-CLAUDE.md und CLAUDE.md.
"""
import datetime
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

SCHWELLE = 8000
DATEI = Path('erfolg/tiktok.json')
KOPF = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/130 Safari/537.36', 'Accept-Language': 'de-DE,de;q=0.9'}


def follower(name):
    """Oeffentliche Followerzahl eines TikTok-Profils oder None."""
    try:
        roh = urllib.request.urlopen(urllib.request.Request(f'https://www.tiktok.com/@{name}', headers=KOPF),
                                     timeout=20).read().decode('utf-8', 'replace')
        m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', roh, re.S)
        info = json.loads(m.group(1))['__DEFAULT_SCOPE__']['webapp.user-detail']['userInfo']
        wert = info['stats']['followerCount']
        return wert if isinstance(wert, int) and wert >= 0 else None
    except Exception:
        return None


def pruefen(kanaele, jetzt=None, senden=None):
    """kanaele: {slug: tiktok_name}. Gibt die Liste der neu gemeldeten Kanaele zurueck."""
    jetzt = jetzt or datetime.datetime.now(datetime.timezone.utc)
    daten = json.loads(DATEI.read_text(encoding='utf-8')) if DATEI.exists() else {'verlauf': [], 'gemeldet': []}
    neu = []
    for slug, name in kanaele.items():
        zahl = follower(name)
        if zahl is None:
            print('TikTok-Follower nicht abrufbar:', name)
            continue
        daten['verlauf'].append({'datum': jetzt.date().isoformat(), 'kanal': slug, 'follower': zahl})
        print(f'TikTok {name}: {zahl} Follower')
        if zahl >= SCHWELLE and slug not in daten['gemeldet']:
            text = (f'📈 TikTok {name} hat {zahl:,} Follower (Schwelle {SCHWELLE:,}).\n'
                    'Erinnerung (Entscheidung 10.10.2026): jetzt zusaetzlich eine TikTok-Fassung ueber 1 Minute '
                    'bauen lassen, damit das Creator Rewards Program zahlt (ab 10.000 Followern und 100.000 '
                    'Aufrufen in 30 Tagen). Sag Claude Bescheid; YouTube-Shorts bleiben 35-45 s.').replace(',', '.')
            if (senden or _telegram)(text):
                daten['gemeldet'].append(slug)
                neu.append(slug)
    daten['verlauf'] = daten['verlauf'][-400:]
    DATEI.parent.mkdir(exist_ok=True)
    DATEI.write_text(json.dumps(daten, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    return neu


def _telegram(text):
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat:
        return False
    try:
        d = json.load(urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', timeout=20,
                                             data=urllib.parse.urlencode({'chat_id': chat, 'text': text}).encode()))
        return d.get('ok') is True
    except Exception:
        return False


def kanaele_aus_profilen():
    aus = {}
    for p in Path('kanaele').glob('*.json'):
        name = json.loads(p.read_text(encoding='utf-8')).get('tiktok_name')
        if name:
            aus[p.stem] = name
    return aus


if __name__ == '__main__':
    pruefen(kanaele_aus_profilen())
