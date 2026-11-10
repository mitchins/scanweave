import pathlib,json,numpy as np
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41b';L=R/'local';p=3;d=json.loads((L/'hvc41/contact/interior/historical/p000003.json').read_text());units={x['symbol']:x for x in d['units']};actual=json.loads((L/'hvc41b/border/p000003-outlines.json').read_text());ledger={x['symbol']:x for x in json.loads((E/'admission-ledger-03.json').read_text())};src=np.asarray(Image.open(L/'ink33r/renders/historical/03-source.png').convert('RGB'));h,w=src.shape[:2];weights=np.array([.2126,.7152,.0722]);lum=src@weights;samples=[]
for glyph in actual['outlines']:
 u=units[glyph['symbol']];entry=ledger[glyph['symbol']];ii=np.asarray(u['mask_indices'],dtype=np.int64);x=int(u['bbox'][0])+ii%u['crop_w'];y=int(u['bbox'][1])+ii//u['crop_w'];good=(x>=0)&(x<w)&(y>=0)&(y<h);x=x[good];y=y[good];selected=np.zeros(len(x),bool)
 for ck in entry['region_checks']:
  if 'bbox' not in ck:continue
  x0,y0,x1,y1=map(int,ck['bbox']);q=lum[max(0,y0):min(h,y1),max(0,x0):min(w,x1)]
  if not q.size:continue
  selected|=(x>=x0)&(x<x1)&(y>=y0)&(y<y1)&(lum[y,x]<np.percentile(q,85)-30)
 if selected.any():samples.append(src[y[selected],x[selected]])
samples=np.concatenate(samples);ink=np.median(samples,axis=0).astype(int).tolist();obj={'page':3,'source_text_ink_rgb':ink,'sample_count':len(samples),'global_ink_rgb':actual['ink'],'method':'Per-channel median of source RGB at owned-unit mask pixels inside source OCR boxes, >30 luminance darker than box p85; artwork components excluded. Diagnostic only; independently frozen admission fails.'};(E/'p3-source-ink.json').write_text(json.dumps(obj,indent=2)+'\n');print(obj)
