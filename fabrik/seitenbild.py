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


def bester_abschnitt(satz, bloecke, benutzt=()):
    """Index des Absatzes, der am besten zum Satz passt, oder None.

    bloecke: Liste von Texten (sichtbare Absaetze der Seite). Sicherer Treffer: mindestens 2 gemeinsame Woerter
    und mindestens ein Drittel der Satzwoerter. Bei Gleichstand gewinnt der kuerzere (genauere) Absatz."""
    ziel = woerter(satz)
    if len(ziel) < 2:
        return None
    beste, wert = None, None
    for i, text in enumerate(bloecke):
        if i in benutzt or not 20 <= len(text) <= 700:
            continue
        gemeinsam = len(ziel & woerter(text))
        if gemeinsam < 2 or gemeinsam / len(ziel) < 1 / 3:
            continue
        w = (gemeinsam, -len(text))
        if wert is None or w > wert:
            beste, wert = i, w
    return beste


SAMMELN = """() => {
  const ZIELE = 'p, li, h1, h2, h3, h4, td, dd, blockquote, figcaption, div';
  const aus = [];
  for (const el of document.querySelectorAll(ZIELE)) {
    // div nur als unterste Textebene (GEMESSEN 21.10.: Googles "Important: If you reach your daily quota..." ist ein div)
    if (el.tagName === 'DIV' && el.querySelector('p, li, div, h1, h2, h3, h4, table, ul, ol, section')) continue;
    const r = el.getBoundingClientRect();
    const t = (el.innerText || '').trim();
    if (!t || r.width < 120 || r.height < 12) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none') continue;
    if (el.closest('nav, header, footer, aside, [role=navigation], [aria-hidden=true]')) continue;
    aus.push({t: t.slice(0, 800), y: r.top + window.scrollY, h: r.height});
  }
  return aus;
}"""


def aufnehmen(url, satz, ziel, benutzt=None):
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
                bloecke = seite.evaluate(SAMMELN)
                schon = {int(k.split('#')[-1]) for k in benutzt if k.startswith(url + '#')}
                i = bester_abschnitt(satz, [b['t'] for b in bloecke], schon)
                if i is None:
                    return None, None
                b = bloecke[i]
                seite.evaluate("""([y, t]) => {
                  const ZIELE = 'p, li, h1, h2, h3, h4, td, dd, blockquote, figcaption, div';
                  for (const el of document.querySelectorAll(ZIELE)) {
                    const r = el.getBoundingClientRect();
                    if (Math.abs(r.top + window.scrollY - y) < 2 && (el.innerText || '').trim().slice(0, 800) === t) {
                      el.style.background = '#fff3a8'; el.style.outline = '4px solid #f5b400';
                      el.style.outlineOffset = '4px'; el.style.borderRadius = '6px'; break;
                    }
                  }
                }""", [b['y'], b['t']])
                hoehe = seite.evaluate('() => document.documentElement.scrollHeight')
                oben = max(0, min(b['y'] - HOEHE * MARKE_OBEN, hoehe - HOEHE))
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
                            'abschnitt': b['t'][:200],
                            'sha256': hashlib.sha256(Path(ziel).read_bytes()).hexdigest()}
    except Exception as e:
        print('Quellseiten-Screenshot nicht moeglich:', url, str(e)[:150])
        return None, None
