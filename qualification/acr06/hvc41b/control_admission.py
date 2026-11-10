import pathlib,json,sys,io,numpy as np,pikepdf
from PIL import Image
sys.path.insert(0,'/data/coding/scanweave/qualification/acr06/ink33r')
from prepare import chars_from_hocr
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/ink37';E=R/'hvc41b';allrows=json.loads((R/'hvc41/estimator-measurements.json').read_text());wts=np.array([.2126,.7152,.0722]);out=[]
for group,folder,reported,truthname in [('control','controls','control-measured','controls-truth.json'),('supplemental','controls-supplemental','control-supplemental-measured','supplemental-truth.json'),('positive','positive-controls','control-positive-measured','positive-controls-truth.json')]:
 truth=json.loads((R/'ink37'/truthname).read_text())
 for name in truth['cases']:
  report=json.loads((L/reported/f'{name}.pdf.json').read_text());pdf=pikepdf.open(L/folder/f'{name}.pdf');obj=next(o for o in pdf.pages[0].Resources.XObject.values() if str(o.get('/Subtype'))=='/Image');a=np.asarray(Image.open(io.BytesIO(obj.read_raw_bytes())).convert('RGB'));pdf.close();lum=a.astype(float)@wts;h,w=lum.shape;row=next(x for x in allrows if x['set']==group and x['document']==name);paper=float(np.array(row['estimators']['interior_mode']['paper_rgb'])@wts);words=[word for line in chars_from_hocr(report['pages'][0]['hocr']) for word in line['words']];accept=0;count=0
  for word in words:
   checks=[]
   for c in word['chars']:
    x0,y0,x1,y1=map(int,c['box']);x0=max(0,x0);y0=max(0,y0);x1=min(w,x1);y1=min(h,y1)
    if x1-x0<2 or y1-y0<2:checks.append(False);continue
    q=lum[y0:y1,x0:x1];p15,p85=np.percentile(q,[15,85]);dark=q<p85-30;edge=np.concatenate([q[0,:],q[-1,:],q[:,0],q[:,-1]]);checks.append(.05<=float(dark.mean())<=.45 and p85-p15>=60 and float((np.abs(edge-p85)<=24).mean())>=.70 and abs(p85-paper)<=24 and dark.sum()>=6)
   if checks:count+=1;accept+=int(all(checks))
  out.append({'set':group,'case':name,'ocr_regions':count,'passes_frozen_region_rule':accept,'rendered_candidate':False,'note':'Source/OCR-local admission measurement only. No output PDF or visual/semantic preservation claim.'});print(group,name,count,accept,flush=True)
(E/'control-admission.json').write_text(json.dumps(out,indent=2)+'\n')
