#!/usr/bin/env python3
import json,math
from pathlib import Path
import pypdfium2 as p
from PIL import Image,ImageDraw
q=Path('/data/coding/scanweave/qualification');d=q/'acr06/local/donorfix'; cases={'single':(0,['w000053','w000102','w000130','w000175','w000180']),'forms':(1,['w000471']),'historical':(1,['w000070','w000106']),'financial':(8,['w000005'])};rows=[]
for name,(page,words) in cases.items():
 cand=d/'candidate'/f'{name}.pdf'; main=d/'baseline'/('single.pdf' if name=='single' else f'{name}-off.pdf'); inp=q/('pdf_packaging/real/input/scan-c03-29.pdf' if name=='single' else f'pdf_packaging/groups/{name}-input.pdf')
 if not cand.exists() or not Path(str(cand)+'.json').exists(): continue
 report=json.loads(Path(str(main)+'.json').read_text()); obs=report['conversion']['page_reports'][page]['reconstruction']['observations']; rw=report['pages'][page]['raster_width']; rh=report['pages'][page]['raster_height']; imgs=[]
 for f in (inp,main,cand):
  doc=p.PdfDocument(str(f)); imgs.append(doc[page].render(scale=150/72).to_pil().convert('RGB'))
 for word in words:
  boxes=[o['bbox_px'] for o in obs if o['symbol_id'].startswith(word+'s')]
  if not boxes: continue
  sx=imgs[0].width/rw;sy=imgs[0].height/rh; box=(math.floor(min(x[0] for x in boxes)*sx)-30,math.floor(min(x[1] for x in boxes)*sy)-10,math.ceil(max(x[2] for x in boxes)*sx)+30,math.ceil(max(x[3] for x in boxes)*sy)+10); tiles=[im.crop(box).resize(((box[2]-box[0])*4,(box[3]-box[1])*4),Image.Resampling.NEAREST) for im in imgs];rows.append((name+' '+word,tiles))
if rows:
 w=max(sum(t.width+10 for t in tiles) for _,tiles in rows);h=sum(max(t.height for t in tiles)+20 for _,tiles in rows);sheet=Image.new('RGB',(w,h),'white');draw=ImageDraw.Draw(sheet);y=0
 for label,tiles in rows:
  draw.text((0,y),label+' [source | main | candidate]',fill='black');x=0;y+=16
  for tile in tiles:sheet.paste(tile,(x,y));x+=tile.width+10
  y+=max(t.height for t in tiles)+4
 sheet.save(d/'confirmed-defects-preview.png')
 print('preview rows',len(rows))
