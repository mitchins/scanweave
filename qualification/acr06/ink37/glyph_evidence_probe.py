from pathlib import Path
from PIL import Image
import numpy as np, json, math
root=Path('/data/coding/scanweave/qualification/acr06')
rows=[]
for doc in ('historical','financial','mixed','receipts','forms'):
  for path in sorted((root/'local/ink33/maps'/doc).glob('*.json')):
    obj=json.loads(path.read_text()); page=int(path.stem)
    a=np.asarray(Image.open(root/'local/ink33/renders'/doc/(path.stem+'-source.png')).convert('RGB'))
    l=a[:,:,0]*.2126+a[:,:,1]*.7152+a[:,:,2]*.0722
    n=0; bad=0; ambiguous=0
    for g in obj['scan_objects']:
      x0,y0,x1,y1=g['box']; pad=3
      x0=max(0,math.floor(x0)-pad); y0=max(0,math.floor(y0)-pad); x1=min(a.shape[1],math.ceil(x1)+pad); y1=min(a.shape[0],math.ceil(y1)+pad)
      if x1<=x0 or y1<=y0: continue
      crop=l[y0:y1,x0:x1]; hist=np.histogram(crop,bins=np.arange(257))[0]; bg=int(np.argmax(np.convolve(hist,np.ones(9),mode='same')))
      low,high=np.percentile(crop,[10,90]); ink=float(np.dot(g['rgba'][:3],[.2126,.7152,.0722])); n+=1
      if abs(ink-bg)<15: bad+=1
      elif ink<bg and abs(ink-low)>45 or ink>bg and abs(ink-high)>45: ambiguous+=1
    rows.append({'document':doc,'page':page,'visible_objects':n,'fill_near_local_mode':bad,'fill_far_from_local_extreme':ambiguous})
(root/'ink37/glyph-evidence-probe.json').write_text(json.dumps(rows,indent=2)+'\n')
