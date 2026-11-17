"""Cross-hypothesis stability of crop PDF glyphs; declines on disagreement."""
import json,pathlib,sys,itertools
import numpy as np
from scipy import ndimage as ndi
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
B=c.B;O=c.O;key='8967062';run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());target=c.CASES[key]['target'];dpi=run['dpi'];groups=c.get_groups(key,target)
names=['inverse12','inverse60_softpsf','local12','mixed12_smooth','inverse_layers'];images={}
for name in names:
 doc=c.pdfium.PdfDocument(str(O/'crops'/f'{key}-{name}.pdf'));images[name]=c.st.rgb_luma(c.st.linear(np.asarray(doc[0].render(scale=dpi*2/72).to_pil().convert('RGB'))))
out=[]
for x0,y0,x1,y1 in groups:
 masks={}; signatures={}
 for name,img in images.items():
  v=img[(y0-target[1])*2:(y1-target[1])*2,(x0-target[0])*2:(x1-target[0])*2];paper=float(np.percentile(v,90));ink=float(np.percentile(v,10));m=(paper-v)>.5*max(paper-ink,1e-6);masks[name]=m;_,cc=ndi.label(m,np.ones((3,3)));_,hh=ndi.label(ndi.binary_fill_holes(m)&~m);signatures[name]=[int(cc),int(hh)]
 ious=[];edges=[]
 for a,b in itertools.combinations(names,2):
  m=masks[a];n=masks[b];ious.append(float((m&n).sum()/max((m|n).sum(),1)));e=m^ndi.binary_erosion(m);f=n^ndi.binary_erosion(n);d=ndi.distance_transform_edt(~f);edges.append(float(np.percentile(d[e],95)/2) if e.any() and f.any() else None)
 stable=len({tuple(x) for x in signatures.values()})==1 and min(ious)>=.9 and max(x for x in edges if x is not None)<=.5
 out.append({'bbox':[x0,y0,x1,y1],'shape_signatures':signatures,'pairwise_iou_min':min(ious),'pairwise_iou_median':float(np.median(ious)),'edge_distance_p95_max_source_px':max(x for x in edges if x is not None),'accept':bool(stable)})
(O/'ambiguity.json').write_text(json.dumps({'hypotheses':names,'groups':out},indent=2));print(json.dumps(out,indent=2))
