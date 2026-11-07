#!/usr/bin/env python3
"""Freeze independent clean ink truth and simulated aged scans, seed 609151."""
import hashlib,json
from pathlib import Path
import numpy as np
import pikepdf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT=Path('/data/coding/scanweave/qualification/acr06/local/bg150/fresh-truth'); OUT.mkdir(parents=True,exist_ok=True)
SEED=609151; rng=np.random.default_rng(SEED); W,H=2550,3300
font_path=Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'); pages=[]
for page in range(2):
 truth=Image.new('L',(W,H),255); d=ImageDraw.Draw(truth); text_truth=[]; text_boxes=[]
 title='AGED PAPER LEGIBILITY AND PUNCTUATION STUDY'; d.text((150,100),title,font=ImageFont.truetype(str(font_path),45),fill=0); text_truth.append(title)
 for row in range(27):
  pt=6+row%3; font=ImageFont.truetype(str(font_path),round(pt*300/72)); y=190+row*59
  text=f'Item {row+1:02d}: café naïve, 1.25 : 3.14; amount ${row+1}.09. i j.'
  d.text((150,y),text,font=font,fill=0); text_truth.append(text); text_boxes.append([150,y,1700,y+42])
 for y in range(1900,2401,62): d.line((150,y,1900,y),fill=0,width=2)
 for x in range(150,1901,350): d.line((x,1900,x,2396),fill=0,width=2)
 for y in range(2520,3090,9):
  for x in range(150,1030,9):
   r=1+int(3*(x-150)/880); d.ellipse((x-r,y-r,x+r,y+r),fill=60)
 art=Image.fromarray(rng.normal(140,35,(550,750)).clip(0,255).astype('uint8')).filter(ImageFilter.GaussianBlur(8))
 truth.paste(art,(1200,2520))
 truth_path=OUT/f'pristine-{page+1}.png'; truth.save(truth_path)
 yy,xx=np.mgrid[:H,:W]; paper=244-7*xx/W-7*yy/H+3*np.sin(xx/210)+rng.normal(0,3,(H,W))
 ink=255-np.asarray(truth,dtype=np.float32); opacity=np.full((H,1),.76,dtype=np.float32)
 for row in range(27):
  if row%5==0: opacity[190+row*59:240+row*59]=.42
 scan=np.clip(paper-ink*opacity,0,255).astype('uint8')
 # Remove narrow pieces from intended ink; pristine truth retains them.
 for row in range(27):
  for _ in range(3):
   x=int(rng.integers(180,1600)); y=int(rng.integers(195+row*59,225+row*59))
   scan[y:y+2,x:x+5]=np.clip(paper[y:y+2,x:x+5],0,255).astype('uint8')
 source=Image.fromarray(scan,'L').convert('RGB'); png=OUT/f'source-{page+1}.png';source.save(png)
 pw,ph=((612.,792.) if page==0 else (612.37,791.63)); pdf=pikepdf.Pdf.new(); pg=pdf.add_blank_page(page_size=(pw,ph)); stream=pdf.make_stream(source.tobytes())
 stream.Type=pikepdf.Name.XObject; stream.Subtype=pikepdf.Name.Image; stream.Width=W; stream.Height=H; stream.ColorSpace=pikepdf.Name.DeviceRGB; stream.BitsPerComponent=8
 pg.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=stream)); pg.Contents=pdf.make_stream(f'q {pw} 0 0 {ph} 0 0 cm /Im0 Do Q\n'.encode())
 path=OUT/f'page-{page+1}.pdf';pdf.save(path)
 pages.append({'pdf':str(path),'source_png':str(png),'pristine_png':str(truth_path),'page_pt':[pw,ph],'pixels':[W,H],'text_truth':text_truth,'text_boxes_pixels':text_boxes})
manifest={'seed':SEED,'font':str(font_path),'font_sha256':hashlib.sha256(font_path.read_bytes()).hexdigest(),'font_license':'Bitstream Vera; DejaVu changes public domain; /usr/share/doc/fonts-dejavu-core/copyright','pages':pages}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
