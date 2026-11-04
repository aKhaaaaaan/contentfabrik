"""Unabhaengige Pruefung lokaler Autorenentwuerfe mit bestehenden Freigabefiltern."""
import base64
import copy
import datetime as dt
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fabrik'))
import entwurf_cache
import dramaturgie
import erfolg
import kanalstandard
import ki_speicher
import lernen
import nachbessern
import prompts
import skript
import themen
import texte
import vorrat
from qualitaet import skript_gruende

KANAELE = ('business-origin-stories', 'ai-tools-explained')
# 04.11.2026: auch Langvideos (KI 41333732613 am 01.11.: Claude-Limit, Groq-Reserve 11422 > 7900 Tokens).
PROFILORDNER = {'short': 'kanaele', 'lang': 'formate'}
AUTOR_MAX_S = {'short': 480, 'lang': 1200}
PRUEF_S = {'short': 480, 'lang': 1200}


def videoformat(p):
    f = p.get('format', 'short') if isinstance(p, dict) else None
    if f not in PROFILORDNER:
        raise ValueError('Unbekanntes Videoformat')
    return f


def profil_pfad(p):
    return Path(PROFILORDNER[videoformat(p)]) / (p['kanal'] + '.json')


def paket_lesen(roh):
    """Langvideos (bis ~1800 Woerter + 5 Quellen) sprengen die 48-KB-Grenze eines Secrets - gzip+Base64."""
    if roh.startswith('gz:'):
        with gzip.GzipFile(fileobj=__import__('io').BytesIO(base64.b64decode(roh[3:], validate=True))) as f:
            daten = f.read(500_001)
        if len(daten) > 500_000:
            raise ValueError('Brueckenauftrag entpackt zu gross')
        return json.loads(daten)
    return json.loads(roh)


def sha(d):
    return hashlib.sha256(json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def keine_extras(d, schema):
    if isinstance(d, dict) and schema.get('type') == 'OBJECT':
        props = schema.get('properties', {})
        return all(k in props and keine_extras(v, props[k]) for k, v in d.items())
    if isinstance(d, list) and schema.get('type') == 'ARRAY':
        return all(keine_extras(v, schema['items']) for v in d)
    return True


def paket_pruefen(p, kennung, jetzt=None):
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    if not isinstance(p, dict) or p.get('version') != 1 or p.get('id') != kennung \
            or not re.fullmatch(r'[a-f0-9]{24}', kennung or '') or p.get('kanal') not in KANAELE:
        raise ValueError('Ungueltiger Brueckenauftrag')
    ab = dt.datetime.fromisoformat(p['erstellt_utc'])
    if ab.tzinfo is None or not 0 <= (jetzt - ab).total_seconds() <= 6 * 3600:
        raise ValueError('Brueckenauftrag abgelaufen')
    profil_p = profil_pfad(p)
    if p.get('profil') != entwurf_cache.profil_key(profil_p) or p.get('prompt_version') != prompts.VERSION:
        raise ValueError('Produktionsprofil seit dem Entwurf geaendert')
    q = p.get('belege')
    if not isinstance(q, list) or not q or p.get('quellen_sha') != sha(q):
        raise ValueError('Quellenbindung fehlt oder ist ungueltig')
    if any(not isinstance(x, dict) or set(x) - {'name', 'url', 'quelle', 'text'}
           or not all(isinstance(x.get(k), str) and x[k].strip() for k in ('name', 'url', 'text')) for x in q):
        raise ValueError('Vollstaendige Quelltexte erforderlich')
    if not isinstance(p.get('thema'), str) or not 0 < len(p['thema']) <= 200:
        raise ValueError('Thema fehlt')
    autor_s = p.get('autor_s', 0)
    if isinstance(autor_s, bool) or not isinstance(autor_s, (int, float)) or not math.isfinite(autor_s) or not 0 <= autor_s <= AUTOR_MAX_S[videoformat(p)]:
        raise ValueError('Ungueltige Autorenzeit')
    d = p.get('entwurf')
    if not keine_extras(d, skript.SKRIPT_SCHEMA) or not ki_speicher.schema_ok(d, skript.SKRIPT_SCHEMA):
        raise ValueError('Autorenentwurf passt nicht zum Schema')
    if not d['teile'] or any(not x['text'].strip() for x in d['teile']):
        raise ValueError('Leere Sprechphase')
    profil = kanalstandard.laden(profil_p)
    if dramaturgie.videoformat(profil) != videoformat(p):
        raise ValueError('Profil passt nicht zum Videoformat')
    worte = sum(len(x['text'].split()) for x in d['teile'])
    lo, hi = skript.wortgrenzen(profil)
    if not lo <= worte <= hi:
        raise ValueError('Sprechtext ausserhalb des aktuellen Wortbudgets')
    return profil


def render_skript(p, profil):
    d = copy.deepcopy(p['entwurf'])
    gelernt = lernen.erprobte_einstellungen(p['kanal'])
    schluessel = ' '.join(d['schluesselwoerter']).lower().split()
    zeile = lambda z: ' '.join(f'*{w}*' if w.strip('.,!?').lower() in schluessel else w for w in z.split())
    s = dict(kanal=profil['name'], thema=d['thema'], titel=[zeile(d['titel_zeile1']), zeile(d['titel_zeile2'])],
        teile=d['teile'], stimme=erfolg.waehlen(p['kanal'], 'stimme', profil.get('stimmen', ['am_michael']),
                                              videoformat=dramaturgie.videoformat(profil)), tempo=1.05,
        titel_farbe=profil.get('titel_farbe', '#20D2BE'), untertitel_profil=gelernt.get('untertitel_profil', 'ruhig'),
        posten_ny=profil.get('posten_ny', '15:00'), laenge_s=dramaturgie.laengen(profil), videoformat=dramaturgie.videoformat(profil),
        format=profil['format'], musik_suche=d.get('musik_suche') or profil.get('musik_suche', []),
        regeln=lernen.regeln(p['kanal']), winkel=profil.get('_winkel', ''),
        hintergrund_suche=profil.get('hintergrund_suche', ''), bilder=[],
        beschreibung=d['beschreibung'] + ''.join(f"\nSource: Wikipedia - {q['name']} (CC BY-SA)"
                                                 for q in p['belege'] if q.get('quelle') == 'Wikipedia'),
        hashtags=texte.hashtags_bereinigen(d['hashtags'], json.dumps([d.get('thema'), d.get('titel_zeile1'),
            d.get('titel_zeile2'), d.get('beschreibung'), [t.get('text') for t in d.get('teile', [])]], ensure_ascii=False)),
        quellen=[q['url'] for q in p['belege']], belege=copy.deepcopy(p['belege']),
        modell='codex:chatgpt-lokal', prompt_version=prompts.VERSION,
        pruefung={'ok': False, 'probleme': ['Unabhaengige Pruefung steht aus']})
    s['musik_suche'] = [q.strip()[:100] for q in d.get('musik_suche', [])
                       if isinstance(q, str) and q.strip()][:3] or profil.get('musik_suche', [])
    return {**gelernt, **s}


def bewerten(p, kennung, modus='pruefen'):
    profil = paket_pruefen(p, kennung)
    if modus not in ('pruefen', 'vorrat'):
        raise ValueError('Unbekannter Brueckenmodus')
    s = render_skript(p, profil)
    bericht = {'id': kennung, 'kanal': p['kanal'], 'modus': modus, 'status': 'ungeprueft',
               'freigabe': False, 'quellen_sha': p['quellen_sha'], 'entwurf_sha': sha(p['entwurf']),
               'pruefmodelle': [], 'vorrat_geschrieben': False}
    lang = videoformat(p) == 'lang'
    if modus == 'vorrat':
        import trends
        # Ein Langvideo erzaehlt bewusst die ganze Geschichte eines gelaufenen Shorts (langvideo.py) -
        # Short-Wiederholungssperren gelten dafuer nicht; doppelte Langvideos verhindert langvideo.faellig().
        wiederholt = not lang and themen.wiederholung_gesperrt(p['kanal'], s['thema'], s['titel'])
        vorhanden = any(vorrat.gueltig(e, profil) and
            (e.get('thema_eingabe') == p['thema'] or sha(e.get('skript', {}).get('belege')) == p['quellen_sha'])
            for _, e in vorrat.eintraege(p['kanal']))
        if wiederholt or vorhanden or (not lang and trends.bereits_gezeigte_quellen(p['kanal'], s)):
            bericht.update(status='gesperrt', gruende=['Thema oder Quelle bereits geliefert oder im Vorrat'])
            return bericht
    original = skript.gemini
    def pruefer(*a, **kw):
        d, m = original(*a, **kw)
        bericht['pruefmodelle'].append(m)
        return d, m
    skript.gemini = pruefer
    try:
        # Unveraenderte produktive Nachpruefung: Fakten + Zahlen + Zweitpruefer + Story.
        nachbessern.faktencheck(s)
        gruende = skript_gruende(s)
        if s.get('pruefung', {}).get('probleme'):
            gruende.append('Offene Faktenbefunde')
        bericht.update(pruefung=s.get('pruefung'), zweitpruefung=s.get('zweitpruefung'),
                        story=s.get('story'), gruende=gruende, freigabe=not gruende,
                        status='freigegeben' if not gruende else 'gesperrt')
    except (ValueError, RuntimeError, OSError) as e:
        from autorenvergleich import fehlertext
        bericht.update(status='gesperrt', gruende=[fehlertext(e)], pruefung=s.get('pruefung'),
                        zweitpruefung=s.get('zweitpruefung'), story=s.get('story'))
    finally:
        skript.gemini = original
    if modus == 'vorrat' and bericht['freigabe']:
        # Der normale Vorratsfilter muss das tatsaechliche Ergebnis ebenfalls akzeptieren.
        eintrag = {'thema_eingabe': p['thema'], 'erstellt_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                   'prompts': prompts.VERSION, 'modell': s['modell'], 'story_note': s['story']['note'], 'skript': s}
        if not vorrat.gueltig(eintrag, profil) or (not lang and vorrat.wiederholung(p['kanal'], eintrag)):
            bericht.update(freigabe=False, status='gesperrt', gruende=['Normaler Vorratsfilter lehnt das Skript ab'])
        else:
            ziel = Path('vorrat') / p['kanal'] / f'codex-{kennung}.json'
            if ziel.exists():
                raise ValueError('Derselbe Auftrag wurde bereits uebergeben')
            liste = themen.laden()
            # Langvideos laufen mit festem Thema aus langvideo.py, nicht ueber die Short-Warteschlange.
            if not lang and not any(x.get('kanal') == p['kanal'] and x.get('thema') == p['thema'] for x in liste):
                liste.append({'kanal': p['kanal'], 'thema': p['thema'], 'id': 'codex-' + kennung,
                              'eingang': dt.date.today().isoformat()})
                themen.speichern(liste)
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(json.dumps(eintrag, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
            bericht['vorrat_geschrieben'] = True
    return bericht


GELESEN = {}


def fehlerbericht(kennung, e):
    """Abgelehnter Auftrag: Grund als Ergebnis statt nur Exitcode (04.11.2026, Lauf 41892146837 meldete
    nur „nicht abgeschlossen"). Eigene Pruefmeldungen (ValueError) im Klartext, sonst nur der Fehlertyp -
    keine fremden Inhalte oder Zugangsdaten im Artefakt."""
    grund = str(e)[:200] if type(e) is ValueError else type(e).__name__
    ziel = Path('ausgabe/codex-pruefung/ergebnis.json')
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps({'id': kennung, 'entwurf_sha': GELESEN.get('entwurf_sha'), 'status': 'abgelehnt',
                                'freigabe': False, 'vorrat_geschrieben': False, 'gruende': [grund]},
                               ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    kennung = os.environ.get('CF_CODEX_ID', '')
    modus = os.environ.get('CF_CODEX_MODUS', 'pruefen')
    roh = os.environ.pop('CF_CODEX_PAKET', '')
    if len(roh.encode()) > 47_000:
        raise ValueError('Brueckenauftrag zu gross')
    os.environ['CF_RESERVE_AUS'] = '1'
    os.environ['CF_TEXT_FALLBACK'] = 'groq'
    p = paket_lesen(roh)
    GELESEN['entwurf_sha'] = sha(p.get('entwurf')) if isinstance(p, dict) else None
    paket_pruefen(p, kennung)
    frist = PRUEF_S[videoformat(p)]
    os.environ['CF_SCHRITT_ENDE'] = str(time.monotonic() + frist)
    reservierung = None
    if modus == 'vorrat':
        import budget
        from lauf import BUDGET_S, BUDGET_LANG_S, tagesgrenze
        # Diese automatische Bruecke eroeffnet keine zusaetzlichen manuellen Zeitfenster.
        os.environ['CF_HANDSTART'] = ''
        # Langvideos haben ein eigenes Tagesbudget (lauf.py: lang-<kanal>), Shorts bleiben unberuehrt.
        topf = ('lang-' if videoformat(p) == 'lang' else '') + p['kanal']
        grenze = tagesgrenze(topf, BUDGET_LANG_S if videoformat(p) == 'lang' else BUDGET_S)
        if budget.rest(topf, grenze) - p.get('autor_s', 0) < 90:
            raise ValueError('Kein normales Tagesbudget fuer die Fallback-Pruefung frei')
        reservierung = budget.reservieren(topf, grenze)
        os.environ['CF_SCHRITT_ENDE'] = str(time.monotonic() + min(frist, reservierung[0] - p.get('autor_s', 0) - 30))
    start = time.monotonic()
    try:
        bericht = bewerten(p, kennung, modus)
    finally:
        if reservierung:
            budget.abschliessen(topf, reservierung, time.monotonic() - start
                                + min(AUTOR_MAX_S[videoformat(p)], max(0, p.get('autor_s', 0))))
    ziel = Path('ausgabe/codex-pruefung/ergebnis.json')
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(bericht, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Unabhaengige Codex-Skriptpruefung:', bericht['status'])


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        try:
            fehlerbericht(os.environ.get('CF_CODEX_ID', ''), e)
        except OSError:
            pass
        print('Brueckenauftrag nicht abgeschlossen; keine Freigabe', file=sys.stderr)
        sys.exit(2)
