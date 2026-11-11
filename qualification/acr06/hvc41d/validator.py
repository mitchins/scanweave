"""Development control validator, source-pixel coordinates. No registration search."""
import numpy as np
from scipy import ndimage as nd
CROSS=nd.generate_binary_structure(2,1); EIGHT=np.ones((3,3),dtype=bool)
def metrics(source,rendered,fill_error):
 source=np.asarray(source,dtype=bool);rendered=np.asarray(rendered,dtype=bool)
 if source.shape!=rendered.shape or not source.any() or not rendered.any():return {'pass':False,'reason':'empty_or_misaligned'}
 tolerance=min(float((source&nd.binary_dilation(rendered,structure=CROSS)).sum()/source.sum()),float((rendered&nd.binary_dilation(source,structure=CROSS)).sum()/rendered.sum()))
 area=float(rendered.sum()/source.sum()); centroid=float(np.linalg.norm(np.array(nd.center_of_mass(source))-np.array(nd.center_of_mass(rendered)))); holes_ok=True
 ah=nd.binary_fill_holes(source)&~source;bh=nd.binary_fill_holes(rendered)&~rendered
 for u,v in ((ah,bh),(bh,ah)):
  labels,n=nd.label(u)
  for j in range(1,n+1):
   component=labels==j
   if component.sum()>=2 and not (nd.binary_dilation(component)&v).any():holes_ok=False
 components_ok=True
 for u,v in ((source,rendered),(rendered,source)):
  labels,n=nd.label(u,structure=EIGHT);near=nd.binary_dilation(v,structure=EIGHT)
  for j in range(1,n+1):
   component=labels==j
   if component.sum()>=3 and (component&near).sum()/component.sum()<.8:components_ok=False
 ok=tolerance>=.93 and centroid<=1.0 and .91<=area<=1.2 and fill_error is not None and fill_error<=15 and holes_ok and components_ok
 return {'pass':bool(ok),'tolerance':tolerance,'area_ratio':area,'centroid_offset':centroid,'fill_error':fill_error,'holes_ok':holes_ok,'components_ok':components_ok}
