import json,subprocess,time,os,hashlib
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[1]
for dpi in [300,600]:
 D=B/str(dpi);D.mkdir(exist_ok=True);inp=R/f'qualification/experiments/m1g/fixture/dpi{dpi}/input/document.json';cmd=[os.environ.get('SCANWEAVE_BIN',str(R/'target/release/scanweave')),'build','--bundle',str(inp),'--profile','clearscan','--output',str(D/'final.pdf'),'--report',str(D/'report.json')];start=time.monotonic()
 with (D/'run.log').open('w') as f:p=subprocess.run(['/usr/bin/time','-v','-o',str(D/'time.txt')]+cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OMP_THREAD_LIMIT='1'),timeout=1800)
 (D/'run.json').write_text(json.dumps({'command':cmd,'status':p.returncode,'seconds':time.monotonic()-start,'input_sha256':hashlib.sha256(inp.read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(Path(cmd[0]).read_bytes()).hexdigest()},indent=2));print(dpi,p.returncode,flush=True)
