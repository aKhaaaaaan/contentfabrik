"""Dokumentierte Bigarrow-Anleitungen als klar gekennzeichnete Diagramme, kein Mac-Test."""
from pathlib import Path
import textwrap
from PIL import Image,ImageDraw,ImageFont

SOURCE='https://github.com/franzenzenhofer/big-arrow-on-the-screen'
TITLES=['WHICH ALLOW BUTTON?','POINT AT THE CONTROL','HUMAN HANDOFF',
        'ARROWS','BOXES','LABELS','INSTALL WITH HOMEBREW','ADD THE SKILL','AGENT ISSUES A COMMAND',
        'SYSTEM SETTINGS EXAMPLE','YOU DECIDE','YOU CLICK','CLICKS PASS THROUGH',
        'KEYBOARD FOCUS STAYS','ARROW REMOVES ITSELF','NO AI INSIDE','NO AUTOMATIC CLICKING','LIKE / SHARE / SAVE']


def grafik(ziel,variante):
    if type(variante) is not int or not 0<=variante<18:raise ValueError('Bigarrow-Variante ungueltig')
    im=Image.new('RGB',(1080,1920),'#10202d');d=ImageDraw.Draw(im)
    font=Path(__file__).resolve().parents[1]/'schriften/Montserrat-ExtraBold.ttf'
    def txt(x,y,t,size=36,color='#edf6ff'):
        d.text((x,y),t,font=ImageFont.truetype(str(font),size),fill=color)
    def box(x,y,w,h,fill='#25394d'):
        d.rounded_rectangle((x,y,x+w,y+h),radius=20,fill=fill,outline='#7091a7',width=3)
    def arrow(start=(255,1040),end=(785,800)):
        d.line([start,end],fill='#ffae35',width=20)
        x,y=end;d.polygon([(x,y),(x-70,y-4),(x-35,y+58)],fill='#ffae35')
    txt(75,315,'BIGARROW / macOS',42,'#20d2be')
    for i,line in enumerate(textwrap.wrap(TITLES[variante],28)):txt(75,395+i*50,line,40)
    txt(75,1500,'DOCUMENTED EXAMPLE / ILLUSTRATION',25,'#8dabbf')
    if variante in (6,7,8):
        box(70,570,940,780,'#08141f')
        txt(100,610,'TERMINAL INSTRUCTIONS',32,'#20d2be')
        lines=(['brew install franzenzenhofer/tap/bigarrow'] if variante==6 else
               ['bigarrow install-skill','Skill teaches the agent','how to issue commands'] if variante==7 else
               ['bigarrow point','--element "Allow"','--app "System Settings"'])
        for n,line in enumerate(lines):txt(100,725+n*100,line,36)
        txt(100,1205,'DOCUMENTED COMMANDS',30,'#ffae35')
    elif variante in (15,16):
        box(80,570,920,320);txt(120,640,'A POINTER, NOT AN AI MODEL',35,'#ffae35')
        txt(120,730,'Arrow + box + label',40)
        box(80,985,920,320);txt(125,1045,'HUMAN DECISION',43,'#20d2be')
        txt(125,1150,'Approve or close the dialog',35)
    elif variante==17:
        for x,title in [(80,'LIKE'),(405,'SHARE'),(730,'SAVE')]:
            box(x,710,270,450);txt(x+30,995,title,40)
        d.polygon([(165,920),(165,820),(195,820),(210,770),(230,770),(230,830),(295,830),(285,920)],fill='#20d2be')
        d.rectangle((135,820,156,920),fill='#20d2be')
        d.line((465,920,465,830,585,830),fill='#20d2be',width=15)
        d.polygon([(610,830),(565,795),(565,865)],fill='#20d2be')
        d.polygon([(810,785),(910,785),(910,930),(860,895),(810,930)],fill='#20d2be')
        txt(105,1290,'SAVE THIS HUMAN-HANDOFF GUIDE',30)
    else:
        box(70,565,940,735,'#dce4ec');txt(100,600,'System Settings',36,'#172635')
        box(105,700,840,430,'#f8fafc');txt(135,740,'Permission example',34,'#172635')
        txt(135,835,'Human approval required',32,'#172635')
        box(665,960,240,95,'#3677dd');txt(697,982,'ALLOW',35)
        if variante!=14:arrow((200+(variante%3)*90,1180),(785,1010))
        if variante in (4,5):
            d.rectangle((650,945,920,1070),outline='#de7b2c',width=12)
        if variante in (2,5,9,10,11,12):
            box(190,1160,665,80,'#13283d');txt(220,1180,'YOU CHOOSE AND CLICK',30,'#ffae35')
        if variante==13:
            txt(140,1190,'Keyboard focus remains here',28,'#172635')
        if variante==14:txt(160,1180,'Overlay is gone; window remains',28,'#172635')
        if variante==3:txt(100,1370,'ARROW POINTS TO THE CONTROL',29,'#ffae35')
        if variante==4:txt(100,1370,'BOX HIGHLIGHTS THE CONTROL',29,'#ffae35')
        if variante==5:txt(100,1370,'LABEL EXPLAINS THE HUMAN STEP',28,'#ffae35')
    Path(ziel).parent.mkdir(parents=True,exist_ok=True);im.save(ziel,'JPEG',quality=95)
    return Path(ziel)


def bildfolge(s):
    if SOURCE not in s.get('quellen',[]) or len(s.get('teile',[]))!=7:
        raise ValueError('Bigarrow-Regie passt nicht zu diesem Skript')
    phases=[[0,1,2],[3,4,5],[6,7,8],[9,10,11],[12,13,14],[15,16],[17]]
    for t,ids in zip(s['teile'],phases):
        t['bildfolge']=[{'bildmodus':'grafik','grafik_typ':'bigarrow','grafik_variante':i,
                        'motiv':TITLES[i],'szene':'Documented explanatory diagram: '+TITLES[i],
                        'suche':'documented macOS human handoff'} for i in ids]
    return s
