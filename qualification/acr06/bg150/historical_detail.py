#!/usr/bin/env python3
"""Physical proxies for historical PDF page 5 on actual product backgrounds."""
import json,subprocess,tempfile
from pathlib import Path
import numpy as np
import pikepdf,pypdfium2 as pdfium
from PIL import Image
from scipy import ndimage
from skimage.morphology import skeletonize
q=Path('/data/coding/scanweave/qualification'); root=q/'acr06/local/bg150'
source=pdfium.PdfDocument(str(q/'pdf_packaging/groups/historical-input.pdf'))[4].render(scale=300/72).to_pil().convert('L')
def bg(path):
 pdf=pikepdf.open(path); pg=pdf.pages[4]; imgs=[x for x in pg.Resources.XObject.values() if x.get('/Subtype')=='/Image']
 x=max(imgs,key=lambda z:int(z.Width)*int(z.Height))
 return pikepdf.PdfImage(x).as_pil_image().convert('L').resize(source.size,Image.Resampling.BICUBIC)
ims={'source':source,'default_background':bg(root/'dev/historical.pdf'),'150_background':bg(root/'metric/historical.pdf')}
results={}; arrays={}
for name,im in ims.items():
 a=np.asarray(im,dtype=np.float32); arrays[name]=a
 paper=ndimage.gaussian_filter(a,sigma=16); dark=paper-a>30
 labels,count=ndimage.label(dark); objects=ndimage.find_objects(labels); sizes=np.bincount(labels.ravel())
 heights=[s[0].stop-s[0].start for i,s in enumerate(objects,1) if s is not None and 6<=s[0].stop-s[0].start<=50 and 2<=s[1].stop-s[1].start<=40 and 5<=sizes[i]<=400]
 skel=skeletonize(dark); dist=ndimage.distance_transform_edt(dark)
 results[name]={'dark_pixels':int(dark.sum()),'median_component_height_300px':float(np.median(heights)) if heights else None,'component_count_for_height':len(heights),'median_skeleton_stroke_width_300px':float(2*np.median(dist[skel])) if skel.any() else None,'mean_dark_contrast':float((paper-a)[dark].mean()) if dark.any() else None}
 with tempfile.NamedTemporaryFile(suffix='.png') as f:
  im.save(f.name)
  boxes=subprocess.run(['tesseract',f.name,'-','--psm','3','-l','eng','makebox'],check=True,capture_output=True,text=True).stdout
 xheights=[]
 for line in boxes.splitlines():
  fields=line.split()
  if len(fields)>=5 and fields[0] in set('acemnorsuvwxz'):
   try: xheights.append(int(fields[4])-int(fields[2]))
   except ValueError: pass
 results[name]['ocr_lowercase_xheight_proxy_300px']={'median':float(np.median(xheights)) if xheights else None,'samples':len(xheights),'p25':float(np.percentile(xheights,25)) if xheights else None,'p75':float(np.percentile(xheights,75)) if xheights else None}
s=arrays['source']; p=ndimage.gaussian_filter(s,sigma=16); ink=p-s>30
near=ndimage.binary_dilation(ink,iterations=3)&~ink
for name in ('default_background','150_background'):
 results[name]['near_source_ink_mean_abs_error_vs_source']=float(np.abs(arrays[name]-s)[near].mean())
results['caveat']='The x-height proxy uses Tesseract boxes labeled as lower-case x-height letters; blackletter misrecognition can bias it. Components and skeletons are whole-page proxies; near-ink error includes resampling and registration, not JPEG ringing alone.'
(q/'acr06/bg150/historical-detail.json').write_text(json.dumps(results,indent=2)+'\n')
