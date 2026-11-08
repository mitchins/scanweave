import subprocess,sys,os
from pathlib import Path
q=Path('/data/coding/scanweave/qualification');scripts=q/'acr06/trace32';out=q/'acr06/local/trace32/runs'; env=dict(os.environ,LD_LIBRARY_PATH='/data/coding/scanweave/tools/dist/lib'); py=q/'.venv/bin/python';mu=q/'acr06/local/mupdf-venv/bin/python'
for n in ('single','competitive600','mixed','historical','competitive300','financial','forms','receipts','competitive600-q3','single-q3'):
 a=out/f'{n}-main-1.pdf';b=out/f'{n}-candidate-1.pdf';print('START',n,flush=True)
 for cmd in ([str(py),'-I',str(scripts/'check_pair.py'),str(out),n],[str(py),'-I',str(scripts/'search_check.py'),str(a),str(b)]):
  with (out/(n+'-'+('preservation' if 'check_pair.py' in cmd[2] else 'search')+'.log')).open('w') as log:
   p=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if p.returncode:print('FAIL',n,cmd[2],p.returncode,flush=True);sys.exit(p.returncode)
 with (out/f'{n}-main-map.json').open('w') as f:p=subprocess.run([str(mu),'-I',str(scripts/'font_mapping.py'),str(a)],stdout=f,stderr=subprocess.DEVNULL)
 if p.returncode:sys.exit(p.returncode)
 with (out/f'{n}-candidate-map.json').open('w') as f:p=subprocess.run([str(mu),'-I',str(scripts/'font_mapping.py'),str(b)],stdout=f,stderr=subprocess.DEVNULL)
 if p.returncode:sys.exit(p.returncode)
 assert (out/f'{n}-main-map.json').read_bytes()==(out/f'{n}-candidate-map.json').read_bytes(),(n,'mapping')
 print('PASS',n,flush=True)
