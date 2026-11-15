#!/usr/bin/env python3
"""Apply the existing pilot one-pixel native overlap policy to saved renders."""
import json,pathlib
import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity
from skimage.color import rgb2lab,deltaE_ciede2000
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];f=P/'pilot/phase1b/fidelity.py';v={'__file__':str(f)};s=f.read_text();exec(compile(s[:s.index('out={};start=time.monotonic()')],str(f),'exec'),v);count=0
for path in (B/'phase2/metrics').glob('*/*.json'):
 x=json.loads(path.read_text());o=x.get('native_fidelity',{})
 if o.get('status')!='dimension_mismatch':continue
 w,h=o['source'];W,H=o['output']
 if abs(w-W)>1 or abs(h-H)>1:continue
 id=x['id'];key=id.split('/')[-1];a=Image.open(B/'phase2/renders'/key/'src/pdfium-native.png').convert('RGB').crop((0,0,min(w,W),min(h,H)));b=Image.open(B/'phase2/renders'/key/x['row']/'pdfium-native.png').convert('RGB').crop((0,0,min(w,W),min(h,H)));src=np.asarray(a);dst=np.asarray(b);sg=np.asarray(a.convert('L'));dg=np.asarray(b.convert('L'));si=sg<128;di=dg<128;dl=np.abs(v['L'](src)-v['L'](dst));_,sm=structural_similarity(sg,dg,data_range=255,full=True);masks=v['masks'](id,(w,h));out={}
 for name,mask in masks.items():
  mask=mask[:a.height,:a.width];n=int(mask.sum());ink=int((si&mask).sum());pred=int((di&mask).sum());tp=int((si&di&mask).sum());val={'pixels':n,'ssim':float(sm[mask].mean()) if n else None,'ink_recall':tp/ink if ink else None,'ink_precision':tp/pred if pred else None,'mean_abs_delta_L':float(dl[mask].mean()) if n else None}
  if name=='illustration' and n:
   aa=src[mask];bb=dst[mask];total=0.;cnt=0
   for off in range(0,len(aa),100000):
    de=deltaE_ciede2000(rgb2lab(aa[off:off+100000].reshape(-1,1,3)),rgb2lab(bb[off:off+100000].reshape(-1,1,3)));total+=float(de.sum());cnt+=de.size
   val['deltaE2000_mean']=total/cnt if cnt else None
  out[name]=val
 x['native_fidelity']=out;x['native_overlap']={'source':[w,h],'output':[W,H],'overlap':[a.width,a.height],'policy':'pilot common top-left grid; at most one rounding row/column omitted'};path.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');count+=1
print('native overlap scores refreshed:',count)
