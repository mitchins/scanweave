#!/usr/bin/env python3
"""Path-only outside-pattern diagnostic, isolated from A0–A2."""
import hashlib,json,os,pathlib,sys,tempfile
import pikepdf
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f';sha=lambda x:hashlib.sha256(x).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_PHASE_A3')!='1':sys.exit('research switch required')
if sha((R/'hvc41e/review-decisions.json').read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha((R/'local/hvc41e/final/historical-composed.pdf').read_bytes())!='9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0' or sha((R/'local/ink33r/historical.pdf').read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b':sys.exit('frozen hash mismatch')
side=R/'local/ink33r/historical.pdf.json';s=json.loads(side.read_text())
if sha((R.parent/'pdf_packaging/groups/historical-input.pdf').read_bytes())!=s['input_sha256'] or any(sha(p['hocr'].encode())!=p['hocr_sha256'] for p in s['pages']):sys.exit('sidecar mismatch')
with tempfile.TemporaryDirectory(prefix='hvc41f-a3-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=L/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(side)
 rows=[]
 for r in json.loads((E/'phase-a-variants.json').read_text()):
  if r['variant']!='A2':continue
  if sha(pathlib.Path(r['path']).read_bytes())!=r['sha256']:sys.exit('A2 hash mismatch')
  pdf=pikepdf.open(r['path']);page=pdf.pages[0];pattern=page.Resources.Pattern['/Research41E'];body=pattern.read_bytes();patch=page.Contents[1].read_bytes();form=pdf.make_stream(body);form.Type=pikepdf.Name.XObject;form.Subtype=pikepdf.Name.Form;form.BBox=pikepdf.Array(page.MediaBox);form.Resources=pikepdf.Dictionary();page.Resources.XObject['/Research41F']=form;page.Contents[2].write(b'q /Research41F Do Q');p=L/f'A3-{r["proposal"]:03}.pdf';pdf.save(p);pdf.close()
  with pikepdf.open(p) as chk:
   if chk.pages[0].Contents[1].read_bytes()!=patch:sys.exit('patch changed')
  rows.append({'proposal':r['proposal'],'variant':'A3','path':str(p),'sha256':sha(p.read_bytes()),'patch_sha256':sha(patch)})
 if marker.exists():sys.exit('OCR invoked')
(E/'phase-a3-variants.json').write_text(json.dumps(rows,indent=2)+'\n');print('A3 prepared',len(rows))
