from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools_env import comparison_binary
import subprocess,os,json,hashlib,time
B=Path(__file__).resolve().parent;R=B.parents[1];D=B/'control-runs';D.mkdir(exist_ok=True);out=[]
for name,profile in [('scan-linn','clearscan'),('cord-00','faithful')]:
 paths=[]
 for label,exe in [('before',comparison_binary('SCANWEAVE_BASELINE_BIN')),('after',comparison_binary('SCANWEAVE_BIN'))]:
  path=D/f'{name}-{profile}-{label}.pdf';cmd=[exe,str(R/'qualification/pdf_packaging/real/input'/f'{name}.pdf'),str(path),'--profile',profile];t=time.monotonic()
  with (path.with_suffix('.log')).open('w') as f:p=subprocess.run(['/usr/bin/time','-v','-o',str(path.with_suffix('.time.txt'))]+cmd,env=dict(os.environ,OMP_THREAD_LIMIT='1'),stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  assert p.returncode==0;paths.append(path);out.append({'id':name,'profile':profile,'arm':label,'seconds':time.monotonic()-t,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'command':cmd});print(out[-1],flush=True)
 assert paths[0].read_bytes()==paths[1].read_bytes()
(B/'controls-results.json').write_text(json.dumps(out,indent=2))
# One normal ClearScan repeat for deterministic serialization.
p=B/'control-runs'/'cord-00-repeat.pdf';subprocess.run([comparison_binary('SCANWEAVE_BIN'),str(R/'qualification/pdf_packaging/real/input/cord-00.pdf'),str(p)],check=True,capture_output=True,env=dict(os.environ,OMP_THREAD_LIMIT='1'),timeout=1800);assert p.read_bytes()==(B/'final/cord-00.pdf').read_bytes()
(B/'determinism.json').write_text(json.dumps({'id':'cord-00','byte_identical':True,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()},indent=2))
