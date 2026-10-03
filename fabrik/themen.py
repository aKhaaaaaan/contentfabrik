"""Themen vom Nutzer per Telegram: „KI: ...", „Business: ..." oder ein YouTube-Link.

GEMELDET: Der Nutzer sieht virale Videos und will deren THEMA einbringen.
Uebernommen wird nur das Thema (beim Link: der Titel ueber die offizielle
YouTube-API) - recherchiert und erzaehlt wird aus eigenen Quellen, nie aus
fremdem Text (Urheberrecht, YouTube-Regel „wiederverwendete Inhalte").

Telegram haelt unbestaetigte Nachrichten nur 24 Stunden - darum holt ein
eigener Zeitplan (themen.yml) sie alle 4 Stunden ab und legt sie in die
Warteschlange themen/warteschlange.json; jeder Video-Lauf nimmt das aelteste
Thema seines Kanals.

Aufruf:  python fabrik/themen.py abholen
"""
import datetime, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

DATEI = Path('themen/warteschlange.json')
KANAELE = {'ai-tools-explained': ('ki', 'ai', 'tools', 'tool'),
           'business-origin-stories': ('business', 'firma', 'story', 'marke', 'brand')}
HILFE = ('So schickst du mir ein Thema:\n'
         '• „KI: kostenlose Bild-KIs\" → AI Tools Explained\n'
         '• „Business: Wie Tonka Trucks entstanden\" → Business Origin Stories\n'
         '• oder einfach einen YouTube-Link (ich nehme nur das Thema, nie den Text)')


def _tg(methode, **felder):
    token = os.environ['TELEGRAM_BOT_TOKEN']
    return json.load(urllib.request.urlopen(f'https://api.telegram.org/bot{token}/{methode}',
                                            data=urllib.parse.urlencode(felder).encode(), timeout=30))


def laden():
    return json.loads(DATEI.read_text(encoding='utf-8')) if DATEI.exists() else []


def speichern(liste):
    DATEI.parent.mkdir(exist_ok=True)
    DATEI.write_text(json.dumps(liste, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def youtube_titel(text):
    m = re.search(r'(?:youtu\.be/|v=|shorts/)([\w-]{11})', text)
    schluessel = os.environ.get('YOUTUBE_API_KEY')
    if not m or not schluessel:
        return None
    d = json.load(urllib.request.urlopen('https://www.googleapis.com/youtube/v3/videos?' + urllib.parse.urlencode(
        {'part': 'snippet', 'id': m[1], 'key': schluessel}), timeout=20))
    return d['items'][0]['snippet']['title'] if d.get('items') else None


def zuordnen(text):
    """(kanal, thema) aus der Nachricht - Vorsilbe gewinnt, sonst entscheidet die KI."""
    m = re.match(r'\s*(\w+)\s*:\s*(.+)', text, re.S)
    if m:
        for kanal, woerter in KANAELE.items():
            if m[1].lower() in woerter:
                return kanal, m[2].strip()
    titel = youtube_titel(text)
    thema = titel or text.strip()
    try:
        from skript import gemini
        wahl, _ = gemini('Which channel fits this topic best? "ai-tools-explained" (AI tools and models) or '
                         f'"business-origin-stories" (how companies and brands started). Topic: {thema}',
                         {'type': 'OBJECT', 'properties': {'kanal': {'type': 'STRING',
                          'enum': list(KANAELE)}}, 'required': ['kanal']}, temperatur=0.0)
        return wahl['kanal'], thema
    except Exception:
        return None, thema


def abholen():
    chat = str(os.environ['TELEGRAM_CHAT_ID'])
    updates = _tg('getUpdates').get('result', [])
    liste, letzte = laden(), None
    for u in updates:
        letzte = u['update_id']
        m = u.get('message') or {}
        text = (m.get('text') or '').strip()
        if str(m.get('chat', {}).get('id')) != chat or not text:
            continue  # nur Nachrichten des Nutzers
        if text.lower() in ('/start', 'hilfe', '/hilfe', 'help', 'hallo'):
            _tg('sendMessage', chat_id=chat, text=HILFE)
            continue
        # Antwort auf die Hoerprobe („Stimmen: 2, 7, 9") - kein Video-Thema
        if re.match(r'\s*stimm', text, re.I):
            nummern = [int(n) for n in re.findall(r'\d+', text)][:3]
            Path('themen').mkdir(exist_ok=True)
            Path('themen/stimmwahl.json').write_text(json.dumps(
                {'nummern': nummern, 'eingang': datetime.date.today().isoformat()}) + '\n', encoding='utf-8')
            _tg('sendMessage', chat_id=chat, text=f'✅ Stimmwahl gespeichert: {nummern}. '
                                                  'Ich stelle die Kanäle darauf um.')
            continue
        kanal, thema = zuordnen(text)
        if not kanal:
            _tg('sendMessage', chat_id=chat, text='❓ Welcher Kanal? ' + HILFE)
            continue
        liste.append({'kanal': kanal, 'thema': thema[:200], 'eingang': datetime.date.today().isoformat()})
        warten = sum(1 for x in liste if x['kanal'] == kanal)
        _tg('sendMessage', chat_id=chat, text=f'✅ Gemerkt für {kanal}: „{thema[:120]}\"\n'
                                              f'Kommt beim nächsten Lauf dran (Platz {warten} in der Warteschlange).')
    if letzte is not None:
        _tg('getUpdates', offset=letzte + 1)  # als gelesen bestaetigen
    speichern(liste)
    print(f'{len(updates)} Nachrichten, Warteschlange: {len(liste)}')


def nehmen(kanal):
    """Aeltestes Thema des Kanals aus der Warteschlange holen (oder '')."""
    liste = laden()
    for i, x in enumerate(liste):
        if x['kanal'] == kanal:
            liste.pop(i)
            speichern(liste)
            return x['thema']
    return ''


if __name__ == '__main__':
    if sys.argv[1:] == ['abholen']:
        sys.path.insert(0, str(Path(__file__).parent))
        abholen()
