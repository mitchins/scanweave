#!/usr/bin/env python3
"""Recheck sw-M using call-order-enforcing shim; require identical prior PDFs."""
import hashlib,json,os,pathlib,subprocess,time
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot';file=Q/'results/runs.json';runs=json.loads(file.read_text());locks=json.loads((P/'sources.lock.json').read_text())['pages'];sw='/data/coding/scanweave/work/scanweave-ab7dfba/target/release/scanweave'
for id,r in runs.items():
 key=id.split('/')[-1];d=B/'pilot/runs'/key; p=locks[id]; old=d/'sw-M.pdf'; new=d/'sw-M-strict.pdf'; state=d/'strict-state';state.unlink(missing_ok=True);env={**os.environ,'TMPDIR':str(B/'tmp'),'TESSDATA_PREFIX':str(B/'tessdata_best'),'OMP_THREAD_LIMIT':'1','PATH':str(B/'pilot/shim')+':'+os.environ['PATH'],'BOOKS01_SHIM_RECORD':str(d/'shim-record.json'),'BOOKS01_SHIM_STATE':str(state)};cmd=[sw,str(B/p['source_pdf_path']),str(new),'--dpi',str(int(p['resolved_dpi'])),'--lang',p['language']];t=time.monotonic()
 with (d/'sw-M-strict.log').open('wb') as log:proc=subprocess.run(['/usr/bin/time','-v','-o',str(d/'sw-M-strict.time')]+cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
 same=proc.returncode==0 and hashlib.sha256(old.read_bytes()).digest()==hashlib.sha256(new.read_bytes()).digest();assert same
 r['rows']['sw-M']['strict_call_order_recheck']={'status':proc.returncode,'wall_seconds':time.monotonic()-t,'time_file':str(d/'sw-M-strict.time'),'identical_to_previous_pdf':same}; print(id,'passed',flush=True)
file.write_text(json.dumps(runs,indent=2)+'\n')
