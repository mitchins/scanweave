"""One evaluator-only disabled-fastpath build, same final source/encoding/OCR."""
import json,hashlib,os,subprocess,time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools_env import comparison_binary
B=Path(__file__).resolve().parent;R=B.parents[1];D=B/'runtime';D.mkdir(exist_ok=True);out=[]
for name,exe in [('recompose',comparison_binary('SCANWEAVE_RECOMPOSE_BIN')),('skip_unneeded',comparison_binary('SCANWEAVE_BIN'))]:
 dst=D/f'{name}.pdf';cmd=[exe,str(R/'qualification/pdf_packaging/real/input/cord-05.pdf'),str(dst)];start=time.monotonic()
 with (D/f'{name}.log').open('w') as f:p=subprocess.run(['/usr/bin/time','-v','-o',str(D/f'{name}.time.txt')]+cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OMP_THREAD_LIMIT='1'))
 if p.returncode:raise RuntimeError(name)
 q=json.loads(Path(str(dst)+'.json').read_text());r=q['conversion']['page_reports'][0];rec={'arm':name,'command':cmd,'seconds':time.monotonic()-start,'pdf_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'pdf_bytes':dst.stat().st_size,'text_sha256':hashlib.sha256(subprocess.check_output(['pdftotext',str(dst),'-'])).hexdigest(),'vectors':sum(o['owner'].startswith('visible') for o in r['occurrences']),'page_stage_ms':r['stage_timings_ms'],'document_stage_ms':q['conversion']['stage_timings']};out.append(rec);print(name,rec['seconds'],flush=True)
assert out[0]['pdf_sha256']==out[1]['pdf_sha256'];assert out[0]['text_sha256']==out[1]['text_sha256'];assert out[1]['vectors']==0
(B/'runtime-control.json').write_text(json.dumps(out,indent=2))
