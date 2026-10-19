"""Measure archive arm's required OCR preparation separately from recoding."""
import time,json,tempfile,subprocess,os,re,concurrent.futures
from pathlib import Path
import pikepdf
B=Path(__file__).resolve().parent;D=B/'real/archive';rows=json.loads((B/'corpus.json').read_text())
def run(row):
 id=row['id'];out=D/(id+'.ocr-time.json')
 if out.exists():return
 start=time.monotonic()
 with tempfile.TemporaryDirectory() as t:
  png=Path(t)/'page.png';q=pikepdf.open(B/'real/input'/(id+'.pdf'));pikepdf.PdfImage(next(iter(q.pages[0].Resources.XObject.values()))).as_pil_image().save(png)
  timer=Path(t)/'time';p=subprocess.run(['/usr/bin/time','-v','-o',str(timer),'tesseract',str(png),str(Path(t)/'out'),'--dpi','300','-c','hocr_char_boxes=1','hocr'],capture_output=True,text=True,env=dict(os.environ,OMP_THREAD_LIMIT='1'));text=timer.read_text();peak=re.search(r'Maximum resident set size \(kbytes\): (\d+)',text)
  data={'id':id,'status':p.returncode,'seconds_including_image_extraction':time.monotonic()-start,'tesseract_peak_kib':int(peak.group(1)) if peak else None,'note':'separate preparation observation; add to recode stage for a pipeline estimate, not an observed single invocation'};out.write_text(json.dumps(data,indent=2));print(id,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,rows))
