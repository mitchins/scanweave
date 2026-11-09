from pathlib import Path
from PIL import Image
import numpy as np,json,hashlib
root=Path('/data/coding/scanweave/qualification/acr06'); loc=root/'local/ink37'; rows=[]
for engine in ('pdfium','poppler','mupdf'):
 for doc in ('historical','financial','mixed','receipts','forms'):
  folder=loc/'three-engine'/engine/doc
  for path in sorted(folder.glob('main-*.png')):
   suffix=path.name[len('main-'):]; candidate=folder/('candidate-'+suffix)
   a=np.asarray(Image.open(path).convert('RGB')); b=np.asarray(Image.open(candidate).convert('RGB'))
   if a.shape!=b.shape: raise ValueError((path,a.shape,b.shape))
   diff=np.any(a!=b,axis=2); delta=np.abs(a.astype(np.int16)-b.astype(np.int16)); dest=folder/('diff-'+suffix); Image.fromarray(diff).save(dest)
   rows.append({'engine':engine,'document':doc,'page':int(suffix[:-4]),'width':a.shape[1],'height':a.shape[0],'changed_pixels':int(diff.sum()),'maximum_channel_delta':int(delta.max()),'total_absolute_channel_delta':int(delta.sum()),'diff_mask':str(dest),'diff_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
(root/'ink37/pixel-diffs.json').write_text(json.dumps(rows,indent=2)+'\n')
