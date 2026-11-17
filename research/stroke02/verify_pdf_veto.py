"""PDFium coverage check for experimental paper vetoes, with fail-closed retry.

The text-only diagnostic retains the trial PDF's exact text operators/fonts,
changes fills to black and suppresses background graphics. It is not a user PDF.
"""
import json,pathlib,math
import numpy as np
import pikepdf,pypdfium2 as pdfium
from PIL import Image
from scipy import ndimage as ndi

def verify(directory,dpi):
 directory=pathlib.Path(directory);ledger=json.loads((directory/'extensions.json').read_text());pre=json.loads((directory/'prepass.json').read_text());veto=np.asarray(Image.open(directory/'paper-veto.png').convert('L'))>0
 targets=[x for x in ledger['decisions'] if x['decision']=='accepted'];checks=[];blocked=[]
 if not targets or not veto.any():return {'checks':checks,'blocked':blocked}
 pdf=pikepdf.Pdf.open(directory/'candidate.pdf');page=pdf.pages[0];ops=pikepdf.parse_content_stream(page);kept=[];inside=False
 for ins in ops:
  op=str(ins.operator)
  if op=='BT':inside=True
  if inside:
   if op=='rg':ins=pikepdf.ContentStreamInstruction([0,0,0],pikepdf.Operator('rg'))
   kept.append(ins)
  if op=='ET':inside=False
 if not kept:raise RuntimeError('PDF text stream missing; cannot verify veto')
 page.Contents=pdf.make_stream(pikepdf.unparse_content_stream(kept));diagnostic=directory/'veto-text-only.pdf';pdf.save(diagnostic);pdf.close()
 doc=pdfium.PdfDocument(str(diagnostic));pg=doc[0];height,width=veto.shape;page_w,page_h=pg.get_size();sx=page_w/width;sy=page_h/height
 for unit in targets:
  a,b,c,d=map(int,unit['bbox']);cx=(a+c)/2;cy=(b+d)/2;lines=[x for x in pre['lines'] if x['bbox'][0]<=cx<x['bbox'][2] and x['bbox'][1]<=cy<x['bbox'][3]]
  if not lines:
   blocked.append(unit['symbol_id']);checks.append({'symbol_id':unit['symbol_id'],'reason':'missing_noise_metadata'});continue
  line=min(lines,key=lambda x:(x['bbox'][2]-x['bbox'][0])*(x['bbox'][3]-x['bbox'][1]));sigma=float(line['sigma']);noise=float(line['noise_proxy']);pad=math.ceil(4*sigma)+2
  x0=max(0,a-pad);x1=min(width,c+pad);y0=max(0,b-pad);y1=min(height,d+pad);v=veto[y0:y1,x0:x1]
  if not v.any():continue
  scale=dpi*4/72;full_w=math.ceil(page_w*scale);full_h=math.ceil(page_h*scale)
  px0=max(0,math.floor(x0*full_w/width));px1=min(full_w,math.ceil(x1*full_w/width));py0=max(0,math.floor(y0*full_h/height));py1=min(full_h,math.ceil(y1*full_h/height))
  # PDFium quantises each crop edge upward independently. Request integer
  # device-pixel edges with a tiny negative epsilon, then map pixel centres
  # through the exact full-page dimensions PDFium uses.
  cv=lambda n:max(0.,n/scale-1e-8)
  crop=(cv(px0),cv(full_h-py1),cv(full_w-px1),cv(py0))
  im=pg.render(scale=scale,crop=crop,grayscale=True).to_pil().convert('L');pixels=np.asarray(im,dtype=float);expected=(py1-py0,px1-px0)
  if pixels.shape!=expected or not np.isfinite(noise) or noise<=0:
   blocked.append(unit['symbol_id']);checks.append({'symbol_id':unit['symbol_id'],'reason':'render_geometry_or_noise_unavailable','shape':list(pixels.shape),'expected':list(expected)});continue
  ys=np.clip(((np.arange(py0,py1)+.5)*height/full_h).astype(int),0,height-1);xs=np.clip(((np.arange(px0,px1)+.5)*width/full_w).astype(int),0,width-1);vv=veto[np.ix_(ys,xs)]
  if not vv.any():continue
  cov=1-pixels/255.;sim=ndi.gaussian_filter(cov,sigma*(full_w/width),mode='constant');direct=float(cov[vv].max());forward=float(sim[vv].max())
  # Assume maximum possible ink contrast (1.0 linear luminance), a conservative
  # upper bound. The single glyph layer gets the whole local noise allowance.
  ok=direct<=noise and forward<=noise
  if not ok:blocked.append(unit['symbol_id'])
  checks.append({'symbol_id':unit['symbol_id'],'veto_pixels':int(v.sum()),'sigma':sigma,'noise_limit':noise,'direct_coverage_max':direct,'reblurred_contrast_upper_bound':forward,'passed':ok})
 return {'checks':checks,'blocked':blocked}
