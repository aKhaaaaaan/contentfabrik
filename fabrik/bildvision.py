"""Echte Bildanfragen an das bereits genutzte multimodale Groq-Qwen-Modell."""
import base64,json,math,os,time,urllib.error,urllib.request
import ki_speicher

MODELL='qwen/qwen3.8-27b'
CACHE_MODELL='groq:'+MODELL
VERBRAUCH=[]


def pruefen(prompt,schema,bilder):
    if len(bilder)!=1 or not isinstance(bilder[0],bytes) or not bilder[0]:
        raise ValueError('Bildpruefung braucht genau ein echtes JPEG')
    key=os.environ['GROQ_API_KEY']
    if ki_speicher.sperre(key,CACHE_MODELL):
        raise RuntimeError('Groq-Vision derzeit gesperrt')
    ende=min(time.monotonic()+90,float(os.environ.get('CF_SCHRITT_ENDE','inf')))
    import autorenvergleich
    text=prompt+'\nReturn exactly ONE evaluation in pruefung for the supplied index. JSON schema: '+json.dumps(schema)
    fmt={'type':'json_schema','json_schema':{'name':'contentfabrik_bildpruefung',
         'strict':True,'schema':autorenvergleich.groq_schema(schema)}}
    fmt['json_schema']['schema']['properties']['pruefung'].update(minItems=1,maxItems=1)
    # Offizielle Gratisbasis8KTPM; ein Bild zaehlt2048Tokens, nie seineBase64zeichen.
    reserve=math.ceil((len(text)+len(json.dumps(fmt)))/3)+2048+1024
    if reserve>7900:
        raise ValueError('Bildpruefauftrag passt nicht in die Minutenreserve')
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
            ki_speicher.sperren(key,CACHE_MODELL,'Groq-Vision HTTP429',warte)
        raise RuntimeError(f'Groq-Vision HTTP{e.code}') from None
    used=d.get('usage',{}).get('total_tokens')
    VERBRAUCH.append((time.monotonic(),used if type(used) is int and used>0 else reserve))
    choice=d['choices'][0]
    if choice.get('finish_reason')!='stop':
        raise ValueError('Groq-Vision-Antwort unvollstaendig')
    answer=json.loads(choice['message']['content'])
    if not ki_speicher.schema_ok(answer,schema):
        raise ValueError('Groq-Vision-Schema nicht bestanden')
    return answer,CACHE_MODELL
