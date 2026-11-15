#!/usr/bin/env python3
"""Run pilot scoring wrapper for completed development pages and record errors."""
import concurrent.futures,json,os,pathlib,subprocess,sys,time
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];D=B/'phase2';pages=[p['id'] for p in json.loads((P/'corpus.frozen.json').read_text())['pages'] if p['split']=='dev'];assert len(pages)==36; mode=sys.argv[1] if len(sys.argv)>1 else 'cli';env={**os.environ,'TMPDIR':str(B/'tmp'),'OPENBLAS_NUM_THREADS':'1','OMP_THREAD_LIMIT':'1'}
def page(id):
 key=id.split('/')[-1];runs=D/'runs'/key/'runs.json'
 while not runs.exists():time.sleep(3)
 rows=['src','sw-E','mrc-M','ocrmypdf-E'] if mode=='cli' else ['adobe-E']
 for row in rows:
  target=D/'metrics'/key/(row+'.json')
  if target.exists():continue
  cmd=[sys.executable,'-I',str(P/'phase2/score.py'),id,row]
  try:
   proc=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=900)
   if proc.returncode!=0:target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps({'id':id,'row':row,'status':'error','returncode':proc.returncode,'error':proc.stderr[-3000:]},indent=2)+'\n')
  except Exception as e:target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps({'id':id,'row':row,'status':'error','error':repr(e)},indent=2)+'\n')
  print(id,row,'scored',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(page,pages))
print(mode,'SCORING FINISHED',flush=True)
