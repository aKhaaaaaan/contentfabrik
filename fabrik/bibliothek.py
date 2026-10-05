"""Sichtgepruefte Originalillustrationen; IDs statt frei waehlbarer Dateipfade."""
import hashlib
import json
from pathlib import Path

ORDNER = Path(__file__).resolve().parents[1] / 'assets' / 'illustrationen'


def katalog():
    return json.loads((ORDNER / 'katalog.json').read_text(encoding='utf-8'))['bilder']


def bild(kennung, kanal):
    eintrag = next((b for b in katalog() if b['id'] == kennung), None)
    if not eintrag or eintrag['kanal'] != kanal:
        raise ValueError('Unbekannte oder fuer diesen Kanal ungeeignete Illustration')
    pfad = (ORDNER / eintrag['datei']).resolve()
    if pfad.parent != ORDNER.resolve() or not pfad.is_file():
        raise ValueError('Illustrationsdatei fehlt oder verlaesst die Bibliothek')
    if hashlib.sha256(pfad.read_bytes()).hexdigest() != eintrag['sha256']:
        raise ValueError('Illustration wurde nach der Sichtkontrolle veraendert')
    return pfad


def signatur():
    return (ORDNER / 'katalog.json').read_bytes()
