import json,gzip,time,zlib,hashlib
from pathlib import Path
import pikepdf,numpy as np
B=Path(__file__).resolve().parent;R=B.parents[1];P=R/'qualification/pdf_packaging'
cases=['cord-00','cord-05','history-02','history-03','scan-linn','nara-form-01','nara-form-02'];out=[]
for id in cases:
 report=json.loads((P/'real/scanweave'/f'{id}.pdf.json').read_text());pr=report['conversion']['page_reports'][0]
 p=pikepdf.open(P/'real/input'/f'{id}.pdf');src=next(iter(p.pages[0].Resources.XObject.values()));im=pikepdf.PdfImage(src).as_pil_image().convert('RGB');a=np.asarray(im);gray=np.all(a[:,:,0]==a[:,:,1]) and np.all(a[:,:,1]==a[:,:,2]);a=a[:,:,:1] if gray else a
 tests=[]
 for predictor in [1,2,12]:
  start=time.monotonic();d=a.copy()
  if predictor==2:d[:,1:,:]=a[:,1:,:]-a[:,:-1,:]
  if predictor==12:d[1:,:,:]=a[1:,:,:]-a[:-1,:,:];d=np.concatenate([np.full((a.shape[0],1),2,dtype=np.uint8),d.reshape(a.shape[0],-1)],axis=1)
  tests.append({'predictor':predictor,'bytes':len(zlib.compress(d.tobytes(),6)),'seconds':time.monotonic()-start})
 resources=[];q=pikepdf.open(P/'real/scanweave'/f'{id}.pdf')
 for obj in q.objects:
  if isinstance(obj,pikepdf.Stream) and obj.get('/Subtype')==pikepdf.Name.Image:resources.append({'object':obj.objgen,'bytes':len(obj.read_raw_bytes()),'width':int(obj.Width),'height':int(obj.Height),'filter':str(obj.Filter)})
 rec={'id':id,'source':{'bytes':len(src.read_raw_bytes()),'format':str(src.Filter),'width':int(src.Width),'height':int(src.Height),'gray':bool(gray)},'predictors':tests,'ocr_words':report['pages'][0].get('ocr_words',pr['semantic_spans']),'supplied_characters':pr['supplied_chars'],'observations':len(pr['reconstruction']['observations']),'reconstruction_keys':list(pr['reconstruction']),'fallback_reasons':pr['fallback_reasons'],'regions':pr.get('regions',[]),'coverage':pr['coverage'],'accepted_occurrences':sum(o['owner'].startswith('visible') for o in pr['occurrences']),'patches':pr['patches'],'timings':report['conversion']['stage_timings'],'resources':resources};out.append(rec);print(id,rec['ocr_words'],rec['accepted_occurrences'],tests,flush=True)
(B/'diagnosis.json').write_text(json.dumps(out,indent=2))
