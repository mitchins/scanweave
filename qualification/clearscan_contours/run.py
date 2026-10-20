#!/usr/bin/env python3
"""Reproduce the normal CLI conversion. Oracle paths go only to evaluators."""
import argparse,subprocess,sys,os,hashlib,gzip
from pathlib import Path
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
# Frozen reports are stored compressed; the evaluator APIs read plain JSON.
for archive in B.rglob('*.json.gz'):
 target=archive.with_suffix('')
 if not target.exists():target.write_bytes(gzip.decompress(archive.read_bytes()))
ap=argparse.ArgumentParser();ap.add_argument('--dpi',type=int,nargs='+',choices=[300,600],default=[300,600]);ap.add_argument('--measure',action='store_true');ap.add_argument('--zooms',action='store_true');ap.add_argument('--repeat',action='store_true');a=ap.parse_args()
def call(args,log,env=None):
 with log.open('w') as f:subprocess.run(list(map(str,args)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True,env=env)
call(['cargo','build','--release','-p','scanweave-cli'],B/'reproduce-build.log')
for dpi in a.dpi:
 d=B/str(dpi);d.mkdir(exist_ok=True)
 call(['/usr/bin/time','-v','-o',d/'final-time.txt',ROOT/'target/release/scanweave-cli','build','--bundle',ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/input/document.json','--profile','clearscan','--output',d/'final.pdf','--report',d/'final.json'],d/'final.log')
 if a.measure:
  for arm in ['adobe','previous','final']:call([sys.executable,B/'compare.py',dpi,arm,d/(arm+'.pdf')],d/(arm+'-metrics.log'))
  call([sys.executable,B/'audit.py',dpi,'final',d/'final.pdf','--report',d/'final.json'],d/'final-audit.log')
  call([sys.executable,B/'stages.py',dpi,'final',d/'final.pdf',d/'final.json'],d/'final-stages.log')
if a.measure and set(a.dpi)=={300,600}:
 for script in ['ownership_audit.py','geometry.py','outline_audit.py','font_complexity.py','semantic_audit.py','text_order.py','validate.py','summarize.py']:
  call([sys.executable,B/script],B/(script.removesuffix('.py')+'.log'))
 if a.zooms:call([sys.executable,B/'zooms.py','--full'],B/'zooms.log')
if a.repeat:
 call([ROOT/'target/release/scanweave-cli','build','--bundle',ROOT/'qualification/experiments/m1g/fixture/dpi300/input/document.json','--profile','clearscan','--output',B/'300/repeat.pdf','--report',B/'300/repeat.json'],B/'determinism.log')
 assert (B/'300/final.pdf').read_bytes()==(B/'300/repeat.pdf').read_bytes()
print('Completed normal ClearScan PDFs:',*[str(B/str(d)/'final.pdf') for d in a.dpi])
