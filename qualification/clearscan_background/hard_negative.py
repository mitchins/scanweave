"""Two bounded faint-line controls, normal converter, existing page0/OCR."""
from pathlib import Path
import json,hashlib,subprocess,math
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image
B=Path(__file__).resolve().parent;R=B.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
rows=[]
for dpi in [300,600]:
 d=B/'hard-negative'/str(dpi);d.mkdir(parents=True,exist_ok=True);src=R/f'qualification/experiments/m1g/fixture/dpi{dpi}/input';scale=dpi//300
 im=np.asarray(Image.open(src/'page00.png').convert('RGB')).copy();y=109*scale;x0=55*scale;x1=520*scale
 # A faint printed rule crosses the word, including counters, extends onto
 # unclassified paper, and is darker than paper but lighter than text ink.
 im[y:y+scale,x0:x1]=np.minimum(im[y:y+scale,x0:x1],245)
 Image.fromarray(im).save(d/'page00.png');ocr=json.loads((src/'page00.ocr.json').read_text());ocr['raster']['file_sha256']=sha((d/'page00.png').read_bytes());ocr['raster']['pixel_sha256']=sha(f'SWRASTER1\nrgb8\n{im.shape[1]}\n{im.shape[0]}\nsrgb\n-\n'.encode()+im.tobytes());(d/'page00.ocr.json').write_text(json.dumps(ocr,indent=2));bundle=json.loads((src/'document.json').read_text());bundle['sources']=bundle['sources'][:1];bundle['sources'][0]['file_sha256']=ocr['raster']['file_sha256'];bundle['pages']=bundle['pages'][:1];bundle['pages'][0]['ocr_page_sha256']=sha((d/'page00.ocr.json').read_bytes());(d/'document.json').write_text(json.dumps(bundle,indent=2))
 cmd=[R/'target/release/scanweave-cli','build','--bundle',d/'document.json','--profile','clearscan','--output',d/'final.pdf','--report',d/'final.json'];p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);(d/'run.log').write_text(p.stdout+p.stderr);assert p.returncode==0
 report=json.loads((d/'final.json').read_text())['page_reports'][0];pdf=pikepdf.open(d/'final.pdf');native={}
 for name,x in pdf.pages[0].Resources.XObject.items():
  if x.get('/Subtype')!='/Image':continue
  arr=np.asarray(pikepdf.PdfImage(x).as_pil_image().convert('RGB'));native[(int(x.Width),int(x.Height),sha(arr.tobytes()))]=arr
 covered=np.zeros(im.shape[:2],bool);modified=np.zeros_like(covered)
 for patch in report['patches']:
  if patch.get('compact_background'):continue
  key=(patch['w'],patch['h'],patch['rgb_sha256']);assert key in native
  a=native[key];xx,yy,xx1,yy1=map(int,patch['bbox_px']);covered[yy:yy1,xx:xx1]=True;modified[yy:yy1,xx:xx1]|=(a!=im[yy:yy1,xx:xx1]).any(2)
 # Evaluate faint-line samples on original paper, excluding actual source ink
 # and 2px context. No pristine font is used by the converter.
 gray=np.asarray(Image.open(src/'page00.png').convert('L'));ink=gray<225;guard=ink.copy()
 for dy in range(-2*scale,2*scale+1):
  for dx in range(-2*scale,2*scale+1):guard|=np.roll(np.roll(ink,dy,0),dx,1)
 line=np.zeros_like(covered);line[y:y+scale,x0:x1]=True;line&=~guard
 final=pdfium.PdfDocument(d/'final.pdf')[0].render(scale=math.nextafter(dpi/72,0)).to_pil();final.save(d/'pdfium.png');subprocess.run(['pdftoppm','-singlefile','-r',str(dpi),'-png',str(d/'final.pdf'),str(d/'poppler')],check=True,capture_output=True)
 rows.append({'dpi':dpi,'vector_occurrences':sum(o['owner']=='visible_tounicode' for o in report['occurrences']),'tested_faint_line_samples_outside_ink_context':int(line.sum()),'native_exact_retained':int((line&covered&~modified).sum()),'native_changed':int((line&covered&modified).sum()),'without_native_patch':int((line&~covered).sum()),'pdf_bytes':(d/'final.pdf').stat().st_size,'source_sha256':sha((d/'page00.png').read_bytes()),'pdf_sha256':sha((d/'final.pdf').read_bytes())})
(B/'hard-negative-results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
