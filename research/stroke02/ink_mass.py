"""Ink-mass sensitivity to two explicitly unverified source-colour hypotheses."""
import json,pathlib,sys
import numpy as np
from PIL import Image
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
key='8967062';native=Image.open(c.O/'native/8967062-000.png').convert('RGB');bounds=c.CASES[key]['context'];cx0,cy0,_,_=bounds;rgb=np.asarray(native.crop(bounds));model=c.st.reconstruction(rgb,237.8);head=c.st.reconstruction(np.asarray(native.crop((1570,190,2035,255))),237.8);obs=c.st.linear(rgb);bg=model['background'];groups=c.get_groups(key,c.CASES[key]['target']);out={'heading_roi':[1570,190,2035,255],'heading_ink_rgb':head['ink_rgb'],'assumptions':{},'warning':'heading ink equivalence is unverified; values are projected coverage mass, not true stroke area'}
for name,ink in [('local',model['ink']),('heading',c.st.linear(np.array(head['ink_rgb'])) )]:
 d=bg-ink;alpha=np.clip(((bg-obs)*d).sum(-1)/np.maximum((d*d).sum(-1),1e-8),0,1);out['assumptions'][name]=[float(alpha[y0-cy0:y1-cy0,x0-cx0:x1-cx0].sum()) for x0,y0,x1,y1 in groups]
(c.O/'ink-mass.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
