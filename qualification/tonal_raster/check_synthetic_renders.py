from pathlib import Path
import sys,json,hashlib,subprocess,tempfile
import pypdfium2 as pdfium
B=Path(__file__).resolve().parent;R=B.parents[1];rows=[]
for dpi in [300,600]:
 p=B/str(dpi)/'final.pdf'
 if not p.exists():p=next((B/str(dpi)).glob('*.pdf'))
 ref=R/'qualification/real_convergence'/str(dpi)/'final.pdf'
 assert p.read_bytes()==ref.read_bytes()
 d=pdfium.PdfDocument(str(p));hashes=[]
 for page in d:
  bitmap=page.render(scale=1);hashes.append(hashlib.sha256(bitmap.to_pil().tobytes()).hexdigest());bitmap.close();page.close()
 text=''.join(page.get_textpage().get_text_range() for page in d)
 d.close()
 with tempfile.TemporaryDirectory(prefix='scanweave-tonal-render-') as folder:
  out=Path(folder)/f'tonal-synthetic-{dpi}'
  subprocess.run(['pdftoppm','-r','72','-png',str(p),str(out)],check=True,capture_output=True,timeout=300)
  files=sorted(out.parent.glob(out.name+'-*.png'));assert len(files)==len(hashes)
  pop=subprocess.check_output(['pdftotext',str(p),'-'],timeout=300)
  rows.append({'dpi':dpi,'bytes':p.stat().st_size,'byte_identical_frozen':True,'pdfium_render_hashes':hashes,'poppler_render_hashes':[hashlib.sha256(f.read_bytes()).hexdigest() for f in files],'pdfium_text_characters':len(text),'poppler_text_bytes':len(pop)})
  for f in files:f.unlink()
(B/'synthetic-render-checks.json').write_text(json.dumps(rows,indent=2))
