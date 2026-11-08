#!/usr/bin/env python3
"""Frozen matched-content development fixture, seed 270602; not a holdout."""
from pathlib import Path
import hashlib, json, random
from PIL import Image, ImageDraw, ImageFont
import pikepdf
SEED=270602
OUT=Path('/data/coding/scanweave/qualification/acr06/local/c2b/development')
OUT.mkdir(parents=True, exist_ok=True)
FONTS=Path('/usr/share/fonts/truetype/dejavu')
fonts=['DejaVuSerif.ttf','DejaVuSansMono-Oblique.ttf','DejaVuSerif-Bold.ttf','DejaVuSans.ttf','DejaVuSans-Bold.ttf']
lines=['office affine fife fluff fi fl ff ffi', 'touching letters minimum ill tilt rifle 111', "Mixed 0123456789 I l i t r f .,;'-", 'small CAPS ALPHA Roman italic bold scan', 'broken faint missing strokes eee ttt rrr', 'she took to me try pray a body can']
rng=random.Random(SEED)
order=[rng.randrange(len(lines)) for _ in range(18)]
hashfile=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest={'purpose':'development; matched content and layout, not holdout','seed':SEED,'generator_sha256':hashfile(Path(__file__)),'font_license':'DejaVu: Bitstream Vera license, DejaVu changes public domain; /usr/share/doc/fonts-dejavu-core/copyright','fonts':{f:hashfile(FONTS/f) for f in fonts},'line_indices':order,'files':{}}
for dpi in (300,600):
    scale=dpi/72; points=432; width=round(points*scale)
    im=Image.new('L',(width,width),255); draw=ImageDraw.Draw(im)
    for row, line in enumerate(order):
        font=ImageFont.truetype(str(FONTS/fonts[row%len(fonts)]),round((9+(row%3)*2)*scale))
        draw.text((round(15*scale),round((20+row*21)*scale)),lines[line],font=font,fill=0)
    png=OUT/f'development-{dpi}.png'; im.save(png)
    tmp=OUT/f'tmp-{dpi}.pdf'; im.convert('RGB').save(tmp,'PDF',resolution=dpi)
    pdf=OUT/f'development-{dpi}.pdf'
    with pikepdf.Pdf.open(tmp) as doc:
        doc.pages[0].MediaBox=[0,0,points,points]; doc.save(pdf, static_id=True)
    tmp.unlink()
    manifest['files'][str(dpi)]={'png_sha256':hashfile(png),'pdf_sha256':hashfile(pdf),'pixels':width,'points':points}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
