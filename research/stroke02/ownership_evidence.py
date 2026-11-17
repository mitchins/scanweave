"""Quantify local foreground evidence outside the stock ownership reference.

Uses only the authorized 8967062 dev page and the already generated sidecar.
Does not write or modify a converter input or output.
"""
import json,pathlib
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
B=pathlib.Path('/data/coding/scanweave/work/books01/stroke02')
rgb=np.asarray(Image.open(B/'native/8967062-000.png').convert('RGB'));lum=rgb@np.array([.2126,.7152,.0722]);paper=237.7876;fg=np.abs(lum-paper)>60
coverage=np.asarray(Image.open(B/'pages/8967062/coverage.png').convert('L'))/255
labels,n=ndi.label(fg,structure=np.ones((3,3),dtype=bool));profiles=json.loads((B/'joint-profiles.json').read_text())['8967062'];regions=[]
for i,r in enumerate(profiles):
 a,b,d,e=r['bbox'];original=fg[b:e,a:d];local=coverage[b:e,a:d]>=.5;added=local&~original;removed=original&~local;part=labels[b:e,a:d];ids=np.unique(part[original]);regions.append({'group_index':i,'bbox':r['bbox'],'original_ink_pixels':int(original.sum()),'candidate_local_mask_pixels':int(local.sum()),'candidate_added_pixels_outside_original_foreground':int(added.sum()),'original_pixels_excluded_by_candidate':int(removed.sum()),'original_foreground_components_intersecting_box':int(len(ids)),'added_pixels_with_original_component_label':int((part[added]>0).sum())})
out={'page':'finebooks/conchologiaiconi05reev/8967062','global_paper_luma':paper,'global_threshold':60,'candidate_mask':'existing STROKE-02 line-pooled sidecar, coverage >= 0.5; diagnostic only, not accepted as ground truth','source_global_components':int(n),'regions':regions,'finding':'build_plan creates component IDs only for original fg pixels; visual_invariant_ok checks IDs and counts, not unit masks; replacing a unit mask after planning cannot register added pixels in the existing ownership/contact references'}
pathlib.Path(__file__).with_name('ownership-evidence.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
