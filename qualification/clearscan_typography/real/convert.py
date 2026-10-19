import argparse,subprocess,time,json
from pathlib import Path
R=Path(__file__).resolve().parents[3];B=R/'qualification/clearscan_competitive/real';ap=argparse.ArgumentParser();ap.add_argument('arm');ap.add_argument('--limit',type=int);ap.add_argument('--region-ocr',action='store_true');a=ap.parse_args();out=R/'qualification/clearscan_typography/real'/a.arm;out.mkdir(exist_ok=True);rows=[]
files=sorted(list(B.glob('cord-*.png'))+list(B.glob('history-*.png')))
files=[p for p in files if '.ocr-crop' not in p.name]
if a.limit:files=files[:a.limit]
for p in files:
 start=time.monotonic();cmd=['/usr/bin/time','-v','-o',str(out/(p.stem+'.time.txt')),str(R/'target/release/scanweave-cli'),'build',str(p),'--ocr',str(p.with_suffix('.regions.hocr') if a.region_ocr else p.with_suffix('.hocr')),'--dpi','300','--profile','clearscan','--output',str(out/(p.stem+'.pdf')),'--report',str(out/(p.stem+'.json'))]
 try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=180);error=None
 except subprocess.TimeoutExpired as e:r=None;error='180 second bounded timeout'
 (out/(p.stem+'.log')).write_text((r.stdout+r.stderr) if r else error)
 row={'name':p.stem,'seconds':time.monotonic()-start,'returncode':r.returncode if r else None,'error':error,'command':cmd};rows.append(row);(out/'runs.json').write_text(json.dumps(rows,indent=2));print(row['name'],row['returncode'],round(row['seconds'],2),flush=True)
