"""Fail-closed tests for the one-shot offline research runner; no conversion or OCR."""
import tempfile,pathlib,subprocess,json,os,copy
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');script=pathlib.Path(__file__).with_name('pilot_preflight.py');orig=json.loads((R/'local/ink33r/historical.pdf.json').read_text());input=R/'../pdf_packaging/groups/historical-input.pdf';baseline=R/'local/ink33r/historical.pdf';results=[]
with tempfile.TemporaryDirectory() as td:
 t=pathlib.Path(td);stub=t/'tesseract';hit=t/'called';stub.write_text('#!/bin/sh\ntouch "'+str(hit)+'"\nexit 97\n');stub.chmod(0o755);env=os.environ.copy();env['PATH']=str(t)+':'+env['PATH']
 for name in ['missing','pdf_hash','dimension','pixel_hash','hocr_hash','decoded_hash']:
  o=copy.deepcopy(orig);side=t/(name+'.json')
  if name=='pdf_hash':o['input_sha256']='0'*64
  if name=='dimension':o['pages'][0]['raster_width']+=1
  if name=='pixel_hash':o['pages'][0]['pixel_sha256']='0'*64
  if name=='hocr_hash':o['pages'][0]['hocr_sha256']='0'*64
  if name=='decoded_hash':o['pages'][0]['native_source']['decoded_rgb_sha256']='0'*64
  if name!='missing':side.write_text(json.dumps(o))
  p=subprocess.run(['/data/coding/scanweave/qualification/.venv/bin/python','-I',str(script),'--sidecar',str(side),'--input',str(input),'--baseline',str(baseline)],env=env,capture_output=True,text=True);results.append({'case':name,'returncode':p.returncode,'message':(p.stderr+p.stdout).strip(),'stub_invoked':hit.exists()});print(results[-1])
  if p.returncode==0 or hit.exists():raise SystemExit('OCR lock regression failed')
(R/'hvc41d/ocr-lock-regression.json').write_text(json.dumps(results,indent=2)+'\n')
