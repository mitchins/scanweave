"""Verify malformed OCR sidecars fail before any HVC-41E trial is created."""
import copy,json,os,pathlib,subprocess,tempfile
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');orig=json.loads((R/'local/ink33r/historical.pdf.json').read_text());runner=pathlib.Path(__file__).with_name('generate_review.py');out=[]
with tempfile.TemporaryDirectory(prefix='hvc41e-test-') as tmp:
 t=pathlib.Path(tmp);stub=t/'tesseract';hit=t/'ocr-called';stub.write_text('#!/bin/sh\ntouch "'+str(hit)+'"\nexit 97\n');stub.chmod(0o755);env=os.environ.copy();env['PATH']=str(t)+':'+env.get('PATH','');env['SCANWEAVE_HVC41E_CLIP_OWNERSHIP']='1'
 for name in ['missing','pdf_hash','dimensions','pixel_hash','decoded_hash','hocr_hash']:
  rec=copy.deepcopy(orig);path=t/(name+'.json')
  if name=='pdf_hash':rec['input_sha256']='0'*64
  if name=='dimensions':rec['pages'][0]['raster_width']+=1
  if name=='pixel_hash':rec['pages'][0]['pixel_sha256']='0'*64
  if name=='decoded_hash':rec['pages'][0]['native_source']['decoded_rgb_sha256']='0'*64
  if name=='hocr_hash':rec['pages'][0]['hocr_sha256']='0'*64
  if name!='missing':path.write_text(json.dumps(rec))
  run=subprocess.run(['/data/coding/scanweave/qualification/.venv/bin/python','-I',str(runner),'--sidecar',str(path)],env=env,text=True,capture_output=True);out.append({'case':name,'exit':run.returncode,'output':(run.stderr+run.stdout).strip(),'ocr_stub_invoked':hit.exists()})
  if run.returncode==0 or hit.exists():raise SystemExit('lock test failed')
(R/'hvc41e/ocr-lock-tests.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
