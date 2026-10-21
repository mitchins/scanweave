#!/usr/bin/env python3
"""Full final-document renders and fixed physical context at 100/300/800/1600%.
No image enlargement stands in for vector rendering. Oracle is evaluator-only.
"""
import argparse,json,math,subprocess,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
import pypdfium2 as pdfium

FINAL_PDF = 'final.pdf'

B=Path(__file__).resolve().parent;ROOT=B.parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--dpi',type=int,nargs='+',default=[300,600]);ap.add_argument('--full',action='store_true');a=ap.parse_args();records=[]
for dpi in a.dpi:
 b=B/str(dpi);pt=72/dpi;s=dpi/300
 if a.full:
  doc=pdfium.PdfDocument(b/FINAL_PDF);pdfsha=hashlib.sha256((b/FINAL_PDF).read_bytes()).hexdigest()
  for zoom in [1,3,8,16]:
   dest=b/'zooms'/str(zoom);dest.mkdir(parents=True,exist_ok=True)
   subprocess.run(['pdftoppm','-r',str(72*zoom),'-gray','-png',str(b/FINAL_PDF),str(dest/'poppler')],check=True,capture_output=True)
   for pi,page in enumerate(doc):
    im=page.render(scale=math.nextafter(zoom,0)).to_pil().convert('L');out=dest/f'pdfium-{pi+1}.png';im.save(out)
    for ren in ['pdfium','poppler']:
     path=dest/f'{ren}-{pi+1}.png';img=Image.open(path);records.append({'dpi':dpi,'page':pi,'zoom':zoom,'renderer':ren,'pdf_sha256':pdfsha,'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'dimensions':list(img.size)})
 for region,pi,bb in [('serif',0,(60,75,480,135)),('italic',6,(60,75,480,135)),('punctuation',3,(260,75,700,135)),('kana',0,(65,700,390,755))]:
  bb=tuple(round(v*s) for v in bb);x0,y0,x1,y1=bb
  arms=[('source',ROOT/f'qualification/clearscan_competitive/{dpi}/source.pdf'),('pristine (oracle)',ROOT/'qualification/clearscan_competitive/300/source-font-control/oracle-source-font.pdf'),('Adobe XI',b/'adobe.pdf'),('previous',b/'previous.pdf'),('final',b/FINAL_PDF),('vector only',b/'final/stages/S4-vector-only.pdf'),('raster only',b/'final/raster-only.pdf')]
  for zoom in [1,3,8,16]:
   panels=[]
   for label,path in arms:
    doc=pdfium.PdfDocument(path);w,h=doc[pi].get_size();im=doc[pi].render(scale=zoom,crop=(x0*pt,h-y1*pt,w-x1*pt,y0*pt)).to_pil().convert('RGB');panels.append((label,im))
   width=max(im.width for _,im in panels)+155;height=sum(max(im.height+26,52) for _,im in panels);sheet=Image.new('RGB',(width,height),'white');d=ImageDraw.Draw(sheet);y=0
   for label,im in panels:d.text((4,y+3),label,fill='black');sheet.paste(im,(150,y+22));y+=max(im.height+26,52)
   sheet.save(b/f'{region}-{zoom*100}pct.png')
if records:(B/'zoom-renders.json').write_text(json.dumps(records,indent=2))
