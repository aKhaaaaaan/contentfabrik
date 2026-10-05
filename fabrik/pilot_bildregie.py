"""Quellengetreue, sichtkontrollierte Regie fuer die zwei redaktionellen Piloten."""


def asset(kennung, motiv):
    return {'bildmodus': 'asset', 'asset': kennung, 'motiv': motiv,
            'szene': motiv, 'suche': 'original editorial illustration'}


def figur():
    return {'bildmodus': 'figur', 'motiv': 'Original channel presenter for the spoken CTA',
            'szene': 'Original fictional channel presenter, not a real historical person', 'suche': 'original presenter'}


def grafik(n):
    beschreibungen = ['Compare durable and lower-quality paper decks', 'Identify the cheaper Tengu card line',
                     'A lower-price response, qualitative arrow with no invented price',
                     'A thin deck and a price marker: lower quality and lower price']
    return {'bildmodus': 'grafik', 'grafik_variante': n, 'szene': beschreibungen[n],
            'motiv': beschreibungen[n], 'suche': 'qualitative sourced card comparison'}


def setzen(s):
    if s['kanal'] == 'AI Tools Explained':
        def a(kennung):
            besch = {'ai-presenter-workflow': 'Original presenter examining cutouts and visual reference objects',
                     'ai-workflow-objects': 'Three creative workflow objects on a workbench: cutout, local annotation and portraits',
                     'ai-layers': 'Flower cutout on physically separate transparent layers',
                     'ai-local-edit': 'A painted flower with a selection ring and a separate paper mask',
                     'ai-reference-wall': 'Six original portrait frames above a blank canvas; conceptual reference workflow',
                     'ai-license-check': 'Original presenter examining a blank folder before choosing a creative tool'}
            return asset(kennung, besch[kennung])
        def demo(n, besch):
            return {'bildmodus': 'demo', 'demo_url': 'https://qianwen-res.oss-accelerate.aliyuncs.com/Qwen-Image/image2.1/images/example-' + n + '.png',
                    'motiv': besch, 'szene': besch, 'suche': 'actual documented model example'}
        d05 = demo('05', 'Actual floral portrait output published in the model card')
        d04 = demo('04', 'Actual transparent dragon sticker published in the model card')
        d06 = demo('06', 'Actual transparent office character published in the model card')
        d15 = demo('15', 'Actual published composite of six reference portraits and a group image')
        karte = {'bildmodus': 'karte', 'suche': 'exact model identification',
                 'szene': 'Brief identification of Qwen Image 2.1', 'motiv': 'Exact source model identification'}
        folgen = [
            [a('ai-presenter-workflow'), d05],
            [karte, a('ai-workflow-objects'), a('ai-presenter-workflow')],
            [d04, d06, a('ai-layers')],
            [a('ai-workflow-objects'), a('ai-layers'), a('ai-presenter-workflow')],
            [a('ai-local-edit'), a('ai-workflow-objects'), a('ai-local-edit')],
            [a('ai-reference-wall'), a('ai-presenter-workflow'), d15],
            [a('ai-license-check'), karte, a('ai-license-check')],
            [a('ai-workflow-objects'), a('ai-presenter-workflow'), figur()]]
    elif s.get('thema') == 'Nintendo: The Problem with Durable Cards':
        def a(kennung):
            besch = {'business-floral-cards': 'Original illustration of two small floral playing-card decks with different paper thickness',
                     'business-family-cards': 'Illustrative fictional 1950s family playing generic flower cards; not a Disney product or documented family',
                     'business-handcraft': 'Anonymous period craft worker painting a small flower card; not a likeness of the named founder',
                     'business-market': 'Period wooden shop counter with flower-card trays and coins, no real branded packaging',
                     'business-durable-deck': 'Weathered but usable thick-paper floral playing-card deck',
                     'business-distribution': 'Illustrative period merchant carrying flower-card decks through an Osaka-like market',
                     'business-fresh-decks': 'Period merchant offering a fresh floral deck beside an older deck',
                     'business-workshop': 'Hand-operated press, paper and drying floral cards in a period workshop',
                     'business-presenter-decks': 'Original channel presenter examining an aged and a fresh floral card deck in his storytelling studio',
                     'business-presenter-price': 'Original channel presenter comparing richly decorated and simpler flower-card decks in his studio'}
            return asset(kennung, besch[kennung])
        folgen = [
            [a('business-presenter-decks'), a('business-durable-deck')],
            [a('business-handcraft'), a('business-workshop'), a('business-floral-cards'), a('business-durable-deck')],
            [a('business-workshop'), a('business-market'), a('business-durable-deck'), a('business-presenter-decks'), a('business-floral-cards')],
            [grafik(0), grafik(1), grafik(2), grafik(3)],
            [a('business-distribution'), a('business-market'), a('business-fresh-decks'), a('business-distribution')],
            [a('business-family-cards'), a('business-floral-cards'), a('business-family-cards'), a('business-fresh-decks')],
            [a('business-presenter-price'), grafik(2), a('business-family-cards'), a('business-market'), a('business-floral-cards')],
            [figur(), a('business-durable-deck')]]
    else:
        raise ValueError('Keine redaktionelle Bildregie fuer diese Vorlage')
    if len(folgen) != len(s['teile']):
        raise ValueError('Die Vorlage hat eine andere Anzahl Sprechphasen')
    for t, folge in zip(s['teile'], folgen):
        t['bildfolge'] = folge
    return s
