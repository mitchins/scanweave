#!/usr/bin/env python3
"""Measure Poppler again with CropBox, matching PDFium/MuPDF page boundaries."""
import concurrent.futures,hashlib,json,os,pathlib,subprocess,sys,time
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot';resultfile=Q/'results/render-costs.json';r=json.loads(resultfile.read_text()); runs=json.loads((Q/'results/runs.json').read_text());tasks=[]
for id,rows in r.items():
 key=id.split('/')[-1]
 for row,renderers in rows.items():
  if row not in ('mrc-M','adobe-E'):continue
  for dpi,v in renderers['poppler'].items():
   old=pathlib.Path(v['output']);pdf=pathlib.Path(runs[id]['rows'][row].get('path',B/'pilot/runs'/key/(row+'.pdf')));tasks.append((id,row,dpi,old,pdf))
def task(t):
 id,row,dpi,out,pdf=t;old=hashlib.sha256(out.read_bytes()).hexdigest();cmd=[sys.executable,'-I',str(Q/'render_worker.py'),str(pdf),'poppler',dpi,str(out)];start=time.monotonic();p=subprocess.run(['/usr/bin/time','-v','-o',str(out)+'.time']+cmd,capture_output=True,text=True,env={**os.environ,'TMPDIR':str(B/'tmp')});record=json.loads(p.stdout) if p.returncode==0 else {'error':p.stderr[-2000:]};record.update(status=p.returncode,worker_wall_seconds=time.monotonic()-start,prior_mediabox_render_sha256=old,cropbox_render_sha256=hashlib.sha256(out.read_bytes()).hexdigest() if out.exists() else None);return id,row,dpi,record
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for n,(id,row,dpi,v) in enumerate(pool.map(task,tasks),1):
  r[id][row]['poppler'][dpi]=v
  if n%21==0:print(n,'/',len(tasks),'CropBox renders measured',flush=True)
resultfile.write_text(json.dumps(r,indent=2)+'\n')
