"""Reproduce the ordinary ClearScan path and reuse existing evaluators."""
import argparse,subprocess,sys,os,json,gzip,shutil
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[1]
for p in B.rglob('*.json.gz'):
 if not p.with_suffix('').exists():p.with_suffix('').write_bytes(gzip.decompress(p.read_bytes()))
ap=argparse.ArgumentParser();ap.add_argument('--measure-only',action='store_true');ap.add_argument('--repeat',action='store_true');a=ap.parse_args();commands=[]
def call(cmd,log,check=True):
 cmd=list(map(str,cmd));commands.append(cmd)
 with (B/log).open('w') as f:r=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 (B/'commands.json').write_text(json.dumps(commands,indent=2))
 if check and r.returncode:raise RuntimeError((cmd,r.returncode))
for dpi in [300,600]:
 d=B/str(dpi);d.mkdir(exist_ok=True)
 for old,new in [('final.pdf','previous.pdf'),('final.json','previous.json'),('adobe.pdf','adobe.pdf')]:
  if not (d/new).exists():shutil.copyfile(R/'qualification/clearscan_contours'/str(dpi)/old,d/new)
 if not a.measure_only:
  if dpi==300:call(['cargo','build','--release','-p','scanweave-cli'],'build.log')
  call(['/usr/bin/time','-v','-o',d/'final-time.txt',R/'target/release/scanweave-cli','build','--bundle',R/f'qualification/experiments/m1g/fixture/dpi{dpi}/input/document.json','--profile','clearscan','--output',d/'final.pdf','--report',d/'final.json'],f'{dpi}/final.log')
 for arm in ['previous','adobe','final']:
  call([sys.executable,B/'compare.py',dpi,arm,d/(arm+'.pdf')],f'{dpi}/{arm}-metrics.log')
  call([sys.executable,B/'audit.py',dpi,arm,d/(arm+'.pdf')]+(['--report',d/(arm+'.json')] if arm!='adobe' else []),f'{dpi}/{arm}-audit.log')
 call([sys.executable,B/'stages.py',dpi,'final',d/'final.pdf',d/'final.json'],f'{dpi}/final-stages.log')
if not a.measure_only:
 call([sys.executable,B/'real/run.py'],'real/run.log')
 call([sys.executable,B/'hard_negative.py'],'hard-negative.log')
# The real converter records its complete commands in a two-page run manifest.
rows=json.loads((B/'real/runs.json').read_text())
for r in rows:r['returncode']=r['status'];r['seconds']=r['elapsed']
(B/'real/final/runs.json').write_text(json.dumps(rows,indent=2))
call([sys.executable,B/'real/evaluate.py','final'],'real/evaluate.log')
call([sys.executable,B/'real/resources.py'],'real/resources.log')
call([sys.executable,B/'real/financial_search.py'],'real/financial-search.log')
call([sys.executable,B/'oracle.py'],'stage-a/oracle.log')
import pikepdf
p=pikepdf.open(B/'300/final.pdf');q=pikepdf.Pdf.new();q.pages.append(p.pages[0]);q.save(B/'stage-a/A2.pdf')
for script in ['stage_a_measure','ownership_audit','background_metrics','resources','semantic_audit','text_order','validate','hard_negative_audit','patch_sampling_control']:
 call([sys.executable,B/(script+'.py')],script+'.log')
call([sys.executable,B/'zooms.py','--full'],'zooms.log')
if a.repeat:
 call([R/'target/release/scanweave-cli','build','--bundle',R/'qualification/experiments/m1g/fixture/dpi300/input/document.json','--profile','clearscan','--output',B/'300/repeat.pdf','--report',B/'300/repeat.json'],'determinism.log')
 assert (B/'300/repeat.pdf').read_bytes()==(B/'300/final.pdf').read_bytes()
print('Completed matched ClearScan outputs and measurements')
