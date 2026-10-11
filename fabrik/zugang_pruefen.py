"""Anbieterzugang lesend pruefen; keine Generierung, Schluessel, URLs oder Rohfehler ausgeben."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request


class KeinRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError('Weiterleitung im Zugangscheck abgelehnt')


def pruefen(auftrag):
    name, url, headers, gesetzt, feld = auftrag
    result = {'anbieter': name, 'ok': False}
    if not gesetzt:
        return result | {'status': 'nicht_eingerichtet'}
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Contentfabrik-Autorenvergleich/1.0', **headers})
        with urllib.request.build_opener(KeinRedirect()).open(request, timeout=20) as response:
            data = json.load(response)
        models = data.get(feld)
        if not isinstance(models, list) or not models:
            return result | {'status': 'ungueltige_modellliste'}
        return result | {'ok': True, 'status': 'erreichbar', 'modellanzahl': len(models)}
    except urllib.error.HTTPError as exc:
        return result | {'status': 'http_fehler', 'http': exc.code}
    except Exception as exc:
        return result | {'status': 'netz_oder_antwortfehler', 'fehler_typ': type(exc).__name__}


def main():
    text_key = os.environ.get('GEMINI_API_KEY', '')
    tts_key = os.environ.get('GEMINI_TTS_API_KEY') or text_key
    groq_key = os.environ.get('GROQ_API_KEY', '')
    cloud_key = os.environ.get('CLOUDFLARE_AI_TOKEN', '')
    account = os.environ.get('CLOUDFLARE_ACCOUNT_ID') or '09e49429346ef780d0e59a7fae936f95'
    if not re.fullmatch(r'[a-fA-F0-9]{32}', account):
        account = ''
    requests = []
    for name, key in (('Gemini Text', text_key), ('Gemini Stimme', tts_key)):
        url = 'https://generativelanguage.googleapis.com/v1beta/models?' + urllib.parse.urlencode(
            {'key': key, 'pageSize': 1000})
        requests.append((name, url, {}, bool(key), 'models'))
    requests += [
        ('Groq', 'https://api.groq.com/openai/v1/models',
         {'Authorization': 'Bearer ' + groq_key}, bool(groq_key), 'data'),
        ('Cloudflare Workers AI', f'https://api.cloudflare.com/client/v4/accounts/{account}/ai/models/search',
         {'Authorization': 'Bearer ' + cloud_key}, bool(account and cloud_key), 'result')]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(pruefen, requests))
    report = {'zugang': results, 'hinweis': 'Nur Zugangs-/Modelllistencheck; Generierungsquoten und Qualitaet ungetestet.'}
    target = Path('ausgabe/zugangscheck.json')
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report), flush=True)
    return 0 if all(r['ok'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
