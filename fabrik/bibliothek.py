"""Sichtgepruefte Originalillustrationen; IDs statt frei waehlbarer Dateipfade."""
import hashlib
import json
import re
from pathlib import Path

ORDNER = Path(__file__).resolve().parents[1] / 'assets' / 'illustrationen'


def katalog():
    return json.loads((ORDNER / 'katalog.json').read_text(encoding='utf-8'))['bilder']


def passt_zum_text(eintrag, text):
    """Thematisch gebundene Bilder nicht allein wegen Kanal oder Ortsname anbieten."""
    begriffe = eintrag.get('nur_fuer_themen')
    if begriffe is None:
        return True
    if not isinstance(begriffe,list) or not begriffe or any(not isinstance(b,str) or not b.strip() for b in begriffe):
        return False
    return any(re.search(r'(?<!\w)'+re.escape(b)+r'(?!\w)',text,re.I) for b in begriffe)


def auswahl(kanal, text):
    return [b for b in katalog() if b['kanal']==kanal and passt_zum_text(b,text)]


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
