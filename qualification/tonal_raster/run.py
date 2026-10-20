"""Use frozen development inputs; never recreate or mutate comparator outputs."""
import json,os,time,subprocess,hashlib,sys,concurrent.futures
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[1];P=R/'qualification/pdf_packaging'
def run(job):
 name,inp,sub=job;D=B/sub;D.mkdir(exist_ok=True);out=D/f'{name}.pdf';record=D/f'{name}.run.json'
 if record.exists() and json.loads(record.read_text()).get('status')==0:return
 cmd=[os.environ.get('SCANWEAVE_BIN',str(R/'target/release/scanweave')),str(inp),str(out)];start=time.monotonic()
 with (D/f'{name}.log').open('w') as f:
  try:status=subprocess.run(['/usr/bin/time','-v','-o',str(D/f'{name}.time.txt')]+cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OMP_THREAD_LIMIT='1'),timeout=1800).returncode
  except subprocess.TimeoutExpired:status='timeout'
 rec={'command':cmd,'input':str(inp.relative_to(R)),'input_sha256':hashlib.sha256(inp.read_bytes()).hexdigest(),'status':status,'executable_sha256':hashlib.sha256(Path(cmd[0]).read_bytes()).hexdigest(),'seconds':time.monotonic()-start,'pdf_bytes':out.stat().st_size if out.exists() else None};record.write_text(json.dumps(rec,indent=2));print(name,status,rec['seconds'],rec['pdf_bytes'],flush=True)
if __name__=='__main__':
 if '--groups' in sys.argv:jobs=[(name,P/'groups'/f'{name}-input.pdf','collections') for name in ['receipts','historical','financial','mixed','forms']]
 elif '--pilot' in sys.argv:jobs=[(name,P/'real/input'/f'{name}.pdf','outputs') for name in ['history-02','scan-linn']]
 else:jobs=[(name,P/'real/input'/f'{name}.pdf','outputs') for name in ['cord-00','cord-05','history-02','history-03','scan-linn','nara-form-01','nara-form-02']]
 with concurrent.futures.ThreadPoolExecutor(max_workers=2 if '--groups' in sys.argv else 1) as pool:list(pool.map(run,jobs))
