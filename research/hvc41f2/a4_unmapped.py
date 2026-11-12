#!/usr/bin/env python3
"""Bounded Type 3 outside-pattern extraction trials, in the authorised order."""
import ast,hashlib,json,os,pathlib,subprocess,sys,tempfile,re
import numpy as np,pikepdf,pypdfium2 as pdfium
R=pathlib.Path('/data/coding/scanweave/qualification/acr06'); E=R/'hvc41f';L=R/'local/hvc41f';D=L/'final';sha=lambda x:hashlib.sha256(x).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_A4')!='1':sys.exit('A4 switch required')
ledger=R/'hvc41e/review-decisions.json';base=R/'local/ink33r/historical.pdf';ref=R/'local/hvc41e/final/historical-composed.pdf';side=R/'local/ink33r/historical.pdf.json'
if sha(ledger.read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha(ref.read_bytes())!='9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0' or sha(base.read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b':sys.exit('frozen hash mismatch')
s=json.loads(side.read_text())
if sha((R.parent/'pdf_packaging/groups/historical-input.pdf').read_bytes())!=s['input_sha256'] or any(sha(x['hocr'].encode())!=x['hocr_sha256'] for x in s['pages']):sys.exit('OCR sidecar mismatch')
from PIL import Image
raw=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');w,h=raw.size
if [w,h]!=[s['pages'][0]['raster_width'],s['pages'][0]['raster_height']] or sha(f'SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n'.encode()+raw.tobytes())!=s['pages'][0]['pixel_sha256']:sys.exit('source mismatch')
# Import only the frozen Phase C functions; never execute its assembly.
tree=ast.parse((pathlib.Path(__file__).parent.parent/'hvc41f/phase_c.py').read_text()); funcs=ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ('quant','simplify')],type_ignores=[]);num=re.compile(r'(?<![A-Za-z0-9_.])[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?');exec(compile(funcs,'phase_c_functions','exec'))
accepted=[x for x in json.loads(ledger.read_text()) if x['decision']=='accept']; rows={x['proposal']:x for x in accepted}; indices={r['proposal']:j for j,r in enumerate(accepted,1)};outlines=json.loads((R/'local/hvc41b/interior/p000001-outlines.json').read_text())['outlines'];ids=[243,38,18]
def text(path):
 d=pdfium.PdfDocument(str(path));out=[]
 for p in d:
  t=p.get_textpage();out.append(t.get_text_range());t.close();p.close()
 d.close();return out
def search(path):
 d=pdfium.PdfDocument(str(path));p=d[0];t=p.get_textpage();out={}
 for q in ['Bacharias','Boect!','Wud','Dat','fram','Ber)']:
  a=t.search(q);hits=[]
  while (z:=a.get_next()) is not None:hits.append(list(z))
  a.close();out[q]=hits
 t.close();p.close();d.close();return out
def mupdf_text(path):
 code='import pymupdf,sys;d=pymupdf.open(sys.argv[1]);sys.stdout.buffer.write("\\f".join(p.get_text() for p in d).encode())';return subprocess.check_output(['/data/coding/scanweave/qualification/acr06/local/mupdf-venv/bin/python','-I','-c',code,str(path)])
with tempfile.TemporaryDirectory(prefix='hvc41f-a4-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=D/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(side)
 if marker.exists():sys.exit('OCR marker exists')
 bt=text(base);bp=subprocess.check_output(['pdftotext','-layout',str(base),'-']);bs=search(base);bm=mupdf_text(base);attempts=[]
 for strategy in ('no_unicode',):
  results=[]
  for i in ids:
   r=rows[i];pdf=pikepdf.open(L/f'B1-{i:03}.pdf');page=pdf.pages[0];idx=indices[i]
   with pikepdf.open(ref) as e:
    old=e.pages[0].Resources.Pattern['/Research41E'];body=old.read_bytes().splitlines()[idx-1];font=pdf.copy_foreign(old.Resources.Font.FR)
   proc=font.CharProcs[f'/g{idx}'];content=proc.read_bytes();assert content.startswith(b'2048 0 d0 ') and content.endswith(b' f');path=content[len(b'2048 0 d0 '):-2].decode();pw=float(page.MediaBox[2]);ph=float(page.MediaBox[3]);path,_=quant(path);path,_,_=simplify(path,outlines[i]['matrix'],pw,ph);proc.write(('2048 0 d0 '+path+' f').encode())
   if strategy=='artifact':body=b'/Artifact BMC\n'+body+b'\nEMC'
   elif strategy=='empty_actualtext':body=b'/Span << /ActualText <> >> BDC\n'+body+b'\nEMC'
   else:
    if '/ToUnicode' in font:del font['/ToUnicode']
    # Use an intentionally unrecognised glyph name with no Unicode mapping.
    name=pikepdf.Name('/ResearchUnmappedGlyph');font.CharProcs['/ResearchUnmappedGlyph']=font.CharProcs[f'/g{idx}'];font.Encoding.Differences[idx]=name
   form=pdf.make_stream(body);form.Type=pikepdf.Name.XObject;form.Subtype=pikepdf.Name.Form;form.BBox=pikepdf.Array(page.MediaBox);form.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(FR=font));page.Resources.XObject['/ResearchA4']=form;page.Contents[2].write(b'q /ResearchA4 Do Q');dest=D/f'A4-unmapped-{strategy}-{i:03}.pdf';pdf.save(dest);pdf.close()
   results.append({'proposal':i,'pdf':str(dest),'sha256':sha(dest.read_bytes()),'pdfium_text_equal':text(dest)==bt,'poppler_text_equal':subprocess.check_output(['pdftotext','-layout',str(dest),'-'])==bp,'pdfium_search_equal':search(dest)==bs,'mupdf_text_equal':mupdf_text(dest)==bm})
  attempts.append({'strategy':strategy,'results':results});print(strategy,[(x['proposal'],x['pdfium_text_equal'],x['poppler_text_equal'],x['pdfium_search_equal'],x['mupdf_text_equal']) for x in results],flush=True)
  if all(x['pdfium_text_equal'] and x['poppler_text_equal'] and x['pdfium_search_equal'] for x in results):break
 if marker.exists():sys.exit('OCR invoked')
(E/'a4-unmapped-attempt.json').write_text(json.dumps(attempts,indent=2)+'\n')
