import pathlib,json,sys,numpy as np
from PIL import Image
sys.path.insert(0,'/data/coding/scanweave/qualification/acr06/ink33r')
from prepare import chars_from_hocr
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');O=R/'local/hvc41';wt=np.array([.2126,.7152,.0722],np.float32)
for d in ('financial','mixed','forms'):
 b=json.loads((R/'local/ink33r'/f'{d}.pdf.json').read_text())
 for i,p in enumerate(b['pages'],1):
  a=np.asarray(Image.open(R/'local/ink33r/renders'/d/f'{i:02d}-source.png').convert('RGB'));h,w=a.shape[:2];y=a.astype(np.float32)@wt;ref=np.zeros((h,w),bool)
  for line in chars_from_hocr(p['hocr']):
   for word in line['words']:
    for char in word['chars']:
     x0,y0,x1,y1=map(int,char['box']);x0=max(0,x0);y0=max(0,y0);x1=min(w,x1);y1=min(h,y1)
     if x1-x0<2 or y1-y0<2:continue
     q=y[y0:y1,x0:x1];bg=float(np.percentile(q,85));ink=q<bg-30;paper=q>bg-10
     if ink.sum()>=3 and paper.sum()>=3:ref[y0:y1,x0:x1]|=ink
  Image.fromarray((ref*255).astype('uint8')).save(O/'masks'/f'corpus-{d}-{i:02d}-reference-ink.png');print(d,i,flush=True)
