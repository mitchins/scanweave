import subprocess,json,time
from pathlib import Path
B=Path(__file__).resolve().parent
for p in sorted(list(B.glob('cord-*.png'))+list(B.glob('history-*.png'))):
 start=time.monotonic();res=subprocess.run(['tesseract',str(p),str(p.with_suffix('')),'--dpi','300','-l','eng','hocr'],capture_output=True,text=True)
 print(p.name,res.returncode,round(time.monotonic()-start,2),flush=True)
 (p.with_suffix('.ocr.log')).write_text(res.stderr)
