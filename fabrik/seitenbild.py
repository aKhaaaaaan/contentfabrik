"""Echter Screenshot der offiziellen Quellseite zum gesprochenen Satz (Nutzer 21.10.2026).

„Bei KI muessen die Bilder nicht immer gemalt sein, nur wenn keine echten Screenshots vorhanden sind." /
„Koennen wir die Screenshots von YouTube-Videos nehmen?" - nein (fremdes Material, Content ID, YouTube-AGB).
Stattdessen: Die Quellseite, aus der der Satz stammt (z. B. support.google.com/gemini/answer/14286560), wird in
einem unsichtbaren Browser (Playwright, Apache 2.0, schon installiert) in Handy-Breite geoeffnet; der Absatz, der
die meisten Woerter des Satzes enthaelt, wird gelb markiert und fotografiert. Kanalneutral: gilt fuer jede
Quellseite mit Text (Doku, Hilfe, Pressemitteilung), GitHub/Hugging Face behalten ihre Beispielbilder.

Ohne sicheren Treffer (zu wenige gemeinsame Woerter) kein Bild - dann wie bisher die Erklaergrafik.
"""
import hashlib
import re
from pathlib import Path

# Handy-Breite: im 960 px breiten Fotokasten (bauen.LAYOUT['foto']) wird die Seitenschrift ~2,2x so gross -
# GEMESSEN 04.10.2026 (aufnahme_fuer): 1280 px Desktop-Seiten waren auf dem Handy unlesbar.
BREITE, HOEHE = 430, 528  # CSS-Pixel; 960x1180 Kasten -> gleiches Seitenverhaeltnis
MARKE_OBEN = 0.30  # markierter Absatz im oberen Drittel: der Pruefer sieht nur Bild-y ~16-65 %

FUELL = set('''a an and are as at be but by can do does for from has have how if in into is it its just more
most not of on or so than that the then their there these this to too was what when which who why will with you
your yes no now only also very really get got want need like make made use using used one two three'''.split())


def woerter(text):
    """Bedeutungstragende Woerter eines Satzes (klein, ohne Fuellwoerter); Zahlen wie 2K bleiben."""
    roh = re.findall(r"[a-z0-9][a-z0-9'+.-]*", (text or '').lower())
    return {w.strip(".'-") for w in roh if (len(w) >= 4 or re.search(r'\d', w)) and w not in FUELL}


def bester_abschnitt(satz, bloecke, benutzt=(), visuell=(), namen=''):
    """Index des Absatzes, der am besten zum Satz passt, oder None.

    bloecke: Liste von Texten (sichtbare Absaetze der Seite). Sicherer Treffer: mindestens 2 gemeinsame Woerter
    und mindestens 40 % der Satzwoerter (oder 4 gemeinsame). Gemeinsame Zahlen zaehlen doppelt; Tabellen,
    Grafiken und Code (Indizes in visuell) gewinnen bei gleichem Treffer. Bei Gleichstand der kuerzere Absatz.
    GEMESSEN 22.10.2026 (KI-Lauf 39757744191): 4 von 10 Screenshots „zeigen lediglich einen Text"; Einstellung 11
    traf mit einem Drittel der Woerter einen Absatz zu einem anderen Punkt."""
    # GEMESSEN 29.10.2026 (KI 40917784096): "A connected server lets Claude read that system" traf eine Tabelle
    # "How Claude Code handles it" (2/10) - "claude" steht in jedem Absatz der Claude-Doku. Produktnamen zaehlen
    # nicht als Treffer; der Anteil bleibt an allen Satzwoertern gemessen (sonst reichten 2 von 5 statt 2 von 6).
    satzwoerter = woerter(satz)
    ziel = satzwoerter - woerter(namen)
    if len(ziel) < 2:
        return None
    zahlen = {w for w in ziel if re.search(r'\d', w)}
    beste, wert = None, None
    for i, text in enumerate(bloecke):
        if i in benutzt or not 20 <= len(text) <= (2000 if i in visuell else 700):
            continue
        da = woerter(text)
        # Treffer muessen beieinander stehen (eine Zeile oder zwei Nachbarsaetze): die 1.486-Zeichen-Tabelle hatte
        # "connected", "server", "read" in drei verschiedenen Zeilen (KI 40917784096).
        teile = [x for x in re.split(r'\n+|(?<=[.!?])\s+', text) if x.strip()] or [text]
        gemeinsam = max(len(ziel & woerter(' '.join(teile[k:k + 2]))) for k in range(len(teile)))
        if gemeinsam < 2 or (gemeinsam / len(satzwoerter) < 0.4 and gemeinsam < 4):
            continue
        w = (gemeinsam + len(zahlen & da) + (1 if i in visuell else 0), -len(text))
        if wert is None or w > wert:
            beste, wert = i, w
    return beste


def ausschnitt_oben(block, visuelle, seitenhoehe, hoehe=HOEHE):
    """Oberkante des Bildausschnitts. Eine Tabelle/Grafik direkt unter dem markierten Absatz kommt mit ins Bild
    (Absatz oben, Tabelle darunter), sonst der Absatz im oberen Drittel."""
    oben = block['y'] - hoehe * MARKE_OBEN
    if block.get('visuell'):
        oben = block['y'] - 24
    else:
        ende = block['y'] + block['h']
        for v in sorted(visuelle, key=lambda v: v['y']):
            if 0 <= v['y'] - ende <= 260 and v['y'] + min(v['h'], hoehe * 0.6) - (block['y'] - 24) <= hoehe:
                oben = block['y'] - 24
                break
    return max(0, min(oben, seitenhoehe - hoehe))


# GEMESSEN 23.10.2026 (KI-Lauf 39924320241): platform.openai.com scrollt in <body>, nicht im Dokument -
# documentElement.scrollHeight blieb 900 px, jeder Ausschnitt wurde auf dieselbe Stelle begrenzt und sechs
# Screenshots waren bytegleich -> "Gleiches Motiv zu lange gehalten", vier Bauversuche ohne Video.
# Den groessten inneren Scrollbereich samt Vorfahren ausklappen, dann ist die Seite wieder so hoch wie ihr Inhalt.
ENTROLLEN = """() => {
  const doc = document.documentElement;
  let el = null, h = doc.scrollHeight;
  for (const e of document.querySelectorAll('*')) {
    const s = getComputedStyle(e);
    if ((s.overflowY === 'auto' || s.overflowY === 'scroll') && e.scrollHeight > e.clientHeight + 50
        && e.scrollHeight > h) { el = e; h = e.scrollHeight; }
  }
  if (!el) return 0;
  for (let x = el; x; x = x.parentElement) {
    x.style.setProperty('height', 'auto', 'important');
    x.style.setProperty('max-height', 'none', 'important');
    x.style.setProperty('overflow', 'visible', 'important');
  }
  return doc.scrollHeight;
}"""

# 25.10.2026 (KI-Short "Claude Code + Your TV", Nutzer: "ja mach das" zu echten Tool-Ansichten): 6 von 8
# beanstandeten Bildern waren Textgrafiken, weil die Quellseite keinen passenden ABSATZ hatte - ihre Bilder
# (Produkt-Screenshots, Diagramme) wurden nie betrachtet. Jetzt ist jedes grosse <img> ein Kandidat; sein Text
# ist Alt-Text + die Ueberschrift darueber. Jeder Kandidat bekommt eine Nummer (data-cf), MARKIEREN findet ihn darueber.
SAMMELN = """() => {
  const ZIELE = 'p, li, h1, h2, h3, h4, td, dd, blockquote, figcaption, div, table, figure, pre, img';
  const aus = [];
  let ueberschrift = '';
  for (const el of document.querySelectorAll(ZIELE)) {
    const tag = el.tagName;
    if (/^H[1-4]$/.test(tag)) ueberschrift = (el.innerText || '').trim().slice(0, 160);
    const bild = tag === 'IMG';
    const visuell = bild || tag === 'TABLE' || tag === 'FIGURE' || tag === 'PRE';
    // div nur als unterste Textebene (GEMESSEN 21.10.: Googles "Important: If you reach your daily quota..." ist ein div)
    if (tag === 'DIV' && el.querySelector('p, li, div, h1, h2, h3, h4, table, ul, ol, section')) continue;
    // Zellen einer Tabelle: die Tabelle als Ganzes ist der bessere Kandidat
    if (tag === 'TD' && el.closest('table')) continue;
    if (bild && el.closest('figure')) continue;  // die Figur samt Bildunterschrift ist der Kandidat
    const r = el.getBoundingClientRect();
    const img = tag === 'FIGURE' ? el.querySelector('img') : null;
    const t = (bild ? ((el.alt || '') + ' ' + ueberschrift)
               : (el.innerText || '') + (img && img.alt ? ' ' + img.alt : '')).trim();
    if (!t || r.width < (bild ? 200 : 120) || r.height < (bild ? 120 : 12)) continue;
    if (visuell && r.height < 60) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none') continue;
    if (el.closest('nav, header, footer, aside, [role=navigation], [aria-hidden=true]')) continue;
    el.setAttribute('data-cf', String(aus.length));
    aus.push({t: t.slice(0, visuell ? 2000 : 800), y: r.top + window.scrollY, h: r.height, visuell, bild});
  }
  return aus;
}"""

MARKIEREN = """([n, woerter]) => {
  const el = document.querySelector('[data-cf="' + n + '"]');
  if (!el) return;
  const rahmen = (x) => { x.style.outline = '4px solid #f5b400'; x.style.outlineOffset = '4px';
                          x.style.borderRadius = '6px'; };
  if (el.tagName === 'IMG') { rahmen(el); return; }  // Bild nur umrahmen, nicht gelb einfaerben
  const tab = el.tagName === 'TABLE' ? el : el.querySelector('table');
  if (tab) {
    // Rahmen um die Tabelle, gelb nur die Zeile mit den meisten Woertern des Satzes
    rahmen(el);
    let beste = null, wert = 0;
    for (const tr of tab.querySelectorAll('tr')) {
      const x = (tr.innerText || '').toLowerCase();
      const k = woerter.filter(w => x.includes(w)).length;
      if (k > wert) { beste = tr; wert = k; }
    }
    if (beste) for (const c of beste.querySelectorAll('td, th')) c.style.background = '#fff3a8';
  } else {
    el.style.background = '#fff3a8';
    rahmen(el);
  }
}"""


def aufnehmen(url, satz, ziel, benutzt=None, namen=''):
    """(pfad, quelle) oder (None, None). benutzt: Menge schon gezeigter Absatz-Kennungen (url#index)."""
    if not re.match(r'https?://', url or '') or re.match(r'https?://(github\.com|huggingface\.co)/', url):
        return None, None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None, None
    benutzt = benutzt if benutzt is not None else set()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                kontext = browser.new_context(viewport={'width': BREITE, 'height': 900}, device_scale_factor=2,
                                              is_mobile=True, has_touch=True, color_scheme='light', locale='en-US')
                seite = kontext.new_page()
                seite.goto(url, wait_until='domcontentloaded', timeout=30000)
                seite.wait_for_timeout(1500)
                # Datenschutzfreundlich: nur „ablehnen" anklicken, nie „alle akzeptieren".
                for name in ('Reject all', 'Alle ablehnen', 'Decline', 'Reject'):
                    knopf = seite.get_by_role('button', name=name)
                    if knopf.count():
                        try:
                            knopf.first.click(timeout=2000)
                            seite.wait_for_timeout(800)
                        except Exception:
                            pass
                        break
                if seite.evaluate(ENTROLLEN):
                    seite.wait_for_timeout(300)
                bloecke = seite.evaluate(SAMMELN)
                schon = {int(k.split('#')[-1]) for k in benutzt if k.startswith(url + '#')}
                visuell = {n for n, x in enumerate(bloecke) if x.get('visuell')}
                i = bester_abschnitt(satz, [b['t'] for b in bloecke], schon, visuell, namen)
                if i is None:
                    return None, None
                b = bloecke[i]
                seite.evaluate(MARKIEREN, [i, sorted(woerter(satz))])
                hoehe = seite.evaluate('() => document.documentElement.scrollHeight')
                oben = ausschnitt_oben(b, [x for x in bloecke if x.get('visuell')], hoehe)
                Path(ziel).parent.mkdir(parents=True, exist_ok=True)
                seite.screenshot(path=str(ziel), clip={'x': 0, 'y': oben, 'width': BREITE, 'height': HOEHE},
                                 full_page=True, type='jpeg', quality=90)
            finally:
                browser.close()
        if not Path(ziel).is_file() or Path(ziel).stat().st_size < 15000:
            return None, None
        kennung = f'{url}#{i}'
        benutzt.add(kennung)
        return Path(ziel), {'quelle': 'Screenshot der Quellseite', 'seite': url, 'datei': kennung,
                            'abschnitt': b['t'][:200], 'visuell': bool(b.get('visuell')), 'bild': bool(b.get('bild')),
                            'sha256': hashlib.sha256(Path(ziel).read_bytes()).hexdigest()}
    except Exception as e:
        print('Quellseiten-Screenshot nicht moeglich:', url, str(e)[:150])
        return None, None
