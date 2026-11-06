#!/usr/bin/env python3
"""Rerun changed candidate inputs with temporary ownership-mask capture."""
import concurrent.futures,json,os,subprocess
from pathlib import Path
q=Path('/data/coding/scanweave/qualification');loc=q/'acr06/local/donorfix'; binary=loc/'scanweave-ownership-instrumented'; jobs=[]
for receipt in sorted((loc/'candidate').glob('*.run.json')):
 name=receipt.name[:-len('.run.json')]; prefix=os.environ.get('DONOR_CAPTURE_PREFIX');
 if prefix and not name.startswith(prefix):continue
 row=json.loads(receipt.read_text()); old=loc/'main'/f'{name}.pdf.json'
 if not old.exists(): old=loc/'baseline'/('single.pdf.json' if name=='single' else f'{name}-off.pdf.json')
 cand=loc/'candidate'/f'{name}.pdf.json'
 if not old.exists() or not cand.exists():continue
 a=json.loads(old.read_text());b=json.loads(cand.read_text());changed=False
 for pa,pb in zip(a['conversion']['page_reports'],b['conversion']['page_reports']):
  aa={x['symbol_id']:(x['decision'],x.get('replacement_bbox_px'),x.get('prototype_id')) for x in pa['reconstruction']['occurrences']};bb={x['symbol_id']:(x['decision'],x.get('replacement_bbox_px'),x.get('prototype_id')) for x in pb['reconstruction']['occurrences']}
  if aa!=bb or pa['occurrences']!=pb['occurrences']:changed=True;break
 if changed:jobs.append((name,row['command']))
jobs.sort(key=lambda x:(x[0]!='financial',x[0]))
def run(job):
 name,cmd=job;out=loc/'ownership'/name;out.mkdir(parents=True,exist_ok=True);cmd[0]=str(binary);cmd[2]=str(out/'capture.pdf');env=dict(os.environ,SCANWEAVE_OWNERSHIP_CAPTURE=str(out),SCANWEAVE_PDFIUM_LIBRARY='/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so',SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python',OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4')
 with (out/'capture.log').open('w') as f:p=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(name)
print('jobs',len(jobs),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,jobs))
