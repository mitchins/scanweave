from pathlib import Path
from PIL import Image
import numpy as np,json,xml.etree.ElementTree as ET,re
base=Path('/data/coding/scanweave/qualification/acr06');results=[]
for doc,n in [('historical',1),('historical',3),('historical',4),('receipts',6),('receipts',7),('receipts',8),('receipts',9)]:
 p=base/'local/ink37/owner37'/f'{doc}.pdf.json';z=json.loads(p.read_text())['pages'][n-1]['hocr'];root=ET.fromstring(z)
 src=np.asarray(Image.open(base/'local/ink33/renders'/doc/f'{n:02d}-source.png').convert('RGB'));out=np.asarray(Image.open(base/'local/ink37/owner37/renders/pdfium'/doc/f'candidate-{n:02d}.png').convert('RGB'));mask=np.zeros(src.shape[:2],bool)
 for el in root.iter():
  if 'ocrx_word' not in el.attrib.get('class','').split():continue
  m=re.search(r'bbox (\d+) (\d+) (\d+) (\d+)',el.attrib.get('title',''))
  if m:
   x0,y0,x1,y1=map(int,m.groups());mask[max(0,y0):min(mask.shape[0],y1),max(0,x0):min(mask.shape[1],x1)]=True
 dark=mask & (np.mean(src,axis=2)<100);delta=np.abs(src.astype('int16')-out.astype('int16'));results.append({'document':doc,'page':n,'ocr_box_pixels':int(mask.sum()),'dark_source_samples_pixels':int(dark.sum()),'dark_pixels_changed':int((dark & np.any(delta!=0,axis=2)).sum()),'dark_channel_mae':float(delta[dark].mean()) if dark.any() else None,'note':'Dark-pixel threshold is a proxy, not an ink ownership mask; baseline is unchanged from main.'})
(base/'ink37/polarity37/owner-no-vector-source.json').write_text(json.dumps(results,indent=2)+'\n')
for r in results:print(r,flush=True)
