"""Compare registered actual PDF pixels after optimising one effective blur."""
import json, pathlib, sys
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
import pypdfium2 as pdfium
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
B,O=c.B,c.O
L=np.array([.2126,.7152,.0722]); sigmas=np.arange(0,1.501,.1)
results=json.loads(pathlib.Path('/tmp/scanweave-books01/qualification/books01/phase2/results.json').read_text())['pages']
profiles=json.loads((O/'joint-profiles.json').read_text()); generated=json.loads((O/'joint-render.json').read_text())
output={}
for key,conf in c.CASES.items():
 run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());dpi=run['dpi'];target=conf['target'];x0,y0,x1,y1=target;rows=results[run['id']]['rows'];h=y1-y0;w=x1-x0
 def source_pdf(path,geom=None):
  return np.asarray(c.pdf_crop(path,key,target,dpi,2,geom).convert('RGB'))[:h*2,:w*2]
 def linear_native(rgb):return c.st.linear(rgb).reshape(h,2,w,2,3).mean((1,3))@L
 source=linear_native(source_pdf(run['rows']['src']['path']))
 comparisons={}
 for name in ['sw-E','mrc-M','adobe-E']:
  if name=='adobe-E':
   paths=[B/'runs/adobe'/f'{key}.adobe.pdf',B/'runs/adobe-p2'/f'{key}.adobe.pdf'];path=next((p for p in paths if p.exists()),None)
  else:path=run['rows'][name]['path']
  geom=rows.get(name,{}).get('geometry')
  if path and geom and geom.get('status')=='accepted': comparisons[name]=linear_native(source_pdf(path,geom))
 for item in generated['runs'][key]:
  path=item['pdf'];name=pathlib.Path(path).stem.split('joint-')[-1];image=pdfium.PdfDocument(path)[0].render(scale=dpi*2/72).to_pil().convert('RGB');comparisons[name]=linear_native(np.asarray(image)[:h*2,:w*2])
 regionout=[]
 for region in profiles[key]:
  a,b,d,e=region['bbox'];ys=slice(max(0,b-y0),min(h,e-y0));xs=slice(max(0,a-x0),min(w,d-x0));rr={}
  for name,im in comparisons.items():
   errs=[float(np.sqrt(np.mean((ndi.gaussian_filter(im,s,mode='nearest')[ys,xs]-source[ys,xs])**2))) if s>0 else float(np.sqrt(np.mean((im[ys,xs]-source[ys,xs])**2))) for s in sigmas];j=int(np.argmin(errs));rr[name]={'min_rmse':errs[j],'sigma_eff':round(float(sigmas[j]),1),'rmse_zero':errs[0]}
  regionout.append({'bbox':region['bbox'],'results':rr})
 output[key]=regionout
(O/'fair-compare.json').write_text(json.dumps(output,indent=2))
for key,regions in output.items():
 for i,r in enumerate(regions):
  v=r['results'];print(key,i,[(k,round(x['min_rmse'],4),x['sigma_eff']) for k,x in v.items() if k in ('sw-E','mrc-M','adobe-E')], 'best candidate',min(((k,round(x['min_rmse'],4),x['sigma_eff']) for k,x in v.items() if k not in ('sw-E','mrc-M','adobe-E')),key=lambda x:x[1]))
