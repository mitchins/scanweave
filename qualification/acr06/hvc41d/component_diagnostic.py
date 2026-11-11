"""Development-only connected-component guard and explicit punctuation perturbations."""
import pathlib,json,numpy as np
from PIL import Image
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41d';data=json.loads((E/'calibration-exploratory.json').read_text());rows=data['rows'];n=data['negative_examples'];structure=np.ones((3,3),bool)
def masks(r):
 a=np.asarray(Image.open(r['panel']).convert('L'))[::4,::4];cw=a.shape[1]//4;x0,y0,x1,y1=map(int,r['ocr_box']);w=x1-x0+6;h=y1-y0+6;return np.pad(a[20:20+h,2*cw:2*cw+w]>128,8),np.pad(a[20:20+h,3*cw:3*cw+w]>128,8)
def comp(a,b):
 for x,y in ((a,b),(b,a)):
  labs,count=nd.label(x,structure=structure); near=nd.binary_dilation(y,structure=structure)
  for j in range(1,count+1):
   part=labs==j
   if part.sum()>=3 and (part&near).sum()/part.sum()<.8:return False
 return True
def score(a,b):
 st=nd.generate_binary_structure(2,1);return min((a&nd.binary_dilation(b,structure=st)).sum()/a.sum(),(b&nd.binary_dilation(a,structure=st)).sum()/b.sum()),b.sum()/a.sum()
out=[]
for i,r in enumerate(rows):
 a,b=masks(r);base=comp(a,b); ys,xs=np.nonzero(b); x=min(b.shape[1]-3,int(xs.max())+4);y=min(b.shape[0]-3,int(ys.max())+4); added=b.copy();added[y:y+2,x:x+2]=1
 lab,num=nd.label(b,structure=structure);parts=[(int((lab==j).sum()),j) for j in range(1,num+1) if 3<=int((lab==j).sum())];parts.sort();dropped=None
 if len(parts)>1 and parts[0][0]<=parts[-1][0]*.4:dropped=b.copy();dropped[lab==parts[0][1]]=0
 sa,ar=score(a,added);drop=score(a,dropped) if dropped is not None and dropped.any() else None
 out.append({'index':i,'base':base,'added_pass_component':comp(a,added),'added_score':sa,'added_area':ar,'dropped_pass_component':comp(a,dropped) if dropped is not None else None,'dropped_score':drop[0] if drop else None,'dropped_area':drop[1] if drop else None,'drop_pixels':parts[0][0] if dropped is not None else None})
(E/'component-diagnostic.json').write_text(json.dumps(out,indent=2,default=lambda x:x.item())+'\n');print('base passes',sum(r['base'] for r in out),'/',len(out),'added rejected',sum(not r['added_pass_component'] for r in out),'/',len(out));dd=[r for r in out if r['dropped_pass_component'] is not None];print('dropped rejected',sum(not r['dropped_pass_component'] for r in dd),'/',len(dd))
