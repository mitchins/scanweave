from pathlib import Path
from PIL import Image
import numpy as np,json
from skimage.metrics import structural_similarity
root=Path('/data/coding/scanweave/qualification/acr06'); results=[]
for doc in ('historical','financial','mixed','receipts','forms'):
 folder=root/'local/ink37/three-engine/pdfium'/doc
 for src in sorted((root/'local/ink33/renders'/doc).glob('*-source.png')):
  n=int(src.name[:2]); a=np.asarray(Image.open(src).convert('L'))
  row={'document':doc,'page':n}
  for arm in ('main','candidate'):
   p=folder/f'{arm}-{n:02d}.png'; b=np.asarray(Image.open(p).convert('L'))
   if a.shape!=b.shape: row[arm]=None; row['note']='render geometry differs'; continue
   row[arm]=float(structural_similarity(a,b,data_range=255))
  results.append(row)
(root/'ink37/source-ssim.json').write_text(json.dumps(results,indent=2)+'\n')
