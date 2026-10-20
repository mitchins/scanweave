from pathlib import Path
import json,subprocess,time
B=Path(__file__).resolve().parent;R=B.parents[2];rows=[]
for name in ['cord-02','history-01']:
 src=R/'qualification/clearscan_competitive/real'/name;out=B/'final'/name
 cmd=['/usr/bin/time','-v','-o',str(out.with_suffix('.time.txt')),str(R/'target/release/scanweave-cli'),'build',str(src.with_suffix('.png')),'--ocr',str(src.with_suffix('.regions.hocr')),'--dpi','300','--profile','clearscan','--output',str(out.with_suffix('.pdf')),'--report',str(out.with_suffix('.json'))]
 t=time.monotonic();p=subprocess.run(cmd,capture_output=True,text=True);out.with_suffix('.log').write_text(p.stdout+p.stderr);rows.append({'name':name,'command':cmd,'status':p.returncode,'elapsed':time.monotonic()-t});(B/'runs.json').write_text(json.dumps(rows,indent=2));assert p.returncode==0;print(name,rows[-1]['elapsed'],flush=True)
