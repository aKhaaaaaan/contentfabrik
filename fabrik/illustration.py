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
Eine konkrete Bildkritik geht in den zweiten Auftrag, die Szene bleibt erhalten.
Nach zwei Versuchen oder bei ausgefallener Pruefung: Foto-/Clip-Rueckfall.
"""
import base64, io, json, os, uuid, urllib.error, urllib.request
from pathlib import Path
from PIL import Image, ImageOps
import prompts

KONTO = os.environ.get('CLOUDFLARE_ACCOUNT_ID', '09e49429346ef780d0e59a7fae936f95')
FIGUREN = Path(__file__).resolve().parent.parent / 'figuren'
GEZAEHLT = {'bilder': 0, 'abgelehnt': 0}


def _anfrage(modell, felder, datei=None):
    token = os.environ.get('CLOUDFLARE_AI_TOKEN')
    if not token:
        return None
    url = f'https://api.cloudflare.com/client/v4/accounts/{KONTO}/ai/run/@cf/black-forest-labs/{modell}'
    kopf = {'Authorization': 'Bearer ' + token, 'User-Agent': 'Contentfabrik/1.0'}
    if datei:  # FLUX.2 erwartet multipart (Referenzbild)
        # Laut Cloudflare muessen Referenzen kleiner als 512x512 sein.
        # Original im Projekt erhalten; nur die API-Kopie vorbereiten.
        with Image.open(datei) as im:
            referenz = ImageOps.exif_transpose(im).convert('RGB')
            referenz.thumbnail((511, 511), Image.Resampling.LANCZOS)
            puffer = io.BytesIO()
            referenz.save(puffer, 'JPEG', quality=95)
        g = uuid.uuid4().hex
        teile = [f'--{g}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in felder.items()]
        teile.append(f'--{g}\r\nContent-Disposition: form-data; name="input_image_0"; filename="ref.jpg"\r\n'
                     'Content-Type: image/jpeg\r\n\r\n'.encode() + puffer.getvalue() + b'\r\n')
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


def pruefen(roh, szene, referenz=None, videoformat='short'):
    """Konkreter Bildbefund; fehlende Pruefung nimmt kein ungeprueftes Bild an."""
    if not os.environ.get('GEMINI_API_KEY'):
        return {'ok': False, 'grund': 'Bildpruefung nicht eingerichtet'}
    try:
        from skript import gemini, SEHEN
        bilder = [roh] + ([Path(referenz).read_bytes()] if referenz else [])
        a, _ = gemini(prompts.bildpruefung(szene, bool(referenz), videoformat),
                      {'type': 'OBJECT', 'properties': {'ok': {'type': 'BOOLEAN'}, 'grund': {'type': 'STRING'}},
                       'required': ['ok', 'grund']}, temperatur=0.1, bilder=bilder, modelle=SEHEN)
        if a.get('ok') is not True:
            print('Illustration verworfen:', a.get('grund', '')[:120])
        return {'ok': a.get('ok') is True, 'grund': str(a.get('grund', ''))[:220]}
    except Exception as e:
        print('Bildpruefung nicht moeglich - Foto/Clip verwenden:', type(e).__name__)
        return {'ok': False, 'grund': 'Bildpruefung nicht verfuegbar'}


def bild(szene, ziel, kanal=None, figur=False, versuche=2, videoformat='short'):
    """Szene als Illustration (hochkant). figur=True: die feste Figur des Kanals per Referenzbild.
    Gibt den Pfad oder None zurueck."""
    if not os.environ.get('GEMINI_API_KEY'):
        return None
    ref = FIGUREN / f'{kanal}.jpg' if kanal else None
    ref = ref if figur and ref and ref.exists() else None
    korrektur = ''
    for v in range(versuche):
        text = prompts.illustration(szene, bool(ref), korrektur, videoformat)
        if ref:
            # Klein ist bei Cloudflare auf vier Schritte festgelegt.
            breite, hoehe = (1360, 768) if videoformat == 'lang' else (768, 1360)
            roh = _anfrage('flux-2-klein-4b', {'prompt': text, 'width': breite, 'height': hoehe}, datei=ref)
        else:
            roh = _anfrage('flux-1-schnell', {'prompt': text, 'steps': 8})
        if not roh:
            continue
        try:
            with Image.open(io.BytesIO(roh)) as im:
                im.verify()
                if min(im.size) < 512:
                    korrektur = 'Produce a sharp complete image, not a small preview.'
                    continue
        except (OSError, ValueError):
            print('Ungueltige Bilddatei - kein Einsatz im Video')
            continue
        bewertung = pruefen(roh, szene, ref, videoformat)
        if bewertung['ok']:
            Path(ziel).write_bytes(roh)
            GEZAEHLT['bilder'] += 1
            return Path(ziel)
        korrektur = bewertung['grund']
        if korrektur in ('Bildpruefung nicht verfuegbar', 'Bildpruefung nicht eingerichtet'):
            break  # kein zweites Bild erzeugen, wenn der Pruefer ausgefallen ist
    return None
