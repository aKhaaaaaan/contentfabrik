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


def upload_titel(skript, datum=None):
    """Gemeinsamer Upload-Titel fuer Telegram, Berichte und Plattformen."""
    import datetime
    from zoneinfo import ZoneInfo
    from dramaturgie import videoformat
    import kanalstandard
    titel = titel_text(skript['titel'])
    if videoformat(skript) == 'lang':
        return titel
    profil = kanalstandard.nach_name(skript.get('kanal')) or {}
    datum = datum or datetime.datetime.now(ZoneInfo('Europe/Berlin')).date()
    return serien_titel(titel, profil.get('serie'), datum)


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


def tiktok_hashtags(skript):
    """Bis zu fuenf belegte Tags: konkretes Thema vor zwei Kanal-Kategorien.

    Keine Trendbehauptung oder neue KI-Anfrage. Zusammengesetzte Tags muessen aus
    benachbarten Woertern stammen; #cat passt nicht allein wegen 'application'.
    """
    inhalt = ' '.join([str(skript.get('thema', '')), titel_text(skript.get('titel', [])),
                      *[str(t.get('text', '')) for t in skript.get('teile', [])]])
    woerter = re.findall(r'[a-z0-9]+', inhalt.lower())
    belegt = {''.join(woerter[i:i + n]) for i in range(len(woerter)) for n in range(1, 5)}
    belegt |= {w[:-1] for w in woerter if len(w) > 4 and w.endswith('s')}
    kategorien = {'AI Tools Explained': ['AITools', 'AI'],
                  'Business Origin Stories': ['BusinessHistory', 'Business']}.get(skript.get('kanal'), [])
    allgemein = {t.lower() for t in kategorien}
    # Keine generischen Reichweiten-Tags oder Zugangs-/Lizenzbehauptungen aus Worttreffern.
    ausgeschlossen = {'fyp', 'foryou', 'foryoupage', 'viral', 'trending', 'short', 'shorts', 'freeai', 'opensource'}
    aus, gesehen = [], set()
    werkzeuge = {re.sub(r'[^a-z0-9]', '', str(w).lower()) for w in
                 [skript.get('thema', ''), *[t.get('werkzeug', '') for t in skript.get('teile', [])]]}
    for tag in skript.get('hashtags', []) or []:
        sauber = re.sub(r'[^a-zA-Z0-9_]', '', str(tag).lstrip('#'))
        kern = sauber.replace('_', '').lower()
        if kern and kern not in allgemein | ausgeschlossen and kern in belegt and kern not in gesehen:
            aus.append(sauber)
            gesehen.add(kern)
    aus.sort(key=lambda tag: tag.replace('_', '').lower() not in werkzeuge)
    return (aus[:5 - len(kategorien)] + kategorien)[:5]


def kapitelmarken(skript, abschnitte_s):
    """YouTube-Kapitel fuer Langvideos aus den Kapitelnamen des Skripts und den GEMESSENEN Abschnittslaengen.

    16.10.2026 (Nutzerauftrag woechentliches Langvideo): Kapitel halten Zuschauer und erscheinen in der Suche
    als eigene Treffer. YouTube erkennt sie nur mit erster Marke 0:00, mindestens 3 Kapiteln und je mindestens
    10 s (support.google.com/youtube/answer/9884579). Sonst lieber gar keine Liste als eine kaputte."""
    teile = skript.get('teile') or []
    if len(abschnitte_s) != len(teile):
        return ''
    marken, t = [], 0.0
    for teil, dauer in zip(teile, abschnitte_s):
        name = str(teil.get('name') or '').strip()
        if not marken:
            marken.append([0.0, name or 'Intro'])
        elif name and name != marken[-1][1]:
            marken.append([t, name])
        t += dauer
    # Zu kurze Kapitel dem vorherigen zuschlagen (YouTube verwirft sonst ALLE Marken)
    gut = [marken[0]]
    for start, name in marken[1:]:
        if start - gut[-1][0] >= 10:
            gut.append([start, name])
    if len(gut) > 1 and t - gut[-1][0] < 10:
        gut.pop()
    if len(gut) < 3:
        return ''
    return '\n'.join(f'{int(s) // 60}:{int(s) % 60:02d} {n[:60]}' for s, n in gut)


# Nutzerentscheidung 17.10.2026: Kommentarfrage am Ende. TikTok gewichtet starke Signale hoeher
# (newsroom.tiktok.com, "How TikTok recommends videos"); ein festes Punktesystem ist nicht belegt.
# Die Antworten sind zugleich Themenwuensche. Nur sichtbar/Beschreibung, nicht gesprochen:
# der gesprochene Aufruf (like, share, save) und seine Endton-Pruefung bleiben unveraendert.
KOMMENTARFRAGE = {
    'Business Origin Stories': ('Which company next? Comment below!',
                                'Which company should we cover next? Tell us in the comments.'),
    'AI Tools Explained': ('Which AI tool next? Comment below!',
                           'Which AI tool should we explain next? Tell us in the comments.'),
}


def kommentar_frage(skript, kurz=False):
    """Kommentarfrage des Kanals ('' fuer Kanaele ohne Frage); kurz=True fuer das Schlussbild."""
    paar = KOMMENTARFRAGE.get(str(skript.get('kanal') or ''))
    return (paar[0] if kurz else paar[1]) if paar else ''


def mit_kommentar_frage(beschreibung, skript):
    """Frage hinter den Inhalt, vor Quellen-/Lizenzzeilen; nie doppelt."""
    frage = kommentar_frage(skript)
    if not frage or frage in beschreibung:
        return beschreibung
    zeilen = beschreibung.splitlines()
    beginn = next((i for i, z in enumerate(zeilen) if z.strip().lower().startswith(
        ('source:', 'sources:', 'quelle', 'music:', 'photos', 'clips:', 'illustrations are'))), len(zeilen))
    return '\n'.join(zeilen[:beginn] + [frage] + zeilen[beginn:])


def beschreibung_mit_quellen(beschreibung, quellen):
    """Gemeinsame vollstaendige Musik-/Foto-Nennung fuer alle Upload-Texte."""
    nennungen = []
    fotos = [q for q in quellen if q.get('quelle') == 'Wikimedia Commons']
    musik = [q for q in quellen if q.get('quelle') == 'Musik']
    if any(q.get('quelle') == 'Pixabay' for q in quellen):
        nennungen.append('Clips: Pixabay')
    if musik:
        nennungen.append(musik[0]['nennung'])
    if any(q.get('quelle') == 'Illustration' for q in quellen):
        nennungen.append('Illustrations are AI-generated.')
    if fotos:
        nennungen.append('Photos (Wikimedia Commons): ' + '; '.join(
            f"{q['von']}, {q['lizenz']} ({q['seite']})" for q in fotos)
            + ' - cropped, animated and captioned' + (
                '; these modified photos are licensed under the same CC BY-SA license'
                if any('SA' in q['lizenz'] for q in fotos) else ''))
    for nennung in nennungen:
        if nennung not in beschreibung:
            beschreibung += '\n' + nennung
    return beschreibung


def tiktok_text(skript, datum=None, quellen=()):
    """Titel, kurzer Inhalt, belegte Hashtags und vollstaendige Quellenangaben.

    Video-Inbox unterstuetzt KEINE Caption; dieser Text ist fuer Telegram und
    einen kuenftigen freigeschalteten Direct-Post-Weg. Lizenztexte niemals abschneiden.
    """
    zeilen = beschreibung_mit_quellen(str(skript.get('beschreibung', '')), quellen).splitlines()
    beginn = next((i for i, z in enumerate(zeilen) if z.strip().lower().startswith(
        ('source:', 'sources:', 'music:', 'photos', 'clips:', 'illustrations are'))), len(zeilen))
    frage = kommentar_frage(skript)
    beschreibung = ' '.join(' '.join(z for z in zeilen[:beginn] if z.strip() != frage).split())
    if len(beschreibung) > 280:
        saetze = re.split(r'(?<=[.!?])\s+(?=[A-Z])', beschreibung)
        beschreibung = saetze[0] if len(saetze[0]) <= 280 else beschreibung[:277].rsplit(' ', 1)[0] + '...'
    tags = ' '.join('#' + tag for tag in tiktok_hashtags(skript))
    nennungen = '\n'.join(zeilen[beginn:]).strip()
    return '\n\n'.join(t for t in (upload_titel(skript, datum), beschreibung, frage, tags, nennungen) if t)


def tiktok_laenge(text):
    """TikTok zaehlt Caption-Zeichen als UTF-16-Einheiten (Emoji oft zwei)."""
    return len(text.encode('utf-16-le')) // 2
