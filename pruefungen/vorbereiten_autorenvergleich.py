"""Quellenpakete einmal abrufen und fuer beide Autoren unveraendert einfrieren."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
import trends


def bereinigen(text):
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    return text.strip()


def main():
    faelle = []
    def fall(ident, kanal, thema, q, herkunft):
        if not q or len(q.get('text', '')) < 1000:
            raise ValueError(f'Keine ausreichend umfangreiche Quelle fuer {ident}')
        q = dict(q, text=bereinigen(q['text'])[:7000])
        faelle.append({'id': ident, 'kanal': kanal, 'thema': thema, 'format': 'erklaerung'
                      if kanal == 'ai-tools-explained' else 'geschichte',
                      'quellen': [q], 'herkunft': herkunft,
                      'quellen_sha256': hashlib.sha256(q['text'].encode()).hexdigest()})
    for ident, thema, datei, kanal in [
            ('qwen-bilder', 'Qwen Image: transparency, local edits and reference images',
             'qwen-bildworkflow', 'ai-tools-explained'),
            ('nintendo-karten', 'Nintendo: the early playing-card business and its product challenges',
             'nintendo-karten', 'business-origin-stories')]:
        s = json.loads(Path(f'piloten/{datei}.json').read_text(encoding='utf-8'))
        fall(ident, kanal, thema, s['belege'][0], 'Gespeicherter Quelltext aus Pilot; keine Narration uebernommen')
    for ident, thema, url, name in [
            ('kokoro-stimme', 'Kokoro: a practical local voice workflow and its limits',
             'https://huggingface.co/hexgrad/Kokoro-82M/raw/main/README.md', 'hexgrad/Kokoro-82M'),
            ('whisper-transkript', 'Whisper: turning recorded speech into text and checking the result',
             'https://raw.githubusercontent.com/openai/whisper/main/README.md', 'OpenAI Whisper')]:
        req = urllib.request.Request(url, headers={'User-Agent': 'Contentfabrik/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode('utf-8')
        fall(ident, 'ai-tools-explained', thema,
             {'name': name, 'quelle': 'Original README', 'url': url, 'text': text}, 'Original-README frisch abgerufen')
    for ident, titel, thema in [('lego-anfang', 'The Lego Group', 'LEGO: wooden toys and the early brick business'),
                               ('nike-anfang', 'Nike, Inc.', 'Nike: Blue Ribbon Sports and the early footwear business')]:
        fall(ident, 'business-origin-stories', thema, trends.wikipedia(titel), 'Wikipedia frisch abgerufen')
    ziel = Path('vergleiche/autoren/faelle.json')
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps({'erstellt_am_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                               'faelle': faelle}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'faelle': [{'id': f['id'], 'zeichen': len(f['quellen'][0]['text']),
                                 'quellen_sha256': f['quellen_sha256']} for f in faelle]}, indent=2))


if __name__ == '__main__':
    main()
