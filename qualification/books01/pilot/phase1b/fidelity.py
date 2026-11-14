#!/usr/bin/env python3
"""Native plus globally aligned source-frame visual scores, without altering originals."""
import json,pathlib,time
import numpy as np
from PIL import Image,ImageDraw
from skimage.metrics import structural_similarity
from skimage.color import rgb2lab,deltaE_ciede2000
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[2];Q=P/'pilot';corpus=json.loads((P/'corpus.frozen.json').read_text());ids=corpus['pilot_6'];works={p['id']:p['work'] for p in corpus['pages']};locks=json.loads((P/'sources.lock.json').read_text())['pages'];geo=json.loads((Q/'results/phase1b/geometry.json').read_text())['pages'];native=json.loads((Q/'results/visual.json').read_text());ADOBE='Acrobat default OCR language (not matched); no Fraktur support; page straightened (deskew)'
def masks(id,size):
 key=id.split('/')[-1];g=json.loads((B/'gt'/works[id]/(key+'.json')).read_text());w,h=size;ow,oh=g['source_dimensions'];layers={k:Image.new('1',size) for k in ['text','illustration']}
 for r in g['regions']:
  kind=r['kind'];cat='text' if kind=='TextRegion' else 'illustration' if kind in ('GraphicRegion','ImageRegion','ChartRegion') else None
  if cat and len(r['polygon'])>=3:ImageDraw.Draw(layers[cat]).polygon([(round(x*w/ow),round(y*h/oh)) for x,y in r['polygon']],fill=1)
 t=np.asarray(layers['text'],dtype=bool);i=np.asarray(layers['illustration'],dtype=bool);return {'text':t&~i,'illustration':i,'paper':~(t|i)}
def L(rgb):
 x=rgb.astype(np.float32)/255.;x=np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4);y=x[:,:,0]*.2126729+x[:,:,1]*.7151522+x[:,:,2]*.0721750;return np.where(y>0.008856,116*np.cbrt(y)-16,903.3*y)
out={};start=time.monotonic()
for id in ids:
 key=id.split('/')[-1];out[id]={}
 for renderer in ['pdfium','poppler','mupdf']:
  for dpi in sorted({150,int(locks[id]['resolved_dpi'])}):
   source=B/'pilot/renders'/key/'src'/f'{renderer}-{dpi}.png';src=np.asarray(Image.open(source).convert('RGB')); ms=masks(id,(src.shape[1],src.shape[0]));sl=L(src);sg=np.asarray(Image.fromarray(src).convert('L'));si=sg<128
   for row in ['src','sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E']:
    g=geo[id][row][renderer][str(dpi)];entry={'registration_status':g['status'],'rotation_degrees':g['rotation_degrees'],'scale_x':g['scale_x'],'scale_y':g['scale_y'],'translation_px':g['translation_px'],'page_box_changed':g['page_box_changed'],'out_of_bounds_fraction':g['out_of_bounds_fraction'],'registration_residual_median_px_150_equivalent':g['residual_median_px_150_equivalent'],'registration_residual_p95_px_150_equivalent':g['residual_p95_px_150_equivalent'],'native':native[id][row][renderer][str(dpi)],'aligned':None,'adobe_label':ADOBE if row=='adobe-E' else None,'source_type':locks[id]['source_type'],'dpi_confidence':locks[id]['dpi_evidence']['confidence']}
    if g['status']=='accepted':
     path=B/g['aligned_render_path'];dst=np.asarray(Image.open(path).convert('RGB'));assert dst.shape==src.shape;dg=np.asarray(Image.fromarray(dst).convert('L'));di=dg<128;dl=np.abs(sl-L(dst));_,sm=structural_similarity(sg,dg,data_range=255,full=True);metrics={}
     for name,mask in ms.items():
      n=int(mask.sum());ink=int((si&mask).sum());pred=int((di&mask).sum());tp=int((si&di&mask).sum());delta=dl[mask];m={'pixels':n,'ssim':float(sm[mask].mean()) if n else None,'mean_abs_delta_L':float(delta.mean()) if n else None,'p95_abs_delta_L':float(np.percentile(delta,95)) if n else None,'ink_recall':tp/ink if ink else None,'ink_precision':tp/pred if pred else None,'spurious_ink_fraction':(pred-tp)/pred if pred else None}
      if name=='illustration' and n:
       a=src[mask];b=dst[mask];de=np.concatenate([deltaE_ciede2000(rgb2lab(a[o:o+200000].reshape(-1,1,3)),rgb2lab(b[o:o+200000].reshape(-1,1,3))).reshape(-1) for o in range(0,len(a),200000)]);m.update(deltaE2000_mean=float(de.mean()),deltaE2000_p95=float(np.percentile(de,95)))
      metrics[name]=m
     entry['aligned']={'regions':metrics,'binarization':'PIL grayscale <128','interpolation':g['interpolation']}
    out[id].setdefault(row,{}).setdefault(renderer,{})[str(dpi)]=entry
   print(key,renderer,dpi,flush=True)
(Q/'results/phase1b/fidelity.json').write_text(json.dumps({'elapsed_seconds':time.monotonic()-start,'pages':out},indent=2)+'\n')
