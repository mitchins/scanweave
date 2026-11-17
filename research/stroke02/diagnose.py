"""Reproduce stroke-width identifiability and measure source-only 613 geometry."""
import json,pathlib,sys,re
import numpy as np
from scipy.ndimage import gaussian_filter1d,distance_transform_edt,label
from skimage.morphology import skeletonize
from PIL import Image
from lxml import html
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'stroke01'))
import prototype as old
B=pathlib.Path('/data/coding/scanweave/work/books01');OUT=B/'stroke02';native=Image.open(OUT/'native/8967062-000.png').convert('RGB')
# Oversampled 1-D physical coverage: known width -> blurred observation; the
# max intensity is misinterpreted as solid ink by a centre-sample estimate.
examples=[]
for sigma in [.8,1.15]:
 for width in [2.,3.,4.,6.]:
  x=np.arange(-20,20,.02);a=(abs(x)<=width/2).astype(float);obs=gaussian_filter1d(a,sigma/.02);peak=float(obs.max());relative=obs/max(peak,1e-9);measured=float((relative>=.5).sum()*.02)
  examples.append({'sigma':sigma,'true_width_px':width,'peak_coverage':peak,'observed_relative_halfmax_width_px':measured,'percent_overwidth':100*(measured/width-1),'true_ink_integral_px':float(obs.sum()*.02)})
# OCR geometry is used only to group pixels into character-sized windows, not
# to infer a glyph shape or draw OCR characters.
h=html.parse(str(B/'phase2/runs/8967062/selected.hocr'));target=(1165,748,1236,791);words=[]
for w in h.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]'):
 for span in w:
  match=re.search(r'x_bboxes (\d+) (\d+) (\d+) (\d+)',span.get('title',''))
  if not match:continue
  x0,y0,x1,y1=map(int,match.groups())
  if 1175<=x0<=1222 and 758<=y0<=780 and x1<=1222 and y1<=784:words.append([x0,y0,x1,y1])
words=sorted(words,key=lambda b:b[0]);box=(1135,718,1266,821);rgb=np.asarray(native.crop(box));z=old.reconstruction(rgb,237.7876)
measurements=[]
for bb in words:
 x0,y0,x1,y1=bb;m=z['masks'][1][y0-box[1]:y1-box[1],x0-box[0]:x1-box[0]];dist=distance_transform_edt(m);sk=skeletonize(m);widths=2*dist[sk];_,components=label(m);measurements.append({'bbox':bb,'pixels':int(m.sum()),'components_4_connected':int(components),'observed_mask_skeleton_width_q25_median_q75_px':np.quantile(widths,[.25,.5,.75]).tolist() if widths.size else None})
out={'one_dimensional_sensitivity':examples,'613':{'image_dpi':500,'ocr_group_boxes':words,'group_metrics':measurements,'qualification':'mask-derived observed widths; neither true unblurred widths nor a fitted scanner PSF'}};(OUT/'diagnostics.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
