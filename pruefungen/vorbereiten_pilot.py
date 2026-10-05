"""Redaktionelle Vorlage aus dem gespeicherten Beleg; keine erfundene Freigabe."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
alt = json.loads((root / 'ausgabe/github/11348639222/ausgabe/skript.json').read_text(encoding='utf-8'))
texte = [
    'Nintendo once had a problem: its cards lasted.',
    'Long before video games, Nintendo made handmade flower cards in Kyoto. Craftsman Fusajiro Yamauchi started that business in 1889. But a sturdy deck wasn\'t always good for business.',
    'Making the cards was slow and expensive. Their price was high, and their durability meant customers rarely needed replacements. Those problems left the young business struggling.',
    'So what did Nintendo change? It offered Tengu: a cheaper, lower-quality line of playing cards. That response went in the opposite direction: a lower-quality product, at a lower price.',
    'Nintendo also sold cards in other cities, including Osaka. Local merchants wanted fresh decks to avoid the suspicions that reusing cards could create. Renewal had a reason beyond wear.',
    'Decades later, Nintendo changed its audience. A 1959 partnership with Walt Disney Productions put characters onto playing cards. That opened the children\'s market and boosted the card business.',
    'The surprise isn\'t just that Nintendo started with cards. Its early challenges involved changing the product, its price and its audience. Video games came much later.',
    'Be sure to like, share and save this video.',
]
bilder = [
    ('illustration', 'durable flower cards', 'The original fictional channel presenter inspecting a small stack of unlettered floral playing cards on a wooden desk, with a crisp edge and worn tabletop. Medium close shot, warm cinematic side light, original painted urban game-poster aesthetic, no historical-person likeness.'),
    ('foto', 'Kyoto old card shop', 'A genuine archival photograph of Nintendo\'s early Kyoto storefront; show the whole building.'),
    ('illustration', 'handmade card workshop', 'An illustrative close shot of anonymous hands arranging floral paper cards beside simple period-appropriate handcraft tools on a wooden bench. Warm window light, strong painted contours, no identifiable real person, lettering or logos.'),
    ('illustration', 'two card decks', 'Two generic floral card decks side by side on a wooden shop counter: one with thick paper, one with thinner plain paper. A clear overhead comparison, painted shading, original editorial illustration, no prices, text, logos or fabricated historical packaging.'),
    ('foto', 'antique Japanese cards', 'A genuine early Nintendo playing-card poster or card photograph; show the original in full as a historical card-business illustration, not as evidence of a named merchant transaction.'),
    ('illustration', 'family playing cards', 'A generic mid-century family sitting around a table with unlettered playing cards showing original geometric floral motifs. Warm afternoon light and painted contours. No Disney characters, copyrighted mascots, logos or claim to recreate a specific historical family.'),
    ('foto', 'Nintendo modern console', 'A genuine product photograph of a Nintendo console, shown in full, illustrating the later video-game business rather than a historical founder event.'),
    ('illustration', 'presenter playing cards', 'The same original fictional channel presenter beside a wooden table with generic floral cards, relaxed confident posture, medium shot, warm cinematic light, original painted urban poster aesthetic, no logos, copied game characters or written text.'),
]
beats = ['hook', 'frage', 'beleg', 'wendung', 'beleg', 'wendung', 'aufloesung', 'aufloesung']
teile = [{'text': t, 'bildmodus': b[0], 'suche': b[1], 'szene': b[2], 'beat': beat}
         for t, b, beat in zip(texte, bilder, beats)]
teile[3]['bildtext'] = 'lower-quality line'
datei = {k: alt[k] for k in ('kanal', 'stimme', 'tempo', 'titel_farbe', 'untertitel_profil',
                              'posten_ny', 'laenge_s', 'videoformat', 'belege', 'bilder', 'quellen')}
datei.update(thema='Nintendo: The Problem with Durable Cards', titel=['Cards That Lasted', "Nintendo's Early Puzzle"],
             teile=teile, format='geschichte', musik=True,
             musik_suche=['curious documentary instrumental', 'warm subtle piano pulse'],
             hintergrund_suche='dark warm background', hashtags=['Nintendo', 'BusinessHistory', 'OriginStory'],
             beschreibung='Nintendo began with handmade playing cards in Kyoto. Its early challenges involved product cost, durability and changing markets.',
             herkunft='Redaktionelle Pilotvorlage aus gespeichertem Quelltext; noch nicht freigegeben.')
ziel = root / 'piloten/nintendo-karten.json'
ziel.parent.mkdir(exist_ok=True)
ziel.write_text(json.dumps(datei, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('Vorlage:', ziel.name, '| Gesprochene Woerter:', sum(len(t.split()) for t in texte))
