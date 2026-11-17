"""Isolate ink/PSF identifiability on known rendered outlines."""
import json,pathlib,sys,statistics
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy import ndimage as ndi
from skimage import morphology
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
st=c.st;rng=np.random.default_rng(20261117);rows=[]
for font in st.FONTS:
 for glyph in ['6','3','e','i','rn']:
  for sigma in [.8,1.2]:
   fs=40;size=(120,80);canvas=Image.new('L',(size[0]*4,size[1]*4),0);ImageDraw.Draw(canvas).text((fs*2,fs*2),glyph,font=ImageFont.truetype(font,fs*4),fill=255);clean=np.asarray(canvas.resize(size,Image.Resampling.LANCZOS),float)/255;gt=clean>=.5
   # Known B and K; variation deliberately limited to blur + noise to isolate
   # stroke-weight bias, not to claim general real-scan performance.
   observed=np.clip(ndi.gaussian_filter(clean,sigma)+rng.normal(0,.005,clean.shape),0,1)
   variants={'oracle':observed,'centre':np.clip(observed/max(np.percentile(observed,99.9),.01),0,1)}
   for assumption,alpha in variants.items():
    for steps in [0,12,60]:
     latent=c.bounded_inverse(alpha,sigma,steps);mask=latent>=.5;s=st.scores(gt,mask)
     def width(m):
      sk=morphology.skeletonize(m);w=2*ndi.distance_transform_edt(m)[sk];return float(np.median(w)) if w.size else None
     tw=width(gt);pw=width(mask);rows.append({'assumption':assumption,'steps':steps,'f1':s['boundary_f1'],'missing':s['missing_fraction'],'false':s['false_ink_fraction'],'topology_match':s['gt_topology']==s['topology'],'joins':s['false_joins'],'width_ratio':pw/tw if pw and tw else None})
out={'cases':len(rows)//6,'methods':{}}
for assumption in ['oracle','centre']:
 for steps in [0,12,60]:
  subset=[r for r in rows if r['assumption']==assumption and r['steps']==steps];out['methods'][f'{assumption}-{steps}']={'mean_boundary_f1':statistics.mean(r['f1'] for r in subset),'mean_missing':statistics.mean(r['missing'] for r in subset),'mean_false':statistics.mean(r['false'] for r in subset),'topology_match':sum(r['topology_match'] for r in subset),'false_joins':sum(r['joins'] for r in subset),'median_width_ratio':statistics.median(r['width_ratio'] for r in subset if r['width_ratio'] is not None)}
(c.O/'synthetic-physics.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
