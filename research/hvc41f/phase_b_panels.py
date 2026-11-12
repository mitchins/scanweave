"""Make 96/300 DPI patch grids from the already completed isolated renders."""
import hashlib,json,pathlib
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f';out=[]
for dpi in (96,300):
 for i in (243,38,18):
  cells=[]
  for v in ('B0','B1','B2'):
   row=[]
   for engine in ('splash-aa','cairo','pdfium','mupdf'):
    im=Image.open(L/f'{v}-{i:03}-{engine}-{dpi}.png').convert('RGB');mk=Image.open(L/f'{v}-{i:03}-{engine}-{dpi}-outside.png').convert('RGB');scale=4 if dpi==300 else 8;im=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST);mk=mk.resize(im.size,Image.Resampling.NEAREST);row.append((v,engine,im,mk))
   cells.append(row)
  cw=max(z[2].width for row in cells for z in row)+10;ch=max(z[2].height for row in cells for z in row)*2+44;sheet=Image.new('RGB',(cw*4,ch*3),'white');draw=ImageDraw.Draw(sheet)
  for y,row in enumerate(cells):
   for x,(v,e,im,mk) in enumerate(row):draw.text((x*cw+2,y*ch+2),f'{v} {e} {dpi} DPI',fill='black');sheet.paste(im,(x*cw+2,y*ch+20));sheet.paste(mk,(x*cw+2,y*ch+24+im.height))
  p=L/f'phase-b-grid-{i:03}-{dpi}.png';sheet.save(p);out.append({'proposal':i,'dpi':dpi,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(E/'phase-b-panel-index.json').write_text(json.dumps(out,indent=2)+'\n');print('patch panels',len(out))
