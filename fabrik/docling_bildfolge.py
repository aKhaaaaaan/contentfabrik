"""Quellengebundene Erklaergrafiken fuer Docling; keine vorgetaeuschten Tool-Ergebnisse."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SOURCE = 'https://docling-project.github.io/docling/getting_started/quickstart/'
HEADLINES = [
    'PDF TABLE: KEEP THE STRUCTURE', 'TEXT ALONE LOSES THE GRID', 'A DOCUMENTED ALTERNATIVE',
    'PDF LAYOUT + READING ORDER', 'KEEP ROWS AND COLUMNS', 'MARKDOWN OR JSON',
    'INSTALL THE PYTHON PACKAGE', 'THE DOCUMENT CONVERTER', 'A PDF IS THE INPUT',
    'EXPORT THE DOCUMENT AS MARKDOWN', 'PYTHON AND COMMAND LINE', 'OCR: FROM SCAN TO TEXT',
    'SCANNED PAGES CAN BE PROCESSED', 'LOCAL DOCUMENT WORKFLOW', 'SETUP COMES FIRST',
    'STRUCTURED DOCUMENT CONTENT', 'CONNECT TO AN AI WORKFLOW', 'LIKE · SHARE · SAVE',
]


def grafik(ziel, variante):
    if type(variante) is not int or not 0 <= variante < len(HEADLINES):
        raise ValueError('Unbekannte Docling-Einstellung')
    im = Image.new('RGB', (960, 1040), '#101c29')
    d = ImageDraw.Draw(im)
    fontpath = Path(__file__).resolve().parents[1] / 'schriften/Montserrat-ExtraBold.ttf'
    def text(x, y, t, size=28, color='#edf5ff'):
        d.text((x, y), t, fill=color, font=ImageFont.truetype(str(fontpath), size))
    def box(x, y, w, h, color='#21394c'):
        d.rounded_rectangle((x, y, x+w, y+h), radius=18, fill=color, outline='#3b6374', width=3)
    def arrow(x, y, end, color='#20d2be'):
        d.line((x, y, end-20, y), fill=color, width=8)
        d.polygon([(end, y), (end-24, y-16), (end-24, y+16)], fill=color)
    def page(x, y, w=290, h=360, title='PDF', grid=False):
        box(x, y, w, h, '#eaf3f6'); text(x+20, y+20, title, 30, '#133040')
        if grid:
            tx, ty = x+20, y+95
            for a in range(4): d.line((tx,ty+a*55,tx+w-40,ty+a*55),fill='#244859',width=3)
            for a in range(3): d.line((tx+a*(w-40)/2,ty,tx+a*(w-40)/2,ty+165),fill='#244859',width=3)
            text(tx+12,ty+14,'A',24,'#16303b');text(tx+w/2,ty+14,'B',24,'#16303b')
        else:
            for a in range(max(1,min(5,(h-120)//38+1))):
                d.rounded_rectangle((x+22,y+105+a*38,x+w-26,y+117+a*38),radius=3,fill='#9db4be')
    def terminal(lines, title='DOCUMENTED EXAMPLE'):
        box(70,260,820,520,'#08121c');text(95,290,title,25,'#20d2be')
        for i,line in enumerate(lines):text(100,360+i*70,line,27)
    def flow(labels, y=455):
        count=len(labels); w=230 if count==3 else 300
        xs=[45,365,685] if count==3 else [80,580]
        for i,(x,label) in enumerate(zip(xs,labels)):
            box(x,y,w,180);text(x+22,y+65,label,25)
            if i<count-1:arrow(x+w+8,y+90,xs[i+1]-12)
    text(45,35,'DOCLING',40,'#20d2be');text(45,100,'ILLUSTRATED WORKFLOW',22,'#8daebf')
    title=HEADLINES[variante]
    import textwrap
    for i,line in enumerate(textwrap.wrap(title,31)):text(45,160+i*43,line,32)
    if variante==0:
        page(90,330,320,390,grid=True);arrow(440,520,520);page(565,330,300,390,title='TABLE',grid=True)
        text(100,785,'ROWS + COLUMNS',34,'#20d2be')
    elif variante==1:
        page(65,340,330,400,grid=True);arrow(420,545,535)
        box(575,350,310,390);text(605,390,'PLAIN TEXT',26)
        text(605,465,'A B',40);text(605,535,'A B',40);text(605,610,'NO CELL GRID',23,'#ffc66d')
    elif variante==2:
        page(55,375,240,330,grid=True);box(365,425,230,160);text(390,480,'DOCLING',30,'#20d2be')
        page(670,375,240,330,title='CONTENT',grid=True);arrow(305,510,350);arrow(607,510,655)
        text(85,790,'DOCUMENTED CONVERSION PATH',28,'#20d2be')
        text(85,850,'converter.convert(source).document',29)
    elif variante==3:
        page(70,320,820,470,title='PAGE LAYOUT')
        for x,n in ((105,'FIRST'),(510,'THEN')):
            box(x,435,325,285);text(x+30,470,n,28,'#20d2be')
            for k in range(4):d.line((x+30,535+k*35,x+275,535+k*35),fill='#bfd5de',width=8)
        arrow(445,600,493)
    elif variante==4:
        page(70,325,325,415,title='PDF TABLE',grid=True);arrow(415,530,515)
        box(545,325,355,460);text(565,365,'MARKDOWN EXPORT',25,'#20d2be')
        text(565,445,'| A | B |',29);text(565,520,'| --- | --- |',24)
        text(565,600,'| A | B |',29);text(80,850,'ROWS AND COLUMNS AS STRUCTURED CONTENT',23,'#8daebf')
    elif variante==5:
        box(65,325,365,460);box(530,325,365,460)
        text(95,370,'MARKDOWN',30,'#20d2be');text(560,370,'JSON',30,'#20d2be')
        text(95,465,'# Heading',30);text(95,535,'| A | B |',28);text(95,605,'| --- | --- |',25)
        text(560,465,'{',36);text(590,525,'"document": {',26);text(620,590,'"tables": [...]',23);text(590,655,'}',36)
        text(75,850,'FORMAT DIAGRAM · NOT A MEASURED RESULT',22,'#8daebf')
    elif variante==6:
        terminal(['$ pip install docling'], 'INSTALL · OFFICIAL README')
        text(100,680,'PYTHON PACKAGE',36,'#20d2be')
    elif variante==7:
        terminal(['from docling.document_converter', 'import DocumentConverter', '', 'converter = DocumentConverter()'])
    elif variante==8:
        page(95,320,290,370,title='SOURCE PDF',grid=True)
        arrow(420,505,540);box(590,380,270,250);text(615,460,'CONVERTER',27,'#20d2be')
        text(105,790,'doc = converter.convert(source).document',30)
    elif variante==9:
        terminal(['doc.export_to_markdown()', '', '# Docling Technical Report', '...'], 'QUICKSTART · MARKDOWN EXPORT')
    elif variante==10:
        box(60,325,840,205);text(90,360,'PYTHON',30,'#20d2be');text(90,425,'converter.convert(source).document',29)
        box(60,580,840,205);text(90,615,'COMMAND LINE',30,'#20d2be');text(90,680,'docling https://arxiv.org/pdf/2206.01062',26)
    elif variante==11:
        page(75,330,290,410,title='SCANNED PAGE')
        arrow(390,545,485);box(510,435,150,170);text(537,490,'OCR',35,'#20d2be')
        arrow(675,520,725);box(750,375,170,325);text(765,450,'TEXT',29)
    elif variante==12:
        page(120,310,320,460,title='SCAN')
        for a in range(5):d.line((150,470+a*40,390,463+a*40),fill='#3e6474',width=7)
        arrow(455,530,535);box(565,350,295,380)
        text(590,390,'OCR TEXT',29,'#20d2be');text(590,470,'Heading',28);text(590,535,'Text content',24)
        text(110,835,'ILLUSTRATED OCR PROCESS',25,'#8daebf')
    elif variante==13:
        box(75,345,810,440,'#122f3c');text(105,380,'LOCAL MACHINE',34,'#20d2be')
        page(115,465,240,230,title='PRIVATE PDF');box(435,465,355,230);text(460,540,'LOCAL DOCLING',30)
        text(135,620,'[REDACTED]',23,'#133040')
        text(460,610,'ON YOUR MACHINE',23,'#20d2be')
        arrow(365,580,420);text(110,845,'SENSITIVE DOCUMENT WORKFLOW',28)
    elif variante==14:
        box(60,300,840,160,'#08121c');text(90,335,'LOCAL INSTALLATION REQUIRED',26,'#20d2be')
        text(90,400,'$ pip install docling',31)
        box(65,535,310,245);text(95,575,'YOUR MACHINE',27,'#20d2be');text(95,650,'Python 3.10+',29)
        arrow(390,650,535);box(570,535,320,245);text(595,575,'DOCLING PACKAGE',25,'#20d2be')
        text(595,650,'Local dependency',25);text(90,850,'SET UP BEFORE CONVERTING DOCUMENTS',25,'#ffc66d')
    elif variante==15:
        page(70,340,330,430,title='PDF CONTENT',grid=True);arrow(420,535,515)
        box(545,335,355,460)
        for y,label in ((370,'HEADING'),(445,'Text paragraph'),(520,'TABLE'),(590,'Row 1: A | B'),(660,'Row 2: A | B')):
            text(565,y,label,26,'#20d2be' if y in (370,520) else '#edf5ff')
        text(90,850,'CONTENT RELATIONSHIPS, ILLUSTRATED',25,'#8daebf')
    elif variante==16:
        page(55,340,260,400,title='PDF',grid=True);arrow(325,530,395)
        box(420,375,455,120);text(445,410,'DOCLING: PARSE + EXPORT',25,'#20d2be')
        box(420,545,455,275);text(445,580,'AI WORKFLOW INPUT',27,'#20d2be')
        text(445,650,'Heading + paragraph',26);text(445,710,'Table: A | B',26)
        d.line((645,505,645,530),fill='#20d2be',width=8)
        d.polygon([(645,540),(630,521),(660,521)],fill='#20d2be')
    else:
        for x,label in ((55,'LIKE'),(365,'SHARE'),(675,'SAVE')):
            box(x,370,230,350);text(x+30,610,label,32)
        d.polygon([(120,550),(120,460),(145,460),(160,410),(180,410),(180,465),(235,465),(225,550)],fill='#20d2be')
        d.rectangle((95,460,113,550),fill='#20d2be')
        d.line((415,550,415,470,515,470),fill='#20d2be',width=15)
        d.polygon([(540,470),(500,440),(500,500)],fill='#20d2be')
        d.polygon([(740,420),(840,420),(840,565),(790,530),(740,565)],fill='#20d2be')
        text(160,830,'SAVE THE DOCUMENTED WORKFLOW',25)
    text(45,965,'Guide based on Docling documentation · illustrative diagrams',18,'#8daebf')
    Path(ziel).parent.mkdir(parents=True,exist_ok=True);im.save(ziel,'JPEG',quality=95)
    return Path(ziel)


def bildfolge(s):
    if 'https://github.com/docling-project/docling' not in s.get('quellen', []):
        raise ValueError('Docling-Regie braucht die richtige Projektquelle')
    folgen = [[0,1,2],[3,4,5],[6,7,8],[9,10],[11,12,13],[14,15,16],[17]]
    if len(s['teile']) != len(folgen):raise ValueError('Docling-Regie erwartet sieben Sprechphasen')
    for t, ids in zip(s['teile'],folgen):
        t['bildfolge'] = [{'bildmodus':'grafik','grafik_typ':'docling','grafik_variante':i,
                          'motiv':HEADLINES[i], 'szene':'Documented explanatory diagram: '+HEADLINES[i],
                          'suche':'documented PDF workflow'} for i in ids]
    return s
