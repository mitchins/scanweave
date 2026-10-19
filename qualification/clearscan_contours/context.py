"""Fixed physical neighboring text comparison; actual PDF viewer zoom800%."""
from pathlib import Path
import argparse
from PIL import Image,ImageDraw
import pypdfium2 as pdfium
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
a=argparse.ArgumentParser();a.add_argument('dpi',type=int);a.add_argument('arm');args=a.parse_args();dpi=args.dpi;s=dpi/300;pt=72/dpi;b=B/str(dpi)
for region,pi,bb in [('serif',0,(60,75,480,135)),('italic',6,(60,75,480,135)),('punctuation',3,(260,75,700,135)),('kana',0,(65,700,390,755))]:
 bb=tuple(round(x*s) for x in bb);x0,y0,x1,y1=bb;panel=Image.new('RGB',(1300,5*190),'white');draw=ImageDraw.Draw(panel)
 for i,(label,p) in enumerate([('source',None),('pristine',None),('Adobe',b/'adobe.pdf'),('baseline',b/'previous.pdf'),(args.arm,b/(args.arm+'.pdf'))]):
  if p:
   doc=pdfium.PdfDocument(p);w,h=doc[pi].get_size();im=doc[pi].render(scale=8,crop=(x0*pt,h-y1*pt,w-x1*pt,y0*pt)).to_pil()
  else:
   f=ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}'/('oracle' if label=='pristine' else 'input')/f'page{pi:02}.png';im=Image.open(f).crop(bb);im=im.resize((round(im.width*pt*8),round(im.height*pt*8)),Image.Resampling.NEAREST)
  draw.text((5,i*190+5),label,fill='black');panel.paste(im.convert('RGB'),(130,i*190+25))
 panel.save(b/f'{args.arm}-{region}-800pct.png')
