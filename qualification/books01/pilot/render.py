#!/usr/bin/env python3
import concurrent.futures,json,os,pathlib,subprocess,sys,time
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot'; ids=json.loads((P/'corpus.frozen.json').read_text())['pilot_6']; lock=json.loads((P/'sources.lock.json').read_text())['pages']; runs=json.loads((Q/'results/runs.json').read_text()); tasks=[]
for id in ids:
 key=id.split('/')[-1];p=lock[id]
 for row in ['src','sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E']:
  path=pathlib.Path(runs[id]['rows'][row].get('path',B/'pilot/runs'/key/(row+'.pdf')))
  if not path.exists():continue
  for renderer in ['pdfium','poppler','mupdf']:
   for dpi in sorted({150,int(p['resolved_dpi'])}):tasks.append((id,row,str(path),renderer,dpi))
def task(t):
 id,row,path,renderer,dpi=t;key=id.split('/')[-1];out=B/'pilot/renders'/key/row/(renderer+'-'+str(dpi)+'.png');cmd=[sys.executable,'-I',str(Q/'render_worker.py'),path,renderer,str(dpi),str(out)];start=time.monotonic();proc=subprocess.run(['/usr/bin/time','-v','-o',str(out)+'.time']+cmd,env={**os.environ,'TMPDIR':str(B/'tmp')},capture_output=True,text=True) if (out.parent.mkdir(parents=True,exist_ok=True) is None) else None
 try:r=json.loads(proc.stdout)
 except Exception:r={'error':proc.stderr[-2000:]}
 r.update(status=proc.returncode,worker_wall_seconds=time.monotonic()-start);return (id,row,renderer,str(dpi),r)
results={}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
 for n,(id,row,renderer,dpi,r) in enumerate(ex.map(task,tasks),1):
  results.setdefault(id,{}).setdefault(row,{}).setdefault(renderer,{})[dpi]=r
  if n%12==0:print(n,'/',len(tasks),'renders measured',flush=True)
(Q/'results/render-costs.json').write_text(json.dumps(results,indent=2)+'\n')
