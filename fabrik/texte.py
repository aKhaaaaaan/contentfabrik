"""Gemeinsame Regeln fuer sichtbare Upload-Texte (Titel, Hashtags) - eine Quelle fuer alle Plattformen."""
import re

# Allgemeine Kategorie-Tags duerfen ohne Textbeleg stehen; alles andere muss im Video vorkommen.
ALLGEMEIN = {'shorts', 'short', 'ai', 'aitools', 'aitoolsexplained', 'freeai', 'aimodels', 'opensource',
             'business', 'businesshistory', 'originstory', 'story', 'history', 'startup', 'entrepreneur',
             'tech', 'technology', 'brand', 'brands', 'company', 'companies'}


def titel_text(zeilen):
    """Zwei Titelzeilen lesbar verbinden. GEMESSEN 10.10.2026 (YouTube): „From DVDs to Streaming The
    Netflix Qwikster Detour" - ohne Trennzeichen wirkte der Titel wie ein Satz ohne Punkt und Komma."""
    teile = [str(z).replace('*', '').strip() for z in zeilen if str(z).replace('*', '').strip()]
    if len(teile) < 2:
        return teile[0] if teile else ''
    erste, rest = teile[0], ' '.join(teile[1:])
    return f'{erste} {rest}' if re.search(r'[:?!.,–-]$', erste) else f'{erste}: {rest}'


def serien_titel(titel, serie, datum, grenze=92):
    """„<Titel> | AI Tool #N" - N = Tag seit Serienstart (Nutzerauftrag 10.10.2026: Serie mit Nummer
    bindet Zuschauer, Mitte des Funnels). Nach Datum statt Zaehler: Pilotlaeufe schreiben keinen
    Stand ins Repo zurueck - ein Zaehler vergaebe dort doppelte Nummern. Ausfalltage = Luecke,
    nie eine Doppelung. Ohne gueltige Serie oder vor dem Start: Titel unveraendert."""
    import datetime
    try:
        start = datetime.date.fromisoformat(str((serie or {}).get('start', '')))
        name = str(serie['name']).strip()
    except (ValueError, KeyError, TypeError):
        return titel
    nummer = (datum - start).days + 1
    if not name or nummer < 1:
        return titel
    zusatz = f' | {name} #{nummer}'
    # grenze 92: YouTube erlaubt 100 Zeichen, freigabe.py haengt bei Shorts noch ' #shorts' an
    return (titel[:grenze - len(zusatz)].rstrip() + zusatz) if titel else zusatz.strip(' |')


def hashtags_bereinigen(tags, inhalt):
    """Nur Hashtags, die im Video vorkommen oder allgemeine Kategorien sind.
    GEMESSEN 10.10.2026: #gta unter dem Whirl-Video - die KI uebernahm den Stilhinweis aus dem
    Nutzerfeedback; ein Hashtag ohne Bezug zum Inhalt kann als irrefuehrend gelten."""
    roh = re.sub(r'[^a-z0-9]', '', str(inhalt).lower())
    aus = []
    for t in tags or []:
        kern = re.sub(r'[^a-z0-9]', '', str(t).lower())
        if kern and (kern in ALLGEMEIN or kern in roh) and kern not in [re.sub(r'[^a-z0-9]', '', a.lower()) for a in aus]:
            aus.append(str(t).lstrip('#'))
    return aus
