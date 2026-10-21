"""Same image-only page PDFs to all ordinary converters; resumable bounded runs."""
import os,json,time,subprocess,concurrent.futures,hashlib,sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools_env import comparison_environment
import pikepdf,pypdfium2 as pdfium
from PIL import Image
B=Path(__file__).resolve().parent;R=B.parents[1];V=Path(sys.executable).parent
rows=json.loads((B/'corpus.json').read_text());OUT=B/'real';OUT.mkdir(exist_ok=True)
env=comparison_environment(str(V))
# Strip pre-existing text by rendering once, losslessly packaging these exact
# shared samples at the PDF's physical size. This is corpus preparation only.
for row in rows:
 src=R/row['input_pdf'];dest=OUT/'input'/src.name;dest.parent.mkdir(exist_ok=True)
 if not dest.exists():
  doc=pdfium.PdfDocument(str(src));page=doc[0];im=page.render(scale=300/72).to_pil().convert('RGB');w,h=im.size;pw,ph=page.get_size();q=pikepdf.Pdf.new();pg=q.add_blank_page(page_size=(pw,ph));s=pikepdf.Stream(q,im.tobytes());s.Type=pikepdf.Name.XObject;s.Subtype=pikepdf.Name.Image;s.Width=w;s.Height=h;s.ColorSpace=pikepdf.Name.DeviceRGB;s.BitsPerComponent=8;pg.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=s));pg.Contents=pikepdf.Stream(q,f'q {pw} 0 0 {ph} 0 0 cm /Im Do Q'.encode());q.save(dest,deterministic_id=True)
 row['matched_input']=str(dest.relative_to(R));row['matched_bytes']=dest.stat().st_size;row['matched_sha256']=hashlib.sha256(dest.read_bytes()).hexdigest()
(B/'corpus.json').write_text(json.dumps(rows,indent=2))
# One same-membership corpus document for the sequential GUI reference engine.
combined=OUT/'all-input.pdf'
q=pikepdf.Pdf.new()
for row in rows:
 p=pikepdf.open(R/row['matched_input']);q.pages.extend(p.pages)

if not combined.exists():q.save(combined,deterministic_id=True)
# Also ordinary genuine multi-page input, requiring no manual OCR/bundle steps.
q=pikepdf.Pdf.new()
for row in rows[:3]:
 p=pikepdf.open(R/row['matched_input']);q.pages.extend(p.pages)

if not (OUT/'receipt-three-pages.pdf').exists():q.save(OUT/'receipt-three-pages.pdf',deterministic_id=True)

def call(row,arm):
 d=OUT/arm;d.mkdir(exist_ok=True);id=row['id'];record=d/(id+'.run.json')
 if record.exists() and json.loads(record.read_text()).get('status')==0:return json.loads(record.read_text())
 inp=R/row['matched_input'];out=d/(id+'.pdf');log=d/(id+'.log');tim=d/(id+'.time.txt')
 if arm=='scanweave':cmd=[R/'target/release/scanweave',inp,out]
 else:cmd=[V/'ocrmypdf','--output-type','pdf','--jobs','1','-O'+arm[-1],inp,out]
 cmd=list(map(str,cmd));start=time.monotonic();status=None;error=None
 try:
  with log.open('w') as f:status=subprocess.run(['/usr/bin/time','-v','-o',str(tim)]+cmd,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=240).returncode
 except Exception as e:error=str(e)
 data={'id':id,'arm':arm,'command':cmd,'seconds':time.monotonic()-start,'status':status,'error':error,'pdf_bytes':out.stat().st_size if out.exists() else None}
 record.write_text(json.dumps(data,indent=2));print(id,arm,status,data['pdf_bytes'],round(data['seconds'],2),flush=True);return data
if __name__=='__main__':
 jobs=[(row,arm) for row in rows for arm in ['scanweave','ocrmypdf1','ocrmypdf3']]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda job:call(*job),jobs))
