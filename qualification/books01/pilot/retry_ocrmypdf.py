#!/usr/bin/env python3
"""Retry only OCRmyPDF failures after installing the missing system txt config."""
import json,os,pathlib,subprocess,time
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]; Q=P/'pilot'; path=Q/'results/runs.json'; rows=json.loads(path.read_text()); locks=json.loads((P/'sources.lock.json').read_text())['pages']; env={**os.environ,'TMPDIR':str(B/'tmp'),'TESSDATA_PREFIX':str(B/'tessdata_best'),'OMP_THREAD_LIMIT':'1','PATH':'/data/coding/scanweave/qualification/.venv/bin:'+os.environ['PATH']}
for id,r in rows.items():
 old=r['rows']['ocrmypdf-E']
 if old['status']==0:continue
 p=locks[id]; d=B/'pilot/runs'/id.split('/')[-1]; out=d/'ocrmypdf-E.pdf';cmd=['/data/coding/scanweave/qualification/.venv/bin/ocrmypdf','--output-type','pdf','-l',p['language'],str(B/p['source_pdf_path']),str(out)];t=time.monotonic()
 with (d/'ocrmypdf-E.retry.log').open('wb') as log:proc=subprocess.run(['/usr/bin/time','-v','-o',str(d/'ocrmypdf-E.retry.time')]+cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
 r['rows']['ocrmypdf-E']={'argv':cmd,'status':proc.returncode,'wall_seconds':time.monotonic()-t,'time_file':str(d/'ocrmypdf-E.retry.time'),'log_file':str(d/'ocrmypdf-E.retry.log'),'previous_attempt':old};(d/'runs.json').write_text(json.dumps(r,indent=2)+'\n');print(id,proc.returncode,flush=True)
path.write_text(json.dumps(rows,indent=2)+'\n')
