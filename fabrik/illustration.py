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
import base64, io, json, os, time, uuid, urllib.error, urllib.request
from pathlib import Path
from PIL import Image, ImageOps
import prompts

KONTO = os.environ.get('CLOUDFLARE_ACCOUNT_ID', '09e49429346ef780d0e59a7fae936f95')
FIGUREN = Path(__file__).resolve().parent.parent / 'figuren'
GEZAEHLT = {'bilder': 0, 'abgelehnt': 0}


# GEMESSEN 08.10.2026 (Lauf 37749486997): Cloudflare meldete „daily free allocation
# used up", obwohl das Dashboard „0/10k heute" zeigte (Verbrauch lag am Vorabend) -
# offenbar zaehlt das Limit rollierend. Der Lauf versuchte trotzdem 5x neu zu bauen.
# Merker im Arbeitsordner: weitere Anfragen sparen, lauf.py bricht ohne Wiederholung ab.
KONTINGENT_LEER = Path('bildkontingent-leer.flag')


def _anfrage(modell, felder, datei=None, charakter=None):
    token = os.environ.get('CLOUDFLARE_AI_TOKEN')
    if not token or KONTINGENT_LEER.exists():
        return None
    url = f'https://api.cloudflare.com/client/v4/accounts/{KONTO}/ai/run/@cf/black-forest-labs/{modell}'
    kopf = {'Authorization': 'Bearer ' + token, 'User-Agent': 'Contentfabrik/1.0'}
    if datei or charakter or modell.startswith('flux-2'):  # FLUX.2 (4B/9B) erwartet multipart
        # Laut Cloudflare muessen Referenzen kleiner als 512x512 sein.
        # Original im Projekt erhalten; nur die API-Kopie vorbereiten.
        g = uuid.uuid4().hex
        teile = [f'--{g}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in felder.items()]
        for index, referenz_datei in enumerate([p for p in (datei, charakter) if p is not None]):
            with Image.open(io.BytesIO(referenz_datei) if isinstance(referenz_datei, bytes) else referenz_datei) as im:
                referenz = ImageOps.exif_transpose(im).convert('RGB')
                referenz.thumbnail((511, 511), Image.Resampling.LANCZOS)
                puffer = io.BytesIO()
                referenz.save(puffer, 'JPEG', quality=95)
            teile.append(f'--{g}\r\nContent-Disposition: form-data; name="input_image_{index}"; filename="ref.jpg"\r\n'
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
    if 'free allocation' in str(d.get('errors')).lower():
        KONTINGENT_LEER.write_text('Cloudflare Workers AI: Gratiskontingent aufgebraucht\n', encoding='utf-8')
    return None


PRUEF_PAUSE_S = 30


def pruefen(roh, szene, referenz=None, videoformat='short'):
    """Konkreter Bildbefund; fehlende Pruefung nimmt kein ungeprueftes Bild an."""
    if not os.environ.get('GEMINI_API_KEY'):
        return {'ok': False, 'grund': 'Bildpruefung nicht eingerichtet'}
    try:
        from skript import gemini, SEHEN
        bilder = [roh] + ([Path(referenz).read_bytes()] if referenz else [])
        auftrag = (prompts.bildpruefung(szene, bool(referenz), videoformat),
                   {'type': 'OBJECT', 'properties': {'ok': {'type': 'BOOLEAN'}, 'grund': {'type': 'STRING'}},
                    'required': ['ok', 'grund']})
        try:
            a, _ = gemini(*auftrag, temperatur=0.1, bilder=bilder, modelle=SEHEN)
        except Exception as e:
            # GEMESSEN 09.10.2026 (Langvideo-Pilot 37888005599): 20x 'Bildpruefung nicht verfuegbar'
            # (Zeitlimit/Ueberlast der Lite-Modelle) -> jedes Bild verworfen, Ersatzbilder aufgebraucht.
            # Kurze Ueberlast: einmal nach 30 s neu pruefen statt ein gutes Bild wegzuwerfen.
            print('Bildpruefung ueberlastet, neuer Versuch in 30 s:', type(e).__name__)
            time.sleep(PRUEF_PAUSE_S)
            a, _ = gemini(*auftrag, temperatur=0.1, bilder=bilder, modelle=SEHEN)
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
    # Erzeugung UND Bildpruefung sehen dieselbe schriftfreie Szene - sonst
    # verwirft die Pruefung ein Bild, weil das verlangte Wort 'BILLING' fehlt.
    szene = prompts.szene_ohne_schrift(szene)
    ref = FIGUREN / f'{kanal}.jpg' if kanal else None
    ref = ref if figur and ref and ref.exists() else None
    breite, hoehe = (1360, 768) if videoformat == 'lang' else (768, 1360)
    szene_roh = None
    if ref:
        # Erst eine neue Szene aufbauen. Das Stadtportraet allein als Referenz
        # hielt im KFC-Tageslauf beide Versuche im falschen Hintergrund fest.
        szene_roh = _anfrage('flux-2-klein-4b', {'prompt': prompts.illustration(szene, False, videoformat=videoformat),
                            'width': breite, 'height': hoehe})
        if not szene_roh:
            return None
        try:
            with Image.open(io.BytesIO(szene_roh)) as im:
                im.verify()
                if min(im.size) < 512:
                    return None
        except (OSError, ValueError):
            return None
    korrektur = ''
    for v in range(versuche):
        text = prompts.illustration(szene, bool(ref), korrektur, videoformat)
        if ref:
            text = prompts.figur_in_szene(szene, korrektur, videoformat)
        if ref or v == 0:
            # Klein ist bei Cloudflare auf vier Schritte festgelegt.
            felder = {'prompt': text, 'width': breite, 'height': hoehe}
            roh = (_anfrage('flux-2-klein-4b', felder, datei=szene_roh, charakter=ref) if ref
                   else _anfrage('flux-2-klein-4b', felder))
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
        # Fehlerbilder fuer echte Sichtkontrolle behalten, niemals als Videomaterial verwenden.
        if not bewertung['ok']:
            fehlerbild = Path(ziel).with_name(Path(ziel).stem + f'_abgelehnt_{v}.jpg')
            fehlerbild.write_bytes(roh)
            fehlerbild.with_suffix('.json').write_text(json.dumps(
                {'szene': szene, 'bewertung': bewertung, 'referenz': str(ref) if ref else None},
                ensure_ascii=False, indent=2), encoding='utf-8')
        if bewertung['ok']:
            Path(ziel).write_bytes(roh)
            GEZAEHLT['bilder'] += 1
            return Path(ziel)
        korrektur = bewertung['grund']
        if korrektur in ('Bildpruefung nicht verfuegbar', 'Bildpruefung nicht eingerichtet'):
            break  # kein zweites Bild erzeugen, wenn der Pruefer ausgefallen ist
    return None
