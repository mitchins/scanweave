"""Archive-pdf-tools practical same-input arm, CCITT mask (no JBIG2 substitution)."""
import os,sys,json,subprocess,time,tempfile
from pathlib import Path
import pikepdf
B=Path(__file__).resolve().parent;R=B.parents[1];V=Path(sys.executable).parent;D=B/'real/archive';D.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,OMP_THREAD_LIMIT='1',PATH=str(V)+':'+os.environ['PATH'])
for row in json.loads((B/'corpus.json').read_text()):
 id=row['id'];rec=D/(id+'.run.json')
 if rec.exists() and json.loads(rec.read_text()).get('status')==0:continue
 inp=R/row.get('matched_input',str((B/'real/input'/(id+'.pdf')).relative_to(R)))
 with tempfile.TemporaryDirectory() as tmp:
  png=Path(tmp)/'page.png';q=pikepdf.open(inp);im=next(iter(q.pages[0].Resources.XObject.values()));pikepdf.PdfImage(im).as_pil_image().save(png)
  hocr=D/(id+'.hocr');ocr=subprocess.run(['tesseract',str(png),str(hocr.with_suffix('')),'--dpi','300','-c','hocr_char_boxes=1','hocr'],capture_output=True,text=True,env=env)
  out=D/(id+'.pdf');cmd=list(map(str,[V/'recode_pdf','-P',inp,'-T',hocr,'-o',out,'--mask-compression','ccitt','--threads','1']));start=time.monotonic()
  try:
   with (D/(id+'.log')).open('w') as f:status=subprocess.run(['/usr/bin/time','-v','-o',str(D/(id+'.time.txt'))]+cmd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=120).returncode
   error=None
  except Exception as e:status=None;error=str(e)
  rec.write_text(json.dumps({'id':id,'arm':'archive','command':cmd,'seconds':time.monotonic()-start,'status':status,'error':error,'ocr_status':ocr.returncode,'pdf_bytes':out.stat().st_size if out.exists() else None},indent=2));print(id,status,flush=True)
