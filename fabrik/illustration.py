"""Illustrationen im Spiel-Plakat-Stil (gemalt, halb-realistisch) - Cloudflare Workers AI, kostenlos.

GEMELDET 04.10.2026: „Das Video wirkt langweilig und eiskalt" - der Nutzer will
den Look von Open-World-Spielplakaten, mit EIGENEN erfundenen Figuren (keine
echten Spielfiguren, kein Spielname). Gewaehlt: je Kanal eine feste Figur
(figuren/<kanal>.jpg). GEMESSEN: FLUX.1 [schnell] kennt keinen festen Seed;
FLUX.2 [klein] 4B (Apache 2.0, kommerziell frei) uebernimmt die Figur aus
einem Referenzbild - in Tests klar wiedererkennbar (Hut/Anzug, Brille/Jacke).

Regeln: nie Schrift oder Logos im KI-Bild (KI-Schrift wird Buchstabensalat,
fremde Logos sind tabu); nie Ersatz fuer echte Fotos von Firmen/Produkten;
jedes Bild prueft Gemini (Schrift, Logos, verformte Haende/Gesichter).
Einmal von Cloudflares Filter abgelehnt (ohne erkennbaren Grund) -> zweiter
Versuch mit schlichterem Auftrag, sonst None (Aufrufer nimmt dann Foto/Clip).
"""
import base64, json, os, uuid, urllib.error, urllib.request
from pathlib import Path

KONTO = os.environ.get('CLOUDFLARE_ACCOUNT_ID', '09e49429346ef780d0e59a7fae936f95')
FIGUREN = Path(__file__).resolve().parent.parent / 'figuren'
STIL = ('semi-realistic digital painting in the style of open-world crime video game key art posters, realistic '
        'proportions, painterly brush shading, strong ink outlines, dramatic rim lighting, high contrast, vivid '
        'saturated colors, no text, no letters, no signs, no watermark, no logo, no brand names')
GEZAEHLT = {'bilder': 0, 'abgelehnt': 0}


def _anfrage(modell, felder, datei=None):
    token = os.environ.get('CLOUDFLARE_AI_TOKEN')
    if not token:
        return None
    url = f'https://api.cloudflare.com/client/v4/accounts/{KONTO}/ai/run/@cf/black-forest-labs/{modell}'
    kopf = {'Authorization': 'Bearer ' + token, 'User-Agent': 'Contentfabrik/1.0'}
    if datei:  # FLUX.2 erwartet multipart (Referenzbild)
        g = uuid.uuid4().hex
        teile = [f'--{g}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in felder.items()]
        teile.append(f'--{g}\r\nContent-Disposition: form-data; name="input_image_0"; filename="ref.jpg"\r\n'
                     'Content-Type: image/jpeg\r\n\r\n'.encode() + Path(datei).read_bytes() + b'\r\n')
        teile.append(f'--{g}--\r\n'.encode())
        daten, kopf['Content-Type'] = b''.join(teile), f'multipart/form-data; boundary={g}'
    else:
        daten, kopf['Content-Type'] = json.dumps(felder).encode(), 'application/json'
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(url, data=daten, headers=kopf), timeout=120))
    except urllib.error.HTTPError as e:
        d = json.loads(e.read().decode(errors='replace') or '{}')
    if d.get('success'):
        return base64.b64decode(d['result']['image'])
    GEZAEHLT['abgelehnt'] += 1
    print('Illustration abgelehnt:', str(d.get('errors'))[:140])
    return None


def pruefen(roh, szene):
    """Gemini schaut drauf (sparsam: Lite-Modelle zuerst). Ohne Schluessel: durchlassen."""
    if not os.environ.get('GEMINI_API_KEY'):
        return True
    try:
        from skript import gemini, SEHEN
        a, _ = gemini('This AI illustration will be shown in a YouTube video about: "' + szene + '". Reject it if it '
                      'contains ANY readable or garbled text, letters, numbers, signatures, watermarks or brand logos, '
                      'or deformed hands/faces/extra limbs, or objects that make no physical sense (light from nowhere, '
                      'merged parts). Answer ok=true only if it is clean.',
                      {'type': 'OBJECT', 'properties': {'ok': {'type': 'BOOLEAN'}, 'grund': {'type': 'STRING'}},
                       'required': ['ok']}, temperatur=0.1, bilder=[roh], modelle=SEHEN)
        if not a['ok']:
            print('Illustration verworfen:', a.get('grund', '')[:120])
        return bool(a['ok'])
    except Exception as e:
        print('Bildpruefung nicht moeglich, Bild wird genommen:', str(e)[:100])
        return True


def bild(szene, ziel, kanal=None, figur=False, versuche=2):
    """Szene als Illustration (hochkant). figur=True: die feste Figur des Kanals per Referenzbild.
    Gibt den Pfad oder None zurueck."""
    ref = FIGUREN / f'{kanal}.jpg' if kanal else None
    for v in range(versuche):
        # Zweiter Versuch schlichter - der Filter lehnte einmal ohne erkennbaren Grund ab
        text = szene if v == 0 else szene.split(',')[0]
        if figur and ref and ref.exists():
            roh = _anfrage('flux-2-klein-4b', {'prompt': f'this character from the reference image, same face and '
                                                         f'clothes, {text}, {STIL}', 'width': 768, 'height': 1024,
                                              'steps': 4}, datei=ref)
        else:
            roh = _anfrage('flux-1-schnell', {'prompt': f'{text}, {STIL}', 'steps': 8})
        if roh and pruefen(roh, szene):
            Path(ziel).write_bytes(roh)
            GEZAEHLT['bilder'] += 1
            return Path(ziel)
    return None
