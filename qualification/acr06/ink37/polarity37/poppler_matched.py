from pathlib import Path
from PIL import Image
import numpy as np,subprocess,json
base=Path('/data/coding/scanweave/qualification/acr06');out=base/'local/ink37/owner37/source-render/poppler';rows=[]
for doc,n in [('historical',2),('historical',5),('receipts',4)]:
 for dpi in (96,300):
  original=out/f'{doc}-{n:02}-{dpi}-source.png';w,h=Image.open(original).size
  source=Path('/data/coding/scanweave/qualification/pdf_packaging/groups')/f'{doc}-input.pdf';candidate=base/'local/ink37/owner37'/f'{doc}.pdf';ims=[]
  for arm,path in (('source',source),('candidate',candidate)):
   stem=out/f'{doc}-{n:02}-{dpi}-{arm}-matched';subprocess.run(['pdftoppm','-f',str(n),'-l',str(n),'-singlefile','-scale-to-x',str(w),'-scale-to-y',str(h),'-png',str(path),str(stem)],check=True);ims.append(np.asarray(Image.open(str(stem)+'.png').convert('RGB')))
  delta=np.abs(ims[0].astype('int16')-ims[1].astype('int16'));rows.append({'document':doc,'page':n,'dpi_nominal':dpi,'width':w,'height':h,'changed_pixels':int(np.any(delta!=0,axis=2).sum()),'max_delta':int(delta.max()),'mean_delta':float(delta.mean())});print(rows[-1],flush=True)
(base/'ink37/polarity37/owner-poppler-matched.json').write_text(json.dumps(rows,indent=2)+'\n')
