#!/usr/bin/env python3
"""Recheck retry OCR using the baseline's exact PSM 6 argument ordering."""
import concurrent.futures,hashlib,json,os,pathlib,subprocess,time
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1]; index=P/'pilot/results/frozen-ocr-index.json'; x=json.loads(index.read_text());env={**os.environ,'TMPDIR':str(B/'tmp'),'TESSDATA_PREFIX':str(B/'tessdata_best'),'OMP_THREAD_LIMIT':'1'}
def run(item):
 id,r=item; d=B/'ocr-frozen'/id.split('/')[-1]; png=d/'page.png'; old=r['runs']['6']['repeat'][0]['output_sha256']; trials=[]
 for repeat in (1,2):
  prefix=d/f'psm6-exact-{repeat}';cmd=['/usr/bin/tesseract',str(png),str(prefix),'-l',r['language'],'--dpi',str(r['dpi']),'--psm','6','-c','hocr_char_boxes=1','hocr'];t=time.monotonic();p=subprocess.run(['/usr/bin/time','-v','-o',str(prefix)+'.time']+cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE); f=pathlib.Path(str(prefix)+'.hocr'); h=hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None;trials.append({'argv':cmd,'status':p.returncode,'wall_seconds':time.monotonic()-t,'output_sha256':h,'time_file':str(prefix)+'.time'});assert p.returncode==0 and h==old
 r['runs']['6']={'repeat':trials,'deterministic':True,'same_as_original_order':True};(d/'freeze.json').write_text(json.dumps(r,indent=2)+'\n');return id
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for id in pool.map(run,x['pages'].items()):print(id,flush=True)
index.write_text(json.dumps(x,indent=2)+'\n')
