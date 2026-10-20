"""Fixed twelve source regions, actual PDF layers, two independent renderers."""
from pathlib import Path
import json,subprocess,hashlib
import pikepdf,pypdfium2 as pdfium
from PIL import Image,ImageDraw
B=Path(__file__).resolve().parent;R=B.parents[1]
for arm in ['control','a']:
 for layer in ['vector','raster']:
  q=pikepdf.open(B/f'{arm}.pdf')
  for pg in q.pages:
   ops=[];inside=False
   for op in pikepdf.parse_content_stream(pg):
    o=str(op.operator)
    if o=='BT':inside=True
    if (layer=='vector' and o not in ['Do','f','f*']) or (layer=='raster' and not inside):ops.append(op)
    if o=='ET':inside=False
   pg.Contents=pikepdf.Stream(q,pikepdf.unparse_content_stream(ops))
   if layer=='vector' and '/XObject' in pg.Resources:del pg.Resources['/XObject']
  q.save(B/f'{arm}-{layer}.pdf')
paths=[('Source',R/'qualification/pdf_packaging/real/input/history-02.pdf',0),('Control',B/'control.pdf',0),('A/B vector',B/'a-vector.pdf',0),('A/B raster',B/'a-raster.pdf',0),('A/B final',B/'a.pdf',0),('Adobe',R/'qualification/pdf_packaging/groups/historical-adobe.pdf',2)]
regions=json.loads((B/'regions.json').read_text());docs=[];texts=[]
for name,path,i in paths:
 d=pdfium.PdfDocument(str(path));pg=d[i];docs.append((name,path,i,d,pg));im=pg.render(scale=1.5).to_pil().convert('RGB');im.save(B/(name.replace('/','-').replace(' ','-')+'-native.png'))
 texts.append({'arm':name,'pdfium':pg.get_textpage().get_text_range(),'poppler':subprocess.check_output(['pdftotext','-raw','-f',str(i+1),'-l',str(i+1),str(path),'-']).decode()})
for renderer in ['pdfium','poppler']:
 sheets=[]
 for n,entry in enumerate(regions):
  x0,y0,x1,y1=entry['observation']['bbox_px'];row=[]
  for name,path,i,d,pg in docs:
   w,h=pg.get_size();xp=max(0,x0-6)/1676*w;yp=max(0,y0-6)/2287*h;xq=min(1676,x1+6)/1676*w;yq=min(2287,y1+6)/2287*h
   if renderer=='pdfium':im=pg.render(scale=12,crop=(xp,h-yq,w-xq,yp)).to_pil().convert('RGB')
   else:
    dst=B/'temporary-crop';subprocess.run(['pdftoppm','-f',str(i+1),'-l',str(i+1),'-singlefile','-r','864','-x',str(round(xp*12)),'-y',str(round(yp*12)),'-W',str(round((xq-xp)*12)),'-H',str(round((yq-yp)*12)),'-png',str(path),str(dst)],check=True,capture_output=True);im=Image.open(str(dst)+'.png').convert('RGB');Path(str(dst)+'.png').unlink()
   tile=Image.new('RGB',(max(190,im.width),im.height+24),'white');tile.paste(im,(0,24));ImageDraw.Draw(tile).text((3,3),name+' '+entry['observation']['text_hypothesis'],fill='black');row.append(tile)
  sheet=Image.new('RGB',(sum(t.width for t in row),max(t.height for t in row)),'white');x=0
  for t in row:sheet.paste(t,(x,0));x+=t.width
  sheet.save(B/f'{renderer}-region-{n:02}.png');sheets.append(sheet)
 canvas=Image.new('RGB',(max(s.width for s in sheets),sum(s.height for s in sheets)),'white');y=0
 for s in sheets:canvas.paste(s,(0,y));y+=s.height
 canvas.save(B/f'{renderer}-twelve.png')
(B/'search.json').write_text(json.dumps(texts,indent=2))
