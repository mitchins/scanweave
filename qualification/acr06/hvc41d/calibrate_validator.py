"""Calibrate without looking at historical p1, using reviewed completed control glyphs."""
import sys,json,pathlib,collections,hashlib
import numpy as np
from PIL import Image
from scipy import ndimage as nd
sys.path.insert(0,str(pathlib.Path(__file__).parent));from validator import metrics
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41d';L=R/'local/hvc41d';rows=json.loads((E/'calibration-exploratory.json').read_text())['rows']
# Human review of sheets 01–09: the excluded OCR assignments are either a multi-character
# object, a clipped/ambiguous mark, or have uncertain source identity.
ids=[i for i in range(143) if i not in (17,53,58,67)] + [207,208]; masks=[]
for r in rows:
 image=np.asarray(Image.open(r['panel']).convert('L'))[::4,::4];cw=image.shape[1]//4;x0,y0,x1,y1=map(int,r['ocr_box']);w=x1-x0+6;h=y1-y0+6;masks.append((np.pad(image[20:20+h,2*cw:2*cw+w]>128,8),np.pad(image[20:20+h,3*cw:3*cw+w]>128,8)))
def shift(a,dy,dx):
 out=np.zeros_like(a);h,w=a.shape;y0=max(dy,0);y1=min(h,h+dy);x0=max(dx,0);x1=min(w,w+dx);out[y0:y1,x0:x1]=a[y0-dy:y1-dy,x0-dx:x1-dx];return out
def scale(a,f):
 h,w=a.shape;m=np.asarray(Image.fromarray(a).resize((round(w*f),round(h*f)),Image.Resampling.NEAREST));o=np.zeros_like(a);sy=max(0,(m.shape[0]-h)//2);sx=max(0,(m.shape[1]-w)//2);dy=max(0,(h-m.shape[0])//2);dx=max(0,(w-m.shape[1])//2);hh=min(h,m.shape[0]);ww=min(w,m.shape[1]);o[dy:dy+hh,dx:dx+ww]=m[sy:sy+hh,sx:sx+ww];return o
def place_center(a,shape):
 out=np.zeros(shape,bool);yy,xx=np.nonzero(a)
 if not len(yy):return out
 ay0,ay1=yy.min(),yy.max()+1;ax0,ax1=xx.min(),xx.max()+1;crop=a[ay0:ay1,ax0:ax1];dy=(shape[0]-crop.shape[0])//2;dx=(shape[1]-crop.shape[1])//2
 if dy<0 or dx<0:return None
 out[dy:dy+crop.shape[0],dx:dx+crop.shape[1]]=crop;return out
pos=[];neg=collections.defaultdict(list)
for i in ids:
 r=rows[i];a,b=masks[i];p=metrics(a,b,r['fill_luminance_error']);pos.append({'index':i,'control':r['control'],'char':r['char_ocr_unverified'],'visual_identity':'reviewed against source and font sheet','panel':r['panel'],'panel_sha256':r['panel_sha256'],'metrics':p})
 for dy,dx in [(0,2),(0,-2),(2,0),(-2,0)]:neg['shift_2'].append({'index':i,'shift':[dy,dx],'metrics':metrics(a,shift(b,dy,dx),r['fill_luminance_error'])})
 for f in (.85,1.15):neg['scale_'+str(f)].append({'index':i,'metrics':metrics(a,scale(b,f),r['fill_luminance_error'])})
 hole=nd.binary_fill_holes(b)&~b
 if hole.sum()>=2:neg['filled_counter'].append({'index':i,'hole_pixels':int(hole.sum()),'metrics':metrics(a,b|hole,r['fill_luminance_error'])})
 neg['fill_error_16'].append({'index':i,'metrics':metrics(a,b,16.0)})
 ys,xs=np.nonzero(b);x=min(b.shape[1]-3,int(xs.max())+4);y=min(b.shape[0]-3,int(ys.max())+4);added=b.copy();added[y:y+2,x:x+2]=1;neg['added_punctuation'].append({'index':i,'metrics':metrics(a,added,r['fill_luminance_error'])})
 if r['char_ocr_unverified'] in ('i','j',':',';','!'):
  labels,num=nd.label(b,structure=np.ones((3,3),bool));parts=sorted((int((labels==j).sum()),j) for j in range(1,num+1) if (labels==j).sum()>=3)
  if len(parts)>1:
   dropped=b.copy();dropped[labels==parts[0][1]]=0;neg['dropped_punctuation'].append({'index':i,'metrics':metrics(a,dropped,r['fill_luminance_error'])})
# Character substitution uses reviewed, different source characters, in the target canvas,
# centre aligned without resizing. It does not depend on an OCR prediction to accept a glyph.
for pair in [('c','e'),('n','h'),('l','1')]:
 left=[i for i in ids if rows[i]['char_ocr_unverified']==pair[0]];right=[i for i in ids if rows[i]['char_ocr_unverified']==pair[1]]
 for i in left:
  for j in right:
   if rows[i]['control']!=rows[j]['control']:continue
   _,b=masks[i];src=place_center(masks[j][0],b.shape)
   if src is None:continue
   # font and reference centred independently by ink bbox; no scaling
   bb=place_center(b,b.shape)
   neg['substitution'].append({'index':i,'source_index':j,'pair':pair,'metrics':metrics(src,bb,rows[i]['fill_luminance_error'])})
summary={'positives':{'total':len(pos),'passed':sum(x['metrics']['pass'] for x in pos)},'negative':{k:{'total':len(v),'rejected':sum(not x['metrics']['pass'] for x in v),'survived':[x for x in v if x['metrics']['pass']][:20]} for k,v in neg.items()}}
(E/'validator-positives.json').write_text(json.dumps(pos,indent=2,ensure_ascii=False)+'\n');(E/'validator-negatives.json').write_text(json.dumps(neg,indent=2,ensure_ascii=False)+'\n');(E/'validator-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
