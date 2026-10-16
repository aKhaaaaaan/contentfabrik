"""Stoerungsmeldung aufs Handy: welcher Dienst gerade ausfaellt und was die Pipeline stattdessen tut.

Nutzerwunsch 16.10.2026: "Gemini ist gerade nicht erreichbar, versuch spaeter nochmal - oder andere
ausgefallene Systeme ... so eine Nachricht auf Telegram waere gut." Bis dahin sah er nur am Ende
"kein Video" - an diesem Tag fiel Gemini stundenlang aus (HTTP 503, danach 429).
Je Dienst hoechstens EINE Meldung pro Lauf (Merker im Arbeitsordner, gilt fuer alle Unterprozesse);
eine Stoerung der Meldung selbst darf nie den Lauf kippen.
"""
import datetime
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

MERKER = Path('ausgabe-lernen') / 'stoerungen'


def melden(dienst, was, folge):
    """dienst: kurzer Name (Merker-Schluessel); was: was ausgefallen ist; folge: was jetzt passiert."""
    schluessel = re.sub(r'[^a-z0-9]+', '-', dienst.lower()).strip('-') or 'dienst'
    merker = MERKER / f'{datetime.date.today().isoformat()}-{schluessel}'
    if merker.exists():
        return False
    token, chat = os.environ.get('TELEGRAM_BOT_TOKEN'), os.environ.get('TELEGRAM_CHAT_ID')
    kanal = os.environ.get('KANAL', '')
    text = f'Stoerung{" (" + kanal + ")" if kanal else ""}: {was}\nPipeline: {folge}'
    print(text, flush=True)
    # GEMELDET 16.10.2026: Die lokale Testsuite schickte echte Stoerungsmeldungen aufs Handy (der PC hat die
    # Telegram-Zugangsdaten). Gesendet wird nur aus einem echten GitHub-Lauf.
    if not (token and chat) or os.environ.get('CF_PILOT') == '1' or os.environ.get('GITHUB_ACTIONS') != 'true':
        return False
    try:
        with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage',
                data=urllib.parse.urlencode({'chat_id': chat, 'text': text}).encode(), timeout=20) as r:
            if json.load(r).get('ok') is not True:
                return False
        MERKER.mkdir(parents=True, exist_ok=True)
        merker.write_text(text, encoding='utf-8')
        return True
    except Exception:
        return False


if __name__ == '__main__':
    import sys
    # Aufruf aus Workflow-Schritten: python fabrik/stoerung.py <dienst> <was> <folge>
    melden(*sys.argv[1:4])
