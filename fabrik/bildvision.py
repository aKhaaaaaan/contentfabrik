"""Echte Bildanfragen an das bereits genutzte multimodale Groq-Qwen-Modell."""
import base64,json,math,os,time,urllib.error,urllib.request
from pathlib import Path
import ki_speicher

MODELL='qwen/qwen3.8-27b'
CACHE_MODELL='groq:'+MODELL
VERBRAUCH=[]
# GEMESSEN 05.11.2026 (Business Casio, Lauf 42027412733): die Einzelbild-Ersatzpruefungen am Vormittag leerten
# das Groq-Tageskontingent (429 um 10:51 UTC, Sperre bis 15:40). Am Nachmittag war das Casio-Video FERTIG,
# Gemini antwortete mit 503 - und Groq durfte nicht mehr: kein Urteil, Video verworfen. Darum bleibt ein Teil
# des Tageskontingents der Schlusspruefung (zweck='video') vorbehalten. Tageslimit ist eine Schaetzung
# (Groq-Gratisstufe ~200K Token/Tag laut Drittquellen); eine Bildpruefung kostet ~4.300-4.500 Token.
TAG=Path('verlauf/groq-vision-tag.json')
TAG_LIMIT=200_000
VIDEO_RESERVE=80_000


def _heute():
    return time.strftime('%Y-%m-%d',time.gmtime())


def tag_verbrauch():
    d=ki_speicher.lesen_json(TAG)
    n=d.get('tokens')
    return n if d.get('datum')==_heute() and type(n) is int and n>0 else 0


def tag_addieren(n):
    with ki_speicher.SPERRE:
        ki_speicher.speichern(TAG,{'datum':_heute(),'tokens':tag_verbrauch()+int(n)})


def pruefen(prompt,schema,bilder,_nochmal=True,zweck='video'):
    if len(bilder)!=1 or not isinstance(bilder[0],bytes) or not bilder[0]:
        raise ValueError('Bildpruefung braucht genau ein echtes JPEG')
    key=os.environ['GROQ_API_KEY']
    if ki_speicher.sperre(key,CACHE_MODELL):
        raise RuntimeError('Groq-Vision derzeit gesperrt')
    ende=min(time.monotonic()+90,float(os.environ.get('CF_SCHRITT_ENDE','inf')))
    import autorenvergleich
    liste='pruefung' in schema.get('properties',{})
    text=prompt+('\nReturn exactly ONE evaluation in pruefung for the supplied index.' if liste else '')+' JSON schema: '+json.dumps(schema)
    fmt={'type':'json_schema','json_schema':{'name':'contentfabrik_bildpruefung',
         'strict':True,'schema':autorenvergleich.groq_schema(schema)}}
    if liste:
        fmt['json_schema']['schema']['properties']['pruefung'].update(minItems=1,maxItems=1)
    # Offizielle Gratisbasis8KTPM; ein Bild zaehlt2048Tokens, nie seineBase64zeichen.
    reserve=math.ceil((len(text)+len(json.dumps(fmt)))/3)+2048+1024
    if reserve>7900:
        raise ValueError('Bildpruefauftrag passt nicht in die Minutenreserve')
    if zweck!='video' and tag_verbrauch()+reserve>TAG_LIMIT-VIDEO_RESERVE:
        raise RuntimeError('Groq-Vision-Tagesrest bleibt der Videopruefung vorbehalten')
    while True:
        jetzt=time.monotonic();VERBRAUCH[:]=[(t,n) for t,n in VERBRAUCH if jetzt-t<61]
        if sum(n for _,n in VERBRAUCH)+reserve<=8000:
            break
        pause=min(60,max(.1,61-(jetzt-VERBRAUCH[0][0])))
        if pause+5>=ende-jetzt:
            raise RuntimeError('Groq-Vision-Minutenreserve passt nicht in die Schrittfrist')
        print(f'Bildpruefung: echte Groq-Minutenreserve, {pause:.1f}s warten',flush=True)
        time.sleep(pause)
    payload={'model':MODELL,'temperature':.1,'reasoning_effort':'none',
             'max_completion_tokens':1024,'response_format':fmt,
             'messages':[{'role':'user','content':[{'type':'text','text':text},
                {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(bilder[0]).decode()}}]}]}
    request=urllib.request.Request('https://api.groq.com/openai/v1/chat/completions',
        data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,
        'Content-Type':'application/json','User-Agent':'Contentfabrik/1.0'})
    rest=ende-time.monotonic()
    if rest<=0:
        raise RuntimeError('Groq-Vision-Schrittfrist erreicht')
    try:
        with urllib.request.urlopen(request,timeout=min(45,rest)) as response:d=json.load(response)
    except urllib.error.HTTPError as e:
        if e.code==429:
            import autorenvergleich
            detail=e.read().decode(errors='replace')
            warte=autorenvergleich.groq_wartezeit(e.headers,detail)
            # GEMESSEN 16.10.2026: Gratisstufe 8.000 Token/Minute, eine Bildpruefung ~5.000-6.000 -> 429 schon
            # beim zweiten Bild einer Minute. Kurze Serverfrist abwarten statt die Bildpruefung aufzugeben.
            if _nochmal and warte<=65 and float(os.environ.get('CF_SCHRITT_ENDE','inf'))-time.monotonic()>warte+120:
                print(f'Groq-Vision: Minutenkontingent, {warte:.0f}s warten',flush=True)
                time.sleep(warte+1)
                return pruefen(prompt,schema,bilder,_nochmal=False,zweck=zweck)
            ki_speicher.sperren(key,CACHE_MODELL,'Groq-Vision HTTP429',warte)
        if e.code==400 and _nochmal and 'json_validate_failed' in e.read().decode(errors='replace'):
            # GEMESSEN 16.10.2026: etwa jede dritte Antwort von qwen3.8-27b war kaputtes JSON
            # ("-ok-ok-ok..."). Ein neuer Versuch ist kein Lockern - das Urteil kommt nur aus gueltigem JSON.
            print('Groq-Vision: ungueltiges JSON, neuer Versuch',flush=True)
            return pruefen(prompt,schema,bilder,_nochmal=False,zweck=zweck)
        raise RuntimeError(f'Groq-Vision HTTP{e.code}') from None
    used=d.get('usage',{}).get('total_tokens')
    VERBRAUCH.append((time.monotonic(),used if type(used) is int and used>0 else reserve))
    tag_addieren(VERBRAUCH[-1][1])
    choice=d['choices'][0]
    if choice.get('finish_reason')!='stop':
        raise ValueError('Groq-Vision-Antwort unvollstaendig')
    answer=json.loads(choice['message']['content'])
    if not ki_speicher.schema_ok(answer,schema):
        raise ValueError('Groq-Vision-Schema nicht bestanden')
    return answer,CACHE_MODELL


# GEMESSEN 06.11.2026 (Ford-Langvideo 42255331749): Gemini-Tageskontingent leer + Groq-Vision 429/503 -> jede
# Pruefung 'nicht verfuegbar', bauen.py fuellte 13 Einstellungen mit denselben zwei Nachbarbildern (bild_passt
# 2/10, 2,5 Std. Budget ohne Video). bauen.py liest diesen Zaehler und bricht dann mit Anbieterpause ab.
AUSFAELLE=0


def mit_ausweichweg(gemini_aufruf,prompt,schema,bild,zweck='einzelbild'):
    """Gemini-Bildurteil; antwortet Gemini GAR NICHT (503/429/Zeitlimit), urteilt Groq-Vision mit demselben Auftrag.

    GEMESSEN 16.10.2026 (Laeufe 38873412464, 38878792792): stundenlang HTTP 503 bei allen Gemini-Modellen,
    danach 429 - fertige Videos blieben ohne Urteil. Eichung 15.10.: Groq urteilte genauso streng (LV 0/7).
    Eine echte Ablehnung durch Gemini bleibt bestehen; ausgewichen wird nur bei fehlender Antwort."""
    try:
        return gemini_aufruf()
    except Exception as e:
        global AUSFAELLE
        if not os.environ.get('GROQ_API_KEY'):
            AUSFAELLE+=1
            raise
        print(f'Gemini-Bildpruefung ausgefallen ({type(e).__name__}) - Groq-Vision urteilt mit demselben Auftrag',flush=True)
        import stoerung
        stoerung.melden('gemini-bild',f'Gemini-Bildpruefung antwortet nicht ({type(e).__name__}).',
                        'Groq-Vision prueft die Bilder mit denselben Regeln weiter.')
        try:
            return pruefen(prompt,schema,[bild],zweck=zweck)
        except Exception as fehler:
            print(f'Groq-Vision: {type(fehler).__name__}: {str(fehler)[:120]}',flush=True)
            stoerung.melden('bildpruefung-aus','Auch Groq-Vision antwortet nicht - keine Bildpruefung moeglich.',
                            'Ungepruefte Bilder werden nie verwendet; das Video wird spaeter erneut geprueft.')
            AUSFAELLE+=1
            raise
