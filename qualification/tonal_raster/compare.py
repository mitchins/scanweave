"""Two independent renderers, fixed physical crops, local features and native search."""
from pathlib import Path
import json,hashlib,subprocess,os
import pikepdf,pypdfium2 as pdfium,numpy as np
from PIL import Image,ImageDraw
B=Path(__file__).resolve().parent;R=B.parents[1];controls=json.load(open(B/'controls.json'));results=json.load(open(B/'comparison.json')) if (B/'comparison.json').exists() else []
def stats(a,b):
 a=np.asarray(a);b=np.asarray(b);H,W,_=a.shape;total=changed=maximum=dark=lost=gxs=gys=0
 for start in range(0,H,128):
  end=min(H,start+128);lo=max(0,start-1);hi=min(H,end+1)
  ac=a[start:end].astype(np.int16);bc=b[start:end].astype(np.int16);e=np.abs(ac-bc);total+=int(e.sum());changed+=int(np.any(e>0,axis=2).sum());maximum=max(maximum,int(e.max()))
  ga=a[lo:hi]@np.array([.2126,.7152,.0722],np.float32);gb=b[lo:hi]@np.array([.2126,.7152,.0722],np.float32);off=start-lo;size=end-start
  gxs+=float(np.abs(np.diff(ga[off:off+size],axis=1)-np.diff(gb[off:off+size],axis=1)).sum())
  n=min(end,H-1)-start
  if n>0:gys+=float(np.abs((ga[off+1:off+n+1]-ga[off:off+n])-(gb[off+1:off+n+1]-gb[off:off+n])).sum())
  first=max(1,start)-lo;last=min(end,H-1)-lo
  if last<=first:continue
  c=ga[first:last,1:-1];d=gb[first:last,1:-1]
  for axis in [0,1]:
   p,q=(ga[first-1:last-1,1:-1],ga[first+1:last+1,1:-1]) if axis==0 else (ga[first:last,:-2],ga[first:last,2:]);u,v=(gb[first-1:last-1,1:-1],gb[first+1:last+1,1:-1]) if axis==0 else (gb[first:last,:-2],gb[first:last,2:])
   for contrast,retained in [(np.minimum(p,q)-c,np.minimum(u,v)-d),(c-np.maximum(p,q),d-np.maximum(u,v))]:
    test=contrast>=8;limit=np.where(contrast>=12,contrast*.5-1,2);dark+=int(test.sum());lost+=int((test&(retained<limit)).sum())
 return {'mae':total/(H*W*3),'max_channel_error':maximum,'changed_fraction':changed/(H*W),'dark_and_light_ridge_tests':dark,'lost_ridges':lost,'gradient_error_x':gxs/(H*(W-1)),'gradient_error_y':gys/((H-1)*W)}
def streams(q):return sorted(hashlib.sha256(o.read_bytes()).hexdigest() for o in q.objects if isinstance(o,pikepdf.Stream) and str(o.get('/Subtype'))!='/Image' and str(o.get('/Type')) not in ['/ObjStm','/XRef'])
for name,regions in controls['regions'].items():
 if any(r['id']==name for r in results):continue
 images={};docs={};row={'id':name,'arms':{},'regions':[]}
 baseline=pikepdf.open(B/'baseline'/f'{name}.pdf');base_streams=streams(baseline)
 for arm in ['baseline','q98','q100']:
  path=B/arm/f'{name}.pdf';q=pikepdf.open(path);assert streams(q)==base_streams;doc=pdfium.PdfDocument(str(path));docs[arm]=doc;pg=doc[0];w,h=pg.get_size();tp=pg.get_textpage();text=tp.get_text_range();native=pg.render(scale=300/72).to_pil().convert('RGB');(B/'renders'/arm).mkdir(parents=True,exist_ok=True);native.save(B/'renders'/arm/f'{name}-pdfium.png');images[(arm,'pdfium')]=native
  dst=B/'renders'/arm/f'{name}-poppler';subprocess.run(['pdftoppm','-f','1','-l','1','-singlefile','-r','300','-png',str(path),str(dst)],check=True,capture_output=True);images[(arm,'poppler')]=Image.open(str(dst)+'.png').convert('RGB')
  ims=[o for o in q.objects if isinstance(o,pikepdf.Stream) and o.get('/Subtype')==pikepdf.Name.Image];assert len(ims)==1
  raw=ims[0].read_raw_bytes();sampling=None
  if str(ims[0].get('/Filter'))=='/DCTDecode':
   im=Image.open(__import__('io').BytesIO(raw));sampling=im.layer if im.mode=='RGB' else 'gray';assert sampling=='gray' or all(c[1:3]==(1,1) for c in sampling)
  report=json.load(open(str(path)+'.json'));row['arms'][arm]={'pdf_bytes':path.stat().st_size,'raster_bytes':len(raw),'filter':str(ims[0].get('/Filter')),'sampling':sampling,'pdf_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pdfium_text':text,'poppler_text':subprocess.check_output(['pdftotext','-raw',str(path),'-']).decode(),'vector_occurrences':sum(o['owner'].startswith('visible') for o in report['conversion']['page_reports'][0]['occurrences'])}
 for renderer in ['pdfium','poppler']:
  for arm in ['q98','q100']:row['arms'][arm][renderer]=stats(images[('baseline',renderer)],images[(arm,renderer)])
  sheets=[]
  for label,x0,y0,x1,y1 in regions:
   parts=[];rec={'renderer':renderer,'label':label,'fraction':[x0,y0,x1,y1],'arms':{}}
   for arm in ['baseline','q98','q100']:
    im=images[(arm,renderer)];W,H=im.size;box=(round(x0*W),round(y0*H),round(x1*W),round(y1*H));crop=im.crop(box);rec['arms'][arm]=stats(images[('baseline',renderer)].crop(box),crop)
    # Actual 300% native-resolution PDF crop, not interpolated finished typography.
    if renderer=='pdfium':
     pg=docs[arm][0];w,h=pg.get_size();zoom=pg.render(scale=900/72,crop=(w*x0,h*(1-y1),w*(1-x1),h*y0)).to_pil().convert('RGB')
    else:
     path=B/arm/f'{name}.pdf';w,h=docs[arm][0].get_size();dst=B/'renders'/'crop';subprocess.run(['pdftoppm','-f','1','-l','1','-singlefile','-r','900','-x',str(round(x0*w*12.5)),'-y',str(round(y0*h*12.5)),'-W',str(round((x1-x0)*w*12.5)),'-H',str(round((y1-y0)*h*12.5)),'-png',str(path),str(dst)],check=True,capture_output=True);zoom=Image.open(str(dst)+'.png').convert('RGB')
    tile=Image.new('RGB',(zoom.width,zoom.height+24),'white');tile.paste(zoom,(0,24));ImageDraw.Draw(tile).text((3,4),arm+' '+label,fill='black');parts.append(tile)
   sheet=Image.new('RGB',(sum(t.width for t in parts),max(t.height for t in parts)),'white');offset=0
   for t in parts:sheet.paste(t,(offset,0));offset+=t.width
   out=B/f'{name}-{renderer}-{len(sheets):02}.png';sheet.save(out);sheet.thumbnail((2400,700));sheets.append(sheet);row['regions'].append(rec)
  # Compact overview; full crop sheets remain locally inspectable.
  overview=Image.new('RGB',(max(t.width for t in sheets),sum(t.height for t in sheets)),'white');offset=0
  for t in sheets:overview.paste(t,(0,offset));offset+=t.height
  overview.thumbnail((2400,3600));overview.save(B/f'{name}-{renderer}-details.png')
 for arm in ['q98','q100']:
  assert row['arms'][arm]['pdfium_text']==row['arms']['baseline']['pdfium_text'];assert row['arms'][arm]['poppler_text']==row['arms']['baseline']['poppler_text']
 results.append(row);(B/'comparison.json').write_text(json.dumps(results,indent=2));print(name,[(a,d['pdf_bytes']) for a,d in row['arms'].items()],flush=True)
 for d in docs.values():d.close()
