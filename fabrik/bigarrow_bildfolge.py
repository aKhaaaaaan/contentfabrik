"""Dokumentierte Bigarrow-Anleitungen als klar gekennzeichnete Diagramme, kein Mac-Test."""
from pathlib import Path
import textwrap
from PIL import Image,ImageDraw,ImageFont

SOURCE='https://github.com/franzenzenhofer/big-arrow-on-the-screen'
# GEMESSEN 14.10.2026 (Lauf 38591953175): Keynote-Ausschnitt (4) und statische
# Einstellungsansicht (15) fielen bei der Einzelbildpruefung durch (3/10, 5/10) - die Boxen
# waren zu klein, "no AI / no auto-click" war nicht sichtbar. Dafuer jetzt eigene Diagramme.
DEMOS={0:'bigarrow-allow',3:'bigarrow-arrow-print',5:'bigarrow-label-chrome'}
TITLES=['WHICH ALLOW BUTTON?','POINT AT THE CONTROL','THAT CONTROL ON YOUR MAC',
        'ARROWS','BOXES AND LABELS','LABELS','INSTALL WITH HOMEBREW','ADD THE SKILL','AGENT ISSUES A COMMAND',
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
    def fenster(x,y,w,h,titel):
        # macOS-Fenster: Titelleiste mit den drei Ampelpunkten, damit es als Mac erkennbar ist.
        d.rounded_rectangle((x,y,x+w,y+h),radius=22,fill='#eef2f6',outline='#9fb3c4',width=3)
        d.rounded_rectangle((x,y,x+w,y+70),radius=22,fill='#d3dbe3')
        d.rectangle((x,y+48,x+w,y+70),fill='#d3dbe3')
        for n,c in enumerate(('#ff5f57','#febc2e','#28c840')):
            d.ellipse((x+28+n*42,y+22,x+54+n*42,y+48),fill=c)
        txt(x+170,y+16,titel,30,'#172635')
    def kreuz(x,y,w,h):
        d.line((x,y,x+w,y+h),fill='#e5484d',width=16);d.line((x,y+h,x+w,y),fill='#e5484d',width=16)
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
    elif variante==2:
        fenster(70,600,940,620,'System Settings')
        txt(115,720,'Privacy & Security',34,'#172635')
        txt(115,790,'"Terminal" wants to control',30,'#172635')
        txt(115,835,'this computer.',30,'#172635')
        box(150,960,300,100,'#8a9aab');txt(195,990,"DON'T ALLOW",30)
        box(620,960,300,100,'#3677dd');txt(705,990,'ALLOW',34)
        arrow((330,1380),(700,1075))
        box(90,1300,520,90,'#13283d');txt(115,1322,'THAT CONTROL',34,'#ffae35')
    elif variante==4:
        fenster(70,580,940,700,'Keynote')
        for n in range(3):
            d.rounded_rectangle((120,690+n*110,420,770+n*110),radius=10,fill='#c9d3dd')
        box(520,760,420,110,'#3677dd');txt(585,792,'Export...',34)
        d.rectangle((495,735,965,895),outline='#ffae35',width=12)
        d.rounded_rectangle((520,960,960,1060),radius=16,fill='#ffae35')
        txt(545,985,'LABEL: click Export',32,'#10202d')
        d.line((740,960,740,900),fill='#ffae35',width=10)
        txt(120,1130,'BOX + LABEL DRAWN ABOVE THE WINDOW',27,'#172635')
    elif variante==15:
        box(70,570,440,330,'#13283d');d.rounded_rectangle((200,610,380,760),radius=18,outline='#8dabbf',width=8)
        txt(232,660,'AI',60,'#8dabbf');txt(160,820,'AI MODEL',36);kreuz(185,600,210,175)
        box(570,570,440,330,'#13283d')
        d.polygon([(720,610),(720,760),(752,728),(790,790),(812,778),(776,716),(820,714)],fill='#8dabbf')
        txt(625,820,'AUTO-CLICK',36);kreuz(665,600,210,175)
        fenster(70,960,940,420,'Your Mac')
        box(640,1150,260,90,'#3677dd');txt(710,1170,'ALLOW',32)
        arrow((260,1330),(650,1180))
        txt(110,1060,'Bigarrow only draws the arrow.',30,'#172635')
        txt(110,1430,'NO AI INSIDE / NO AUTOMATIC CLICKING',27,'#ffae35')
    elif variante==16:
        box(80,610,920,640,'#dce4ec');txt(120,675,'THE HUMAN MAKES THE CLICK',34,'#172635')
        box(580,860,320,120,'#3677dd');txt(620,900,'APPROVE',36)
        d.polygon([(700,925),(700,1080),(735,1045),(780,1110),(808,1085),(760,1018),(820,1010)],fill='#172635')
        txt(125,1170,'Pointer does not press buttons',31,'#172635')
    elif variante==3:
        box(80,650,920,580);box(690,770,220,200,'#3677dd')
        txt(735,845,'UI',48);arrow((180,1160),(785,785))
        txt(120,1330,'OVERLAY ARROW POINTS TO AN ELEMENT',27,'#ffae35')
    elif variante==14:
        for x,label in [(65,'BEFORE'),(560,'AFTER')]:
            txt(x+85,580,label,43,'#20d2be')
            box(x,700,455,510,'#dce4ec')
            txt(x+35,750,'Permission',30,'#172635')
            box(x+120,905,215,90,'#3677dd');txt(x+150,930,'ALLOW',32)
        arrow((120,1160),(300,890))
        txt(180,1290,'INSTRUCTION FINISHED',38,'#ffae35')
        txt(200,1390,'SAME WINDOW / OVERLAY REMOVED',28)
    elif variante==17:
        for x,title in [(80,'LIKE'),(405,'SHARE'),(730,'SAVE')]:
            box(x,710,270,450);txt(x+30,995,title,40)
        d.polygon([(165,920),(165,820),(195,820),(210,770),(230,770),(230,830),(295,830),(285,920)],fill='#20d2be')
        d.rectangle((135,820,156,920),fill='#20d2be')
        d.line((465,920,465,830,585,830),fill='#20d2be',width=15)
        d.polygon([(610,830),(565,795),(565,865)],fill='#20d2be')
        d.polygon([(810,785),(910,785),(910,930),(860,895),(810,930)],fill='#20d2be')
        txt(105,1290,'SAVE THIS HUMAN-HANDOFF GUIDE',30)
    elif variante==0:
        for x,label in [(70,'WINDOW A'),(565,'WINDOW B')]:
            box(x,640,440,510,'#dce4ec');txt(x+25,690,label,32,'#172635')
            box(x+100,945,240,95,'#3677dd');txt(x+135,968,'ALLOW',35)
        txt(155,1230,'SAME LABEL. WHICH CONTROL?',36,'#ffae35')
    elif variante in (10,11,12,13):
        box(80,560,920,730,'#dce4ec');txt(120,615,'PERMISSION EXAMPLE',34,'#172635')
        if variante==13:
            box(125,790,820,150,'#ffffff');txt(155,835,'Typing stays in this window |',33,'#172635')
            arrow((260,1180),(855,835))
            txt(130,1080,'Overlay does not take keyboard focus',27,'#172635')
        else:
            for x,label,color in [(140,'CANCEL','#607285'),(620,'ALLOW','#3677dd')]:
                box(x,930,280,100,color);txt(x+30,960,label,34)
            if variante==10:
                txt(130,790,'APPROVE OR DECLINE: YOUR CHOICE',27,'#172635')
            else:
                arrow((250,1170),(760,945))
                d.polygon([(735,1000),(735,1060),(752,1046),(770,1070),(782,1060),(764,1036),(790,1035)],fill='#172635')
                txt(130,790,'HUMAN CLICKS THE BUTTON' if variante==11 else 'CLICK REACHES WINDOW THROUGH OVERLAY',24,'#172635')
        txt(125,1360,'ILLUSTRATED INTERACTION',31,'#ffae35')
    else:
        box(70,565,940,735,'#dce4ec');txt(100,600,'System Settings',36,'#172635')
        box(105,700,840,430,'#f8fafc');txt(135,740,'Permission example',34,'#172635')
        txt(135,835,'Human approval required',32,'#172635')
        box(665,960,240,95,'#3677dd');txt(697,982,'ALLOW',35)
        if variante not in (4,5,14):arrow((200+(variante%3)*90,1180),(785,945))
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
        for entry,i in zip(t['bildfolge'],ids):
            if i in DEMOS:
                entry.update(bildmodus='asset',asset=DEMOS[i],
                             szene='Original documented Bigarrow macOS screenshot: '+TITLES[i])
    return s
