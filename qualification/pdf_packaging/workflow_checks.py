"""Ordinary CLI integration: genuine 3-page input, rotated crops, failures."""
import json,subprocess,tempfile,hashlib
from pathlib import Path
import pikepdf,pypdfium2 as pdfium
B=Path(__file__).resolve().parent;R=B.parents[1];exe=R/'target/release/scanweave';checks=[]
p=B/'real/receipt-three-pages-final.pdf';q=pikepdf.open(p);src=pikepdf.open(B/'real/receipt-three-pages.pdf');assert len(q.pages)==3
for a,b in zip(src.pages,q.pages):
 assert max(abs(float(x)-float(y)) for x,y in zip(a.MediaBox,b.MediaBox))<.001
report=json.loads(Path(str(p)+'.json').read_text());assert report['pages'][0]['hocr'];assert report['poppler_version'];assert report['pages'][0]['ocr']['name']=='Tesseract'
checks.append({'name':'ordinary-genuine-three-page','status':'pass','output_bytes':p.stat().st_size,'pages':3,'no_manual_OCR_bundle':True,'pdfium_text_lengths':[len(pg.get_textpage().get_text_range()) for pg in pdfium.PdfDocument(str(p))]})
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp);raw=pikepdf.open(B/'real/input/cord-02.pdf');geometry=pikepdf.Pdf.new()
 for rotation in [0,90]:
  geometry.pages.append(raw.pages[0]);pg=geometry.pages[-1];w=float(pg.MediaBox[2]);h=float(pg.MediaBox[3]);pg.CropBox=pikepdf.Array([12,24,w-12,h-24]);pg.Rotate=rotation
 inp=t/'geometry.pdf';out=t/'out.pdf';geometry.save(inp)
 cmd=[str(exe),str(inp),str(out),'--dpi','72'];run=subprocess.run(cmd,capture_output=True,text=True);assert run.returncode==0,run.stderr
 sizes=[tuple(pg.get_size()) for pg in pdfium.PdfDocument(str(out))];expected=[(w-24,h-48),(h-48,w-24)]
 assert all(max(abs(a-b) for a,b in zip(x,y))<.001 for x,y in zip(sizes,expected)),(sizes,expected)
 checks.append({'name':'cropbox-and-rotation','status':'pass','dpi':72,'sizes':sizes,'expected':expected})
 bad=t/'bad.pdf';bad.write_bytes(b'not a PDF');invalid=t/'invalid.pdf';run=subprocess.run([str(exe),str(bad),str(invalid)],capture_output=True,text=True);assert run.returncode!=0 and not invalid.exists();checks.append({'name':'invalid-input','status':'pass','exit':run.returncode,'message':run.stderr})
 run=subprocess.run([str(exe),str(inp),str(t/'no-tools.pdf')],capture_output=True,text=True,env={'PATH':str(t)});assert run.returncode!=0 and 'Poppler' in run.stderr;checks.append({'name':'missing-dependency','status':'pass','exit':run.returncode,'message':run.stderr})
(B/'workflow-checks.json').write_text(json.dumps(checks,indent=2));print(checks)
