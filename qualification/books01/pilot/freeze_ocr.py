#!/usr/bin/env python3
"""Freeze real Tesseract OCR on exactly the six selected source-PDF samples."""
import concurrent.futures,hashlib,json,os,pathlib,subprocess,time
import pikepdf
from PIL import Image
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]; Q=P/'pilot'; D=B/'ocr-frozen'; D.mkdir(parents=True,exist_ok=True)
ids=json.loads((P/'corpus.frozen.json').read_text())['pilot_6']; lock=json.loads((P/'sources.lock.json').read_text())['pages']; assert len(ids)==6 and len(set(ids))==6
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(id):
 p=lock[id]; key=id.split('/')[-1]; d=D/key;d.mkdir(parents=True,exist_ok=True); pdf=B/p['source_pdf_path']; png=d/'page.png'
 with pikepdf.open(pdf) as q:
  obj=q.pages[0].Resources.XObject['/Im0']; im=pikepdf.PdfImage(obj).as_pil_image().convert('RGB'); assert hashlib.sha256(im.tobytes()).hexdigest()==p['decoded_pixel_sha256']; im.save(png)
 env={**os.environ,'TMPDIR':str(B/'tmp'),'TESSDATA_PREFIX':str(B/'tessdata_best'),'OMP_THREAD_LIMIT':'1'}; result={'page_id':id,'dpi':int(p['resolved_dpi']),'language':p['language'],'decoded_pixel_sha256':p['decoded_pixel_sha256'],'source_pdf_sha256':p['source_pdf_sha256'],'png_sha256':sha(png),'runs':{}}
 for psm in (3,6):
  commands=[]
  for repeat in (1,2):
   prefix=d/f'psm{psm}-{repeat}'; cmd=['/usr/bin/tesseract',str(png),str(prefix),'-l',p['language'],'--dpi',str(int(p['resolved_dpi'])),*(['-c','hocr_char_boxes=1','--psm','3'] if psm==3 else ['--psm','6','-c','hocr_char_boxes=1']),'hocr']; t=time.monotonic(); proc=subprocess.run(['/usr/bin/time','-v','-o',str(prefix)+'.time']+cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE); (d/f'psm{psm}-{repeat}.log').write_bytes(proc.stderr); out=pathlib.Path(str(prefix)+'.hocr'); commands.append({'argv':cmd,'status':proc.returncode,'wall_seconds':time.monotonic()-t,'output_sha256':sha(out) if out.exists() else None,'time_file':str(prefix)+'.time'});
   if proc.returncode or not out.exists(): raise RuntimeError(f'{id} psm{psm} failed: {proc.stderr.decode(errors="replace")}')
  result['runs'][str(psm)]={'repeat':commands,'deterministic':commands[0]['output_sha256']==commands[1]['output_sha256']}
 (d/'freeze.json').write_text(json.dumps(result,indent=2)+'\n'); print(id,[(k,v['deterministic']) for k,v in result['runs'].items()],flush=True); return id,result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: rows=dict(pool.map(run,ids))
(Q/'results').mkdir(parents=True,exist_ok=True); (Q/'results/frozen-ocr-index.json').write_text(json.dumps({'schema':'books01-frozen-ocr/1','pages':rows},indent=2)+'\n')
