from pathlib import Path
from PIL import Image
import numpy as np,json,math
from scipy.ndimage import binary_fill_holes,label
root=Path('/data/coding/scanweave/qualification/acr06');idx=json.load(open(root/'ink37c/panel-index.json'));imgs={};rows=[]
for g in idx:
 if g['kind']!='glyph':continue
 d,n=g['document'],g['page'];key=(d,n)
 if key not in imgs:imgs[key]=[np.asarray(Image.open(p).convert('L')) for p in [root/'local/ink33/renders'/d/f'{n:02d}-source.png',root/'local/ink37c/renders/pdfium'/f'{d}-{n:02d}-300.png']]
 x0,y0,x1,y1=g['crop_box']; counts=[]
 for a in imgs[key]:
  dark=a[y0:y1,x0:x1]<128;holes=binary_fill_holes(dark)&~dark;lab,num=label(holes);counts.append([int((lab==i).sum()) for i in range(1,num+1) if (lab==i).sum()>=2])
 rows.append({'document':d,'page':n,'box':g['box'],'sheet':g['sheet'],'row':g['sheet_row'],'source_holes':counts[0],'compact_holes':counts[1]})
(root/'ink37c/counters.json').write_text(json.dumps(rows,indent=2)+'\n')
for i,r in enumerate(rows,1):
 if len(r['compact_holes'])<len(r['source_holes']):print(i,r,flush=True)
