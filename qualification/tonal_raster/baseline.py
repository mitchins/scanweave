"""Frozen real development inputs; normal CLI, no OCR/ownership modifications."""
from pathlib import Path
import subprocess,os,json,hashlib,time
B=Path(__file__).resolve().parent;R=B.parents[1];rows=[];binary=Path('/tmp/scanweave-tonal-baseline')
for name in ['cord-00','cord-05','history-02','history-03']:
 d=B/'baseline';d.mkdir(exist_ok=True);inp=R/'qualification/pdf_packaging/real/input'/f'{name}.pdf';out=d/f'{name}.pdf';cmd=[str(binary),str(inp),str(out)];t=time.monotonic()
 with open(d/f'{name}.log','w') as f:p=subprocess.run(['/usr/bin/time','-v','-o',str(d/f'{name}.time.txt')]+cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OMP_THREAD_LIMIT='1'))
 rows.append({'id':name,'command':cmd,'seconds':time.monotonic()-t,'status':p.returncode,'input_sha256':hashlib.sha256(inp.read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'pdf_bytes':out.stat().st_size if out.exists() else None});print(rows[-1],flush=True)
(B/'baseline-runs.json').write_text(json.dumps(rows,indent=2));assert all(x['status']==0 for x in rows)
