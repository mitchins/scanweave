from pathlib import Path
from PIL import Image
import json, numpy as np, hashlib
base=Path('/data/coding/scanweave/qualification/acr06'); out=base/'local/ink37/masks'; out.mkdir(parents=True,exist_ok=True)
rows=[]
for row in json.loads((base/'ink37/segmentation-investigation.json').read_text()):
 doc=row['document']; page=row['page']; a=np.asarray(Image.open(base/'local/ink33/renders'/doc/f'{page:02}-source.png').convert('RGB'))
 p=row['corner_paper']; lum=a[:,:,0].astype(float)*.2126+a[:,:,1]*.7152+a[:,:,2]*.0722; pl=p[0]*.2126+p[1]*.7152+p[2]*.0722
 mask=np.abs(lum-pl)>60; path=out/f'{doc}-{page:02}-main.png'; Image.fromarray(mask).save(path)
 rows.append({'document':doc,'page':page,'pixel_count':int(mask.sum()),'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(base/'ink37/main-mask-index.json').write_text(json.dumps(rows,indent=2)+'\n')
