from pathlib import Path
from PIL import Image
import numpy as np,json,xml.etree.ElementTree as ET,re
root=Path('/data/coding/scanweave/qualification/acr06');rows=[]
for doc,n in [('historical',2),('historical',5),('receipts',4)]:
 a=np.asarray(Image.open(root/'local/ink33/renders'/doc/f'{n:02d}-source.png').convert('RGB'),dtype=np.int16);b=np.asarray(Image.open(root/'local/ink37c/renders/pdfium'/f'{doc}-{n:02d}-300.png').convert('RGB'),dtype=np.int16);xml=json.load(open(root/'local/ink37c'/f'{doc}.pdf.json'))['pages'][n-1]['hocr'];w=[]
 for e in ET.fromstring(xml).iter():
  if 'ocrx_word' not in e.attrib.get('class','').split():continue
  m=re.search(r'bbox (\d+) (\d+) (\d+) (\d+)',e.attrib.get('title',''))
  if m:
   x0,y0,x1,y1=map(int,m.groups());x0=max(0,x0);y0=max(0,y0);x1=min(a.shape[1],x1);y1=min(a.shape[0],y1)
   if x1<=x0 or y1<=y0:continue
   x=a[y0:y1,x0:x1];y=b[y0:y1,x0:x1];col=x.max(axis=2)-x.min(axis=2);sel=col>=45
   w.append({'bbox':[x0,y0,x1,y1],'text':''.join((s.text or '').strip() for s in e if 'ocrx_cinfo' in s.attrib.get('class','')),'mae':float(np.abs(x-y).mean()),'chromatic_pixels':int(sel.sum()),'chromatic_mae':float(np.abs(x-y)[sel].mean()) if sel.sum()>25 else None})
 vals=[(v['chromatic_mae'],v) for v in w if v['chromatic_mae'] is not None];vals.sort(key=lambda x:x[0],reverse=True);rows.append({'document':doc,'page':n,'top':vals[:5]});print(doc,n,vals[:3],flush=True)
(root/'ink37c/word-fidelity.json').write_text(json.dumps(rows,indent=2)+'\n')
