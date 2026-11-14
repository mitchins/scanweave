#!/usr/bin/env python3
"""Regenerate incomplete local pilot renders from their corresponding PDF."""
import json,os,pathlib,subprocess,sys,time
from PIL import Image
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot';path=Q/'results/render-costs.json';results=json.loads(path.read_text());runs=json.loads((Q/'results/runs.json').read_text());bykey={id.split('/')[-1]:id for id in runs}
for image in (B/'pilot/renders').rglob('*.png'):
 try:
  with Image.open(image) as x:x.load()
  continue
 except OSError:pass
 key,row=image.parent.parent.name,image.parent.name;renderer,dpi=image.stem.split('-');id=bykey[key];pdf=pathlib.Path(runs[id]['rows'][row].get('path',B/'pilot/runs'/key/(row+'.pdf')));cmd=[sys.executable,'-I',str(Q/'render_worker.py'),str(pdf),renderer,dpi,str(image)];start=time.monotonic();p=subprocess.run(['/usr/bin/time','-v','-o',str(image)+'.time']+cmd,env={**os.environ,'TMPDIR':str(B/'tmp')},capture_output=True,text=True);assert p.returncode==0,p.stderr;v=json.loads(p.stdout);v.update(status=0,worker_wall_seconds=time.monotonic()-start,reason='regenerated after interrupted rerender');results[id][row][renderer][dpi]=v;print('repaired',key,row,renderer,dpi,flush=True)
path.write_text(json.dumps(results,indent=2)+'\n')
