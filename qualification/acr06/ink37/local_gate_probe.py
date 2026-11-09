from pathlib import Path
from PIL import Image
import numpy as np,json,math
base=Path('/data/coding/scanweave/qualification/acr06'); result=[]
for doc in ('historical','financial','mixed','receipts','forms'):
 for f in sorted((base/'local/ink33/maps'/doc).glob('*.json')):
  j=json.loads(f.read_text()); a=np.asarray(Image.open(base/'local/ink33/renders'/doc/(f.stem+'-source.png')).convert('RGB'))
  bad=[]
  for i,o in enumerate(j['scan_objects']):
   x0,y0,x1,y1=o['box']; x0=max(0,math.floor(x0)-3); y0=max(0,math.floor(y0)-3); x1=min(a.shape[1],math.ceil(x1)+3); y1=min(a.shape[0],math.ceil(y1)+3)
   if x1<=x0 or y1<=y0:continue
   crop=a[y0:y1,x0:x1].astype(int); ink=np.array(o['rgba'][:3]); lum=crop@np.array([.2126,.7152,.0722]); ink_l=ink@np.array([.2126,.7152,.0722]); hist=np.bincount(np.clip(lum.astype(int),0,255).ravel(),minlength=256); mode=int(np.convolve(hist,np.ones(9),mode='same').argmax()); matched=int(np.all(np.abs(crop-ink)<=30,axis=2).sum()); total=lum.size
   if matched<2 or matched*50<total or abs(ink_l-mode)<15:bad.append({'object':i,'box':o['box'],'matched':matched,'total':total,'ink_lum':float(ink_l),'local_mode':mode})
  result.append({'document':doc,'page':int(f.stem),'objects':len(j['scan_objects']),'unsupported':len(bad),'examples':bad[:5]})
(base/'ink37/local-gate-probe.json').write_text(json.dumps(result,indent=2)+'\n')
