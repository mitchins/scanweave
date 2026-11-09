from pathlib import Path
import numpy as np,json
from PIL import Image
root=Path('/data/coding/scanweave/qualification/acr06/local/ink37/owner37/source-render');out=[]
for engine in ('pdfium','poppler','mupdf'):
 for doc,n in (('historical',2),('historical',5),('receipts',4)):
  for dpi in (96,300):
   a=np.asarray(Image.open(root/engine/f'{doc}-{n:02}-{dpi}-source.png').convert('RGB'));b=np.asarray(Image.open(root/engine/f'{doc}-{n:02}-{dpi}-candidate.png').convert('RGB'));r={'engine':engine,'document':doc,'page':n,'dpi':dpi,'shape_source':a.shape,'shape_candidate':b.shape}
   if a.shape==b.shape:
    delta=np.abs(a.astype('int16')-b.astype('int16'));r.update(changed_pixels=int(np.any(delta!=0,axis=2).sum()),max_channel_delta=int(delta.max()),mean_absolute_channel_delta=float(delta.mean()))
   out.append(r)
Path('/data/coding/scanweave/qualification/acr06/ink37/polarity37/owner-source-render-metrics.json').write_text(json.dumps(out,indent=2)+'\n')
for row in out:print(row)
