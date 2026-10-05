"""Saubere redaktionelle Vergleichsgrafiken; keine erfundenen Fotos oder Tool-Outputs."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def karten(ziel, variante=0, breite=1080, hoehe=1920):
    im = Image.new('RGB', (breite, hoehe), '#12202c')
    d = ImageDraw.Draw(im)
    sx, sy = breite / 1080, hoehe / 1920
    def box(x, y, w, h, color, line='#081118', radius=18):
        d.rounded_rectangle((x*sx,y*sy,(x+w)*sx,(y+h)*sy), int(radius*sx), fill=color, outline=line, width=max(1,int(4*sx)))
    def text(x, y, s, size=44, color='#ffffff'):
        font = ImageFont.truetype(str(Path(__file__).resolve().parents[1]/'schriften/Montserrat-ExtraBold.ttf'), int(size*sx))
        d.text((x*sx,y*sy),s,font=font,fill=color)
    def deck(x, y, dick, floral=True):
        for i in range(dick, -1, -1):
            box(x+i*3,y+i*10,270,410,'#d0b48c' if i else '#fff1d4')
        if floral:
            for a,b in ((x+65,y+90),(x+160,y+210),(x+85,y+300)):
                for dx,dy in ((-16,0),(16,0),(0,-16),(0,16)):
                    d.ellipse(((a+dx-18)*sx,(b+dy-18)*sy,(a+dx+18)*sx,(b+dy+18)*sy),fill='#eb7058')
                d.ellipse(((a-12)*sx,(b-12)*sy,(a+12)*sx,(b+12)*sy),fill='#ffc963')
        else:
            d.ellipse(((x+95)*sx,(y+155)*sy,(x+170)*sx,(y+230)*sy),fill='#e7b866')
    for y in range(0,1920,96):
        d.line((0,y*sy,breite,(y+240)*sy),fill='#182b38',width=2)
    text(90,320,'AN EARLY BUSINESS RESPONSE',34,'#85a6b7')
    if variante % 4 == 0:
        text(95,470,'A DIFFERENT DECK',62,'#ffc963')
        deck(125,680,9);deck(665,680,3,False)
        text(125,1260,'DURABLE',42);text(650,1260,'LOWER QUALITY',34)
    elif variante % 4 == 1:
        text(90,470,'TENGU',100,'#ffc963');deck(405,680,3,False)
        text(95,1270,'A cheaper line of cards',48)
    elif variante % 4 == 2:
        deck(120,630,3,False)
        d.polygon([(650*sx,690*sy),(760*sx,690*sy),(760*sx,880*sy),(825*sx,880*sy),(705*sx,1040*sy),(585*sx,880*sy),(650*sx,880*sy)],fill='#ffc963')
        text(575,1120,'LOWER PRICE',44,'#ffc963')
    else:
        text(90,480,'QUALITY AND PRICE',58,'#ffc963')
        deck(130,700,3,False)
        # Eine Preis-Marke, kein vermeintlich dickeres Deck unter LOWER QUALITY.
        box(650,750,310,260,'#ffc963')
        d.polygon([(715*sx,780*sy),(815*sx,780*sy),(815*sx,875*sy),(870*sx,875*sy),(765*sx,970*sy),(660*sx,875*sy),(715*sx,875*sy)],fill='#12202c')
        text(125,1290,'LOWER QUALITY',36);text(650,1290,'LOWER PRICE',36)
    Path(ziel).parent.mkdir(parents=True,exist_ok=True)
    im.save(ziel,'JPEG',quality=95)
    return Path(ziel)
