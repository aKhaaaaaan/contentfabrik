"""Ausdrucksvolle Erzaehlstimme ueber Gemini Flash TTS - erst als Hoerprobe.

GEMELDET 07.10.2026: „Muss man beim Erzaehlen von Stories nicht Emotionen in der
Voice einfuegen?" Kokoro liest gleichmaessig neutral; Regie ist dort nicht moeglich.
GEPRUEFT 07.10.2026 (ai.google.dev/gemini-api/docs/speech-generation): 3.8 Flash TTS
trennt woertlichen Text (`text`) von Regie (`speech_metadata.style`); Momente wie
<short pause> stehen direkt im Text. Antwort: WAV 24 kHz mono 16 bit. Neuer Weg ist
die Interactions-API; als Ausweg der dokumentierte generateContent-Weg mit
gemini-2.5-flash-preview-tts. Gratiskontingent knapp (Berichte: ~10/Tag) -
der Videobau behaelt Kokoro als Rueckfall.
"""
import base64
import io
import json
import os
import urllib.error
import urllib.request
import wave

BASIS = 'https://generativelanguage.googleapis.com/v1beta'


def schluessel():
    """Eigener Stimmen-Schluessel (bezahltes Google-Projekt) vor dem Gratis-Schluessel.

    GEMESSEN 09.10.2026 (Langvideo-Pilot 37888005599): Free Tier 3.8 Flash TTS = 10 Anfragen/Tag,
    danach sprach Kokoro. Ein separates Projekt mit Abrechnung haelt die uebrigen Gemini-Pruefungen
    im kostenlosen Projekt (ai.google.dev/gemini-api/docs/billing: Projekte je Schluessel getrennt).
    """
    return os.environ.get('GEMINI_TTS_API_KEY', '').strip() or os.environ['GEMINI_API_KEY']


def _post(pfad, daten):
    req = urllib.request.Request(BASIS + pfad, data=json.dumps(daten).encode(),
                                 headers={'x-goog-api-key': schluessel(),
                                          'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'TTS HTTP {e.code}: {e.read()[:300].decode("utf-8", "replace")}') from None


def _audio_finden(d):
    """Base64-Audio irgendwo in der Antwort (Interactions: type=audio/data; alt: inlineData)."""
    if isinstance(d, dict):
        if d.get('type') == 'audio' and isinstance(d.get('data'), str):
            return d['data']
        if isinstance(d.get('inlineData'), dict) and str(d['inlineData'].get('mimeType', '')).startswith('audio'):
            return d['inlineData']['data']
        werte = d.values()
    elif isinstance(d, list):
        werte = d
    else:
        return None
    gefunden = None
    for w in werte:
        gefunden = _audio_finden(w) or gefunden  # letzter Treffer = endgueltige Ausgabe
    return gefunden


def als_wav(roh, rate=24000):
    """WAV mit Kopf unveraendert; rohes L16-PCM bekommt einen Kopf."""
    if roh[:4] == b'RIFF':
        return roh
    puffer = io.BytesIO()
    with wave.open(puffer, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(roh)
    return puffer.getvalue()


def sprechen(text, stimme='Charon', stil='', modell='gemini-3.8-flash-tts'):
    """Gibt (wav_bytes, genutztes_modell) zurueck oder wirft RuntimeError."""
    fehler = []
    try:
        inhalt = {'type': 'text', 'text': text}
        if stil:
            inhalt['annotations'] = [{'type': 'speech_metadata', 'style': stil}]
        d = _post('/interactions', {'model': modell, 'input': [{'type': 'user_input', 'content': [inhalt]}],
                                    'response_format': {'type': 'audio'},
                                    'generation_config': {'speech_config': [{'voice': stimme}]}})
        b64 = _audio_finden(d)
        if b64:
            return als_wav(base64.b64decode(b64)), modell
        fehler.append(f'{modell}: keine Audiodaten')
    except (RuntimeError, OSError, ValueError) as e:
        fehler.append(f'{modell}: {str(e)[:200]}')
    alt = 'gemini-2.5-flash-preview-tts'
    try:
        d = _post(f'/models/{alt}:generateContent', {
            'contents': [{'parts': [{'text': (f'Say in this style - {stil}: ' if stil else '') + text}]}],
            'generationConfig': {'responseModalities': ['AUDIO'], 'speechConfig': {
                'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': stimme}}}}})
        b64 = _audio_finden(d)
        if b64:
            return als_wav(base64.b64decode(b64)), alt
        fehler.append(f'{alt}: keine Audiodaten')
    except (RuntimeError, OSError, ValueError) as e:
        fehler.append(f'{alt}: {str(e)[:200]}')
    raise RuntimeError(' | '.join(fehler))
