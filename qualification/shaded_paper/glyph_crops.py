from pathlib import Path
import json,math
import pypdfium2 as pdfium
from PIL import Image,ImageDraw
B=Path(__file__).resolve().parent;R=B.parents[1];p=json.loads((B/'b.pdf.json').read_text())['conversion']['page_reports'][0];obs={o['symbol_id']:o for o in p['reconstruction']['observations']};owners=[o for o in p['occurrences'] if o['owner']=='visible_tounicode'];selected=[o for o in owners if o['symbol_id'] in obs][:12];rows=[];sheets=[]
paths=[('Source',R/'qualification/pdf_packaging/real/input/history-02.pdf',0),('Vector only',B/'b-vector.pdf',0),('Final',B/'b.pdf',0),('Raster only',B/'b-raster.pdf',0),('Adobe',R/'qualification/pdf_packaging/groups/historical-adobe.pdf',2)]
for own in selected:
 ob=obs[own['symbol_id']];x0,y0,x1,y1=ob['bbox_px'];row=[]
 for name,path,i in paths:
  d=pdfium.PdfDocument(str(path));pg=d[i];w,h=pg.get_size();x0p=max(0,x0-6)/1676*w;y0p=max(0,y0-6)/2287*h;x1p=min(1676,x1+6)/1676*w;y1p=min(2287,y1+6)/2287*h
  im=pg.render(scale=12,crop=(x0p,h-y1p,w-x1p,y0p)).to_pil().convert('RGB');canvas=Image.new('RGB',(max(220,im.width),im.height+25),'white');canvas.paste(im,(0,25));ImageDraw.Draw(canvas).text((4,4),name+' '+ob['text_hypothesis'],fill='black');row.append(canvas)
 sheet=Image.new('RGB',(sum(i.width for i in row),max(i.height for i in row)),'white');x=0
 for im in row:sheet.paste(im,(x,0));x+=im.width
 sheets.append(sheet);rows.append({'owner':own,'observation':ob})
canvas=Image.new('RGB',(max(x.width for x in sheets),sum(x.height for x in sheets)),'white');y=0
for im in sheets:canvas.paste(im,(0,y));y+=im.height
canvas.save(B/'accepted-glyphs.png');(B/'accepted-glyphs.json').write_text(json.dumps(rows,indent=2));print(len(rows))
