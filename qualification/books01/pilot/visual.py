#!/usr/bin/env python3
"""Full-resolution region metrics against the matching renderer's source PDF."""
import json,os,pathlib,time
import numpy as np
from PIL import Image,ImageDraw
from skimage.metrics import structural_similarity
from skimage.color import rgb2lab,deltaE_ciede2000
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot';corpus=json.loads((P/'corpus.frozen.json').read_text());ids=corpus['pilot_6'];works={p['id']:p['work'] for p in corpus['pages']};locks=json.loads((P/'sources.lock.json').read_text())['pages']; renders=json.loads((Q/'results/render-costs.json').read_text())
def masks(id,size):
 key=id.split('/')[-1];g=json.loads((B/'gt'/works[id]/(key+'.json')).read_text());w,h=size;ow,oh=g['source_dimensions'];sx=w/ow;sy=h/oh; layers={k:Image.new('1',size) for k in ['text','illustration']}
 for r in g['regions']:
  typ=r['kind'];cl='text' if typ=='TextRegion' else 'illustration' if typ in ('GraphicRegion','ImageRegion','ChartRegion') else None
  if cl and len(r['polygon'])>=3:ImageDraw.Draw(layers[cl]).polygon([(round(x*sx),round(y*sy)) for x,y in r['polygon']],fill=1)
 text=np.asarray(layers['text'],dtype=bool);ill=np.asarray(layers['illustration'],dtype=bool);return {'text':text & ~ill,'illustration':ill,'paper':~(text|ill)}
def luminance(rgb):
 x=rgb.astype(np.float32)/255.;x=np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4); y=x[:,:,0]*.2126729+x[:,:,1]*.7151522+x[:,:,2]*.0721750;return np.where(y>0.008856,116*np.cbrt(y)-16,903.3*y)
only_poppler=os.environ.get('BOOKS01_VISUAL_ONLY')=='poppler'; prior=Q/'results/visual.json';result=json.loads(prior.read_text()) if only_poppler and prior.exists() else {}
for id in ids:
 key=id.split('/')[-1];result.setdefault(id,{})
 for renderer in ['pdfium','poppler','mupdf']:
  if only_poppler and renderer!='poppler':continue
  for dpi in sorted({150,int(locks[id]['resolved_dpi'])}):
   source=B/'pilot/renders'/key/'src'/(renderer+'-'+str(dpi)+'.png')
   if not source.exists():continue
   with Image.open(source) as im:src=np.asarray(im.convert('RGB'))
   ms=masks(id,(src.shape[1],src.shape[0])); sl=luminance(src);sg=np.asarray(Image.fromarray(src).convert('L'));si=sg<128
   for row in ['src','sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E']:
    path=B/'pilot/renders'/key/row/(renderer+'-'+str(dpi)+'.png');result[id].setdefault(row,{}).setdefault(renderer,{})
    if not path.exists():result[id][row][renderer][str(dpi)]={'status':'missing'};continue
    with Image.open(path) as im:dst=np.asarray(im.convert('RGB'))
    if abs(src.shape[0]-dst.shape[0])>1 or abs(src.shape[1]-dst.shape[1])>1:result[id][row][renderer][str(dpi)]={'status':'dimension_mismatch','source':list(src.shape),'output':list(dst.shape)};continue
    hh=min(src.shape[0],dst.shape[0]);ww=min(src.shape[1],dst.shape[1]); source_size=list(src.shape); output_size=list(dst.shape); a_src=src[:hh,:ww];dst=dst[:hh,:ww]; sgray=sg[:hh,:ww];sink=si[:hh,:ww]; slab=sl[:hh,:ww]
    dg=np.asarray(Image.fromarray(dst).convert('L'));di=dg<128; dl=np.abs(slab-luminance(dst)); _,smap=structural_similarity(sgray,dg,data_range=255,full=True); metrics={}
    for name,mask in ms.items():
     mask=mask[:hh,:ww]
     count=int(mask.sum()); ink=int((sink&mask).sum()); pred=int((di&mask).sum()); tp=int((sink&di&mask).sum()); delta=dl[mask];record={'pixels':count,'ssim':float(smap[mask].mean()) if count else None,'mean_abs_delta_L':float(delta.mean()) if count else None,'p95_abs_delta_L':float(np.percentile(delta,95)) if count else None,'ink_recall':tp/ink if ink else None,'ink_precision':tp/pred if pred else None,'spurious_ink_fraction':(pred-tp)/pred if pred else None}
     if name=='illustration' and count:
      a=a_src[mask];b=dst[mask]; vals=[]
      for off in range(0,len(a),250000):vals.append(deltaE_ciede2000(rgb2lab(a[off:off+250000].reshape(-1,1,3)),rgb2lab(b[off:off+250000].reshape(-1,1,3))).reshape(-1))
      de=np.concatenate(vals);record['deltaE2000_mean']=float(de.mean());record['deltaE2000_p95']=float(np.percentile(de,95))
     metrics[name]=record
    result[id][row][renderer][str(dpi)]={'status':'ok','threshold':'PIL grayscale <128','dpi_confidence':locks[id]['dpi_evidence']['confidence'],'source_dimensions':source_size,'output_dimensions':output_size,'overlap_dimensions':[hh,ww],'overlap_policy':'compare common top-left pixel grid; at most one rounding row/column omitted','regions':metrics};print(key,row,renderer,dpi,flush=True)
(Q/'results/visual.json').write_text(json.dumps(result,indent=2)+'\n')
