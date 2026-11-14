#!/usr/bin/env python3
"""Run failure-injection checks against the stock PDF-import path."""
import json,os,pathlib,subprocess,time
import pikepdf
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1]; Q=P/'pilot'; ids=json.loads((P/'corpus.frozen.json').read_text())['pilot_6']; id=ids[0]; key=id.split('/')[-1]; lock=json.loads((P/'sources.lock.json').read_text())['pages'][id]; base=json.loads((B/'pilot/runs'/key/'shim-record.json').read_text()); D=B/'pilot/negative'; D.mkdir(parents=True,exist_ok=True)
results={}
for name in ['wrong_pixels','wrong_language','unexpected_psm']:
 rec=base.copy(); lang=rec['language']
 if name=='wrong_pixels':
  altered=D/'wrong-input.pdf'
  with pikepdf.open(B/lock['source_pdf_path']) as pdf:
   image=pdf.pages[0].Resources.XObject['/Im0']; raw=bytearray(image.read_bytes());raw[0]^=255;image.write(bytes(raw));pdf.save(altered,static_id=True)
 if name=='wrong_language':lang='eng'
 if name=='unexpected_psm':rec['allowed_psm']=['6']
 (D/(name+'.state')).unlink(missing_ok=True);path=D/(name+'.json');path.write_text(json.dumps(rec)); out=D/(name+'.pdf'); assert not out.exists(); env={**os.environ,'TMPDIR':str(B/'tmp'),'TESSDATA_PREFIX':str(B/'tessdata_best'),'BOOKS01_SHIM_RECORD':str(path),'BOOKS01_SHIM_STATE':str(D/(name+'.state')),'PATH':str(B/'pilot/shim')+':'+os.environ['PATH'],'OMP_THREAD_LIMIT':'1'}; cmd=['/data/coding/scanweave/work/scanweave-ab7dfba/target/release/scanweave',str(altered if name=='wrong_pixels' else B/lock['source_pdf_path']),str(out),'--dpi',str(int(lock['resolved_dpi'])),'--lang',lang]; start=time.monotonic(); proc=subprocess.run(['/usr/bin/time','-v','-o',str(D/(name+'.time'))]+cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE); (D/(name+'.log')).write_bytes(proc.stderr); results[name]={'status':proc.returncode,'output_exists':out.exists(),'rejected_by_shim':b'frozen OCR shim:' in proc.stderr,'wall_seconds':time.monotonic()-start}; assert proc.returncode!=0 and not out.exists() and results[name]['rejected_by_shim']
(Q/'results/negative-shim.json').write_text(json.dumps({'page_id':id,'tests':results},indent=2)+'\n')
