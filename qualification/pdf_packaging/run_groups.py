"""Matched multi-page corpus collections, identical membership for all engines.
Single-page diagnostics are supplementary; collection serialized bytes are the fair comparison.
"""
import json,os,sys,time,subprocess,concurrent.futures,hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools_env import comparison_environment
import pikepdf
B=Path(__file__).resolve().parent;R=B.parents[1];V=Path(sys.executable).parent;D=B/'groups';D.mkdir(exist_ok=True)
rows=json.loads((B/'corpus.json').read_text());groups={}
for name,prefix in [('receipts','cord-'),('historical','history-'),('financial','annual-'),('mixed','scan-'),('forms','nara-')]:
 members=[r for r in rows if r['id'].startswith(prefix)];q=pikepdf.Pdf.new()
 for r in members:
  p=pikepdf.open(R/r['matched_input']);q.pages.extend(p.pages)
 inp=D/(name+'-input.pdf')
 if not inp.exists():q.save(inp,deterministic_id=True)
 groups[name]={'members':[r['id'] for r in members],'input':str(inp.relative_to(R))}
(B/'groups.json').write_text(json.dumps(groups,indent=2))
env=comparison_environment(str(V))
def run(job):
 name,arm=job;rec=D/f'{name}-{arm}.run.json'
 if rec.exists() and json.loads(rec.read_text()).get('status')==0:return
 inp=R/groups[name]['input'];out=D/f'{name}-{arm}.pdf'
 if arm=='adobe':cmd=[R/'adobe-acrobat-sandbox/clearscan.sh',inp,out]
 elif arm=='scanweave':cmd=[R/'target/release/scanweave',inp,out]
 else:cmd=[V/'ocrmypdf','--jobs','1','--output-type','pdf','-O'+arm[-1],inp,out]
 cmd=list(map(str,cmd));start=time.monotonic();status=None;error=None
 try:
  with (D/f'{name}-{arm}.log').open('w') as f:status=subprocess.run(['/usr/bin/time','-v','-o',str(D/f'{name}-{arm}.time.txt')]+cmd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=1200).returncode
 except Exception as e:error=str(e)
 rec.write_text(json.dumps({'group':name,'arm':arm,'command':cmd,'input_sha256':hashlib.sha256(inp.read_bytes()).hexdigest(),'status':status,'error':error,'seconds':time.monotonic()-start,'pdf_bytes':out.stat().st_size if out.exists() else None},indent=2));print(name,arm,status,round(time.monotonic()-start,2),flush=True)
if __name__=='__main__':
 if '--adobe' in sys.argv:
  for name in groups:run((name,'adobe'))
 else:
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,[(name,arm) for name in groups for arm in ['scanweave','ocrmypdf1','ocrmypdf3']]))
