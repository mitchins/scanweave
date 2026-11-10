#!/usr/bin/env python3
"""Time segmentation hypotheses over the frozen pages, excluding OCR/reference scoring."""
import io,json,pathlib,sys,time
import numpy as np,pikepdf
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');mode=sys.argv[1];W=np.array([.2126,.7152,.0722],np.float32);count=0;total=0;start=time.monotonic()
def upper(a):return np.partition(a,len(a)//2,axis=0)[len(a)//2]
def run(a):
 global count,total
 h,w=a.shape[:2];y=a.astype(np.float32)@W
 if mode=='tile_median_128':
  mask=np.zeros((h,w),bool)
  for yy in range(0,h,128):
   for xx in range(0,w,128):
    z=y[yy:yy+128,xx:xx+128];mask[yy:yy+128,xx:xx+128]=np.abs(z-np.median(z))>60
 else:
  if mode=='corner':p=upper(np.array([upper(a[yy:yy+6,xx:xx+6].reshape(-1,3)) for xx,yy in ((0,0),(w-6,0),(0,h-6),(w-6,h-6))]))
  else:
   mid=y[h//10:9*h//10,w//10:9*w//10];cl=a[h//10:9*h//10,w//10:9*w//10]
   if mode=='interior_median':p=upper(cl.reshape(-1,3))
   else:
    hist=np.bincount(np.minimum((mid/8).astype(int),31).ravel(),minlength=32);k=int(hist.argmax());pos=np.flatnonzero(hist>=mid.size*.02)
    if mode=='bright_mode' and len(pos):k=int(pos[-1])
    p=upper(cl[(mid>=k*8)&(mid<(k+1)*8)].reshape(-1,3))
  mask=np.abs(y-float(p@W))>60
 count+=1;total+=int(mask.sum())
for doc in ('historical','receipts','financial','mixed','forms'):
 for path in sorted((R/'local/ink33r/renders'/doc).glob('*-source.png')):run(np.asarray(Image.open(path).convert('RGB')))
for folder,truthfile in (('controls','controls-truth.json'),('controls-supplemental','supplemental-truth.json'),('positive-controls','positive-controls-truth.json')):
 for name in json.loads((R/'ink37'/truthfile).read_text())['cases']:
  path=R/'local/ink37'/folder/f'{name}.pdf'
  if not path.exists():continue
  pdf=pikepdf.open(path);obj=next(o for o in pdf.pages[0].Resources.XObject.values() if str(o.get('/Subtype'))=='/Image');a=np.asarray(Image.open(io.BytesIO(obj.read_raw_bytes())).convert('RGB'));pdf.close();run(a)
print(json.dumps({'mode':mode,'pages':count,'foreground_pixels':total,'wall_seconds_internal':time.monotonic()-start}),flush=True)
