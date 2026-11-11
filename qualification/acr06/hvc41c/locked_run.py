#!/usr/bin/env python3
"""HVC-41C runner. Frozen OCR is mandatory and all OCR execution is forbidden."""
import argparse,hashlib,json,os,pathlib,subprocess,sys,tempfile
p=argparse.ArgumentParser();p.add_argument('input',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);p.add_argument('--sidecar',required=True,type=pathlib.Path);p.add_argument('--time-file',type=pathlib.Path);a=p.parse_args()
if not a.sidecar.is_file():sys.exit('HVC-41C: missing frozen OCR sidecar')
data=json.loads(a.sidecar.read_text());h=lambda b:hashlib.sha256(b).hexdigest()
if h(a.input.read_bytes())!=data.get('input_sha256'):sys.exit('HVC-41C: source PDF hash mismatch')
for page in data.get('pages',[]):
 if h(page.get('hocr','').encode())!=page.get('hocr_sha256'):sys.exit('HVC-41C: hOCR hash mismatch')
if not data.get('pages'):sys.exit('HVC-41C: no frozen OCR pages')
with tempfile.TemporaryDirectory(prefix='hvc41c-noocr-') as td:
 t=pathlib.Path(td);stub=t/'tesseract';marker=t/'ocr-invoked';stub.write_text('#!/bin/sh\necho invoked > "$SCANWEAVE_HVC41C_OCR_MARKER"\nexit 97\n');stub.chmod(0o755);env=os.environ.copy()
 for k in list(env):
  if k.startswith('SCANWEAVE_HVC41B_') or k in ('SCANWEAVE_HVC41_INTERIOR','SCANWEAVE_HVC41_PIXEL_CONTACT','SCANWEAVE_HVC41_DUMP_DIR'):env.pop(k,None)
 env.update({'PATH':str(t)+':'+env.get('PATH',''),'SCANWEAVE_HVC41C_LOCK_OCR':'1','SCANWEAVE_HVC41C_OCR_SIDECAR':str(a.sidecar),'SCANWEAVE_HVC41C_OCR_MARKER':str(marker),'SCANWEAVE_PDFIUM_LIBRARY':'/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so'})
 cmd=['/tmp/scanweave-hvc41/target/release/scanweave',str(a.input),str(a.output),'--dpi','300','--profile','clearscan','--glyph-sharing','off']
 if a.time_file:cmd=['/usr/bin/time','-v','-o',str(a.time_file)]+cmd
 result=subprocess.run(cmd,env=env)
 if marker.exists():sys.exit('HVC-41C: forbidden OCR process invoked')
 print('HVC-41C: Tesseract stub not invoked',file=sys.stderr)
 sys.exit(result.returncode)
