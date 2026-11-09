from pathlib import Path
from PIL import Image
import numpy as np,json
base=Path('/data/coding/scanweave/qualification/acr06'); idx=json.load((base/'ink37/glyph-panel-index.json').open()); cache={}; rows=[]
for k,x in enumerate(idx,1):
 key=(x['document'],x['page'])
 if key not in cache:
  folder=base/'local/ink37/three-engine/pdfium'/key[0]; cache[key]=[np.asarray(Image.open(folder/f'{arm}-{key[1]:02d}.png').convert('RGB')) for arm in ('main','candidate')]
 a,b=cache[key]; x0,y0,x1,y1=map(int,x['box']); aa=a[y0:y1,x0:x1];bb=b[y0:y1,x0:x1]; delta=np.any(aa!=bb,axis=2)
 rows.append({'number':k,'document':key[0],'page':key[1],'box':x['box'],'changed_pixels':int(delta.sum()),'crop_pixels':int(delta.size)})
(base/'ink37/known-glyph-diff.json').write_text(json.dumps(rows,indent=2)+'\n')
