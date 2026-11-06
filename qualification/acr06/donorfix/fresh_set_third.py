#!/usr/bin/env python3
"""Frozen seed 290613; page images and pristine truth for issue 29 qualification."""
from pathlib import Path
import hashlib, json, random
from PIL import Image, ImageDraw, ImageFont
import pikepdf
SEED=290613
ROOT=Path('/data/coding/scanweave/qualification/acr06/local/donorfix/fresh3')
ROOT.mkdir(parents=True,exist_ok=True)
FONTS=Path('/usr/share/fonts/truetype/dejavu')
fonts=['DejaVuSerif.ttf','DejaVuSansMono-Oblique.ttf','DejaVuSerif-Bold.ttf','DejaVuSans.ttf','DejaVuSans-Bold.ttf']
lines=['office affine fife fluff fi fl ff ffi', 'touching letters minimum ill tilt rifle 111', "Mixed 0123456789 I l i t r f .,;'-", 'small CAPS ALPHA Roman italic bold scan', 'broken faint missing strokes: eee ttt rrr', 'she took to me try pray a body can']
random.seed(SEED)
pdf=pikepdf.Pdf.new(); metadata=[]
for n,(dpi,width,points) in enumerate([(200,1208,435),(300,1812,435),(600,3625,435),(300.0827586,1813,435)]):
    scale=width/points
    im=Image.new('L',(width,width),255); draw=ImageDraw.Draw(im)
    for row in range(18):
        text=lines[row%len(lines)]; f=ImageFont.truetype(str(FONTS/fonts[row%len(fonts)]),round((9+(row%3)*2)*scale))
        y=round((20+row*21)*scale); x=round(15*scale)
        if row==1:
            for ch in text:
                draw.text((x,y),ch,font=f,fill=0,stroke_width=0)
                x+=max(1,round(draw.textlength(ch,font=f)-0.6*scale))
        else: draw.text((x,y),text,font=f,fill=0)
    truth=ROOT/f'truth-{n}.png'; im.save(truth)
    degraded=im.copy(); d=ImageDraw.Draw(degraded)
    for row in (4,10,16):
        y=round((20+row*21+7)*scale)
        for _ in range(4):
            x=round(random.uniform(22,210)*scale)
            d.rectangle((x,y,x+max(1,round(.6*scale)),y+max(1,round(2*scale))),fill=255)
    d.rectangle((round(15*scale),round((20+10*21)*scale),round(220*scale),round((20+10*21+15)*scale)), fill=None)
    for y in range(round((20+16*21)*scale),round((20+16*21+15)*scale)):
        for x in range(round(15*scale),round(210*scale)):
            v=degraded.getpixel((x,y)); degraded.putpixel((x,y),round(v*.55+255*.45))
    src=ROOT/f'source-{n}.png'; degraded.save(src)
    temp=ROOT/f'page-{n}.pdf'; degraded.convert('RGB').save(temp,'PDF',resolution=72*scale)
    with pikepdf.Pdf.open(temp) as page:
        pdf.pages.append(page.pages[0]); pdf.pages[-1].MediaBox=[0,0,points,points]
    metadata.append({'page_index':n,'nominal_dpi':dpi,'pixels':width,'points':points,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'truth_sha256':hashlib.sha256(truth.read_bytes()).hexdigest()})
pdf.save(ROOT/'source.pdf')
(ROOT/'manifest.json').write_text(json.dumps({'seed':SEED,'fonts':fonts,'font_license':'Bitstream Vera license; DejaVu changes public domain; /usr/share/doc/fonts-dejavu-core/copyright','pages':metadata},indent=2)+'\n')
