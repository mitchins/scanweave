"""Uniform source-coordinate measurements on actual 2x PDFium renderings."""
import json,pathlib,sys
import numpy as np
from scipy import ndimage as ndi
from skimage import morphology
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
B=c.B;O=c.O;key='8967062';run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());source=json.loads(pathlib.Path('/tmp/scanweave-books01/qualification/books01/phase2/results.json').read_text())['pages'][run['id']]['rows'];target=c.CASES[key]['target'];dpi=run['dpi'];groups=c.get_groups(key,target)
paths={'source':run['rows']['src']['path'],'baseline':run['rows']['sw-E']['path'],'mrc':run['rows']['mrc-M']['path'],'adobe':str(B/'runs/adobe-p2/8967062.adobe.pdf')}; geom={'baseline':source['sw-E']['geometry'],'mrc':source['mrc-M']['geometry'],'adobe':source['adobe-E']['geometry']};images={}
for name,path in paths.items():images[name]=c.pdf_crop(path,key,target,dpi,2,geom.get(name))
for name in ['inverse12','local12','local_observed_low','inverse_layers']:
 pdf=c.pdfium.PdfDocument(str(O/'crops'/f'{key}-{name}.pdf'));images[name]=pdf[0].render(scale=dpi*2/72).to_pil().convert('RGB')
out={}
for name,im in images.items():
 a=c.st.rgb_luma(c.st.linear(np.asarray(im.convert('RGB'))));row=[]
 for x0,y0,x1,y1 in groups:
  v=a[(y0-target[1])*2:(y1-target[1])*2,(x0-target[0])*2:(x1-target[0])*2];paper=float(np.percentile(v,90));ink=float(np.percentile(v,10));
  score=[]
  for threshold in [.35,.5,.65]:
   m=(paper-v)>threshold*max(paper-ink,1e-6);_,cc=ndi.label(m,np.ones((3,3)));holes=ndi.binary_fill_holes(m)&~m;_,hh=ndi.label(holes);sk=morphology.skeletonize(m);nb=ndi.convolve(sk.astype(int),np.ones((3,3),int));w=ndi.distance_transform_edt(m)[sk];score.append({'threshold':threshold,'components':int(cc),'holes':int(hh),'terminals':int((sk&(nb==2)).sum()),'median_width_source_px':float(np.median(w)) if len(w) else None})
  row.append({'bbox':[x0,y0,x1,y1],'topology_by_relative_threshold':score})
 out[name]=row
(O/'actual-pdf-digit-metrics.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:[x['topology_by_relative_threshold'][1] for x in v] for k,v in out.items()},indent=2))
