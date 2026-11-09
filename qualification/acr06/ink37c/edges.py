from pathlib import Path
from PIL import Image
import numpy as np,json,scipy.ndimage as ndi,xml.etree.ElementTree as ET,re
root=Path('/data/coding/scanweave/qualification/acr06');rows=[]
for d,n in [('historical',2),('historical',5),('receipts',4)]:
 src=np.asarray(Image.open(root/'local/ink33/renders'/d/f'{n:02d}-source.png').convert('L'),dtype=np.float32);out=np.asarray(Image.open(root/'local/ink37c/renders/pdfium'/f'{d}-{n:02d}-300.png').convert('L'),dtype=np.float32)
 mask=np.zeros(src.shape,bool);xml=json.load(open(root/'local/ink37c'/f'{d}.pdf.json'))['pages'][n-1]['hocr']
 for e in ET.fromstring(xml).iter():
  if 'ocrx_word' not in e.attrib.get('class','').split():continue
  m=re.search(r'bbox (\d+) (\d+) (\d+) (\d+)',e.attrib.get('title',''))
  if m:
   x0,y0,x1,y1=map(int,m.groups());mask[max(0,y0):min(src.shape[0],y1),max(0,x0):min(src.shape[1],x1)]=True
 dx=lambda a:np.hypot(ndi.sobel(a,0)/8,ndi.sobel(a,1)/8)
 a=dx(src);b=dx(out);edge=mask&(a>30); dark=mask&(src<128);row={'doc':d,'page':n,'edges':int(edge.sum()),'edge_recall_same_30':float((b[edge]>30).mean()),'edge_recall_same_15':float((b[edge]>15).mean()),'edge_strength_ratio':float(b[edge].mean()/a[edge].mean()),'dark_recall_same_128':float((out[dark]<128).mean())};rows.append(row);print(row,flush=True)
(root/'ink37c/edges.json').write_text(json.dumps(rows,indent=2)+'\n')
