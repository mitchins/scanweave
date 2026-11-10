import json,pathlib,subprocess,os,hashlib,sys
R=pathlib.Path('/data/coding/scanweave/qualification/acr06'); L=R/'local/hvc41b'; old=R/'local/ink37'; rows=json.loads((R/'hvc41b/control-admission.json').read_text());out=[];folders={'control':('controls','control-measured'),'supplemental':('controls-supplemental','control-supplemental-measured'),'positive':('positive-controls','control-positive-measured')};tool=pathlib.Path('/tmp/hvc41b-noocr');tool.mkdir(exist_ok=True);(tool/'tesseract').write_text('#!/bin/sh\necho FORBIDDEN_OCR >&2\nexit 99\n');(tool/'tesseract').chmod(0o755)
for row in rows:
 group=row['set'];name=row['case'];folder,measure=folders[group];src=old/folder/f'{name}.pdf';side=old/measure/f'{name}.pdf.json';dest=L/'controls'/group/name;dest.mkdir(parents=True,exist_ok=True);base=os.environ.copy()
 for k in ['SCANWEAVE_HVC41_INTERIOR','SCANWEAVE_HVC41_PIXEL_CONTACT','SCANWEAVE_HVC41_DUMP_DIR','SCANWEAVE_HVC41B_INTERIOR','SCANWEAVE_HVC41B_BORDER_CONTACT','SCANWEAVE_HVC41B_TRACE_DIR']:base.pop(k,None)
 base['PATH']=str(tool)+':'+base['PATH'];base['SCANWEAVE_PDFIUM_LIBRARY']='/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so';base['SCANWEAVE_HVC41B_OCR_SIDECAR']=str(side);cases=[]
 for variant in ('baseline','border'):
  env=base.copy();pdf=dest/f'{variant}.pdf';log=dest/f'{variant}.log';tm=dest/f'{variant}.time'
  if variant=='border':env['SCANWEAVE_HVC41B_BORDER_CONTACT']='1';env['SCANWEAVE_HVC41B_TRACE_DIR']=str(dest)
  cmd=['/usr/bin/time','-v','-o',str(tm),'/tmp/scanweave-hvc41/target/release/scanweave',str(src),str(pdf),'--dpi','300','--profile','clearscan','--glyph-sharing','off']
  with log.open('w') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
  if r.returncode:print('STOP',group,name,variant,'exit',r.returncode,flush=True);sys.exit(r.returncode)
  cases.append({'variant':variant,'bytes':pdf.stat().st_size,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()})
 same=cases[0]['sha256']==cases[1]['sha256'];out.append({'set':group,'case':name,'outputs':cases,'byte_identical':same});(R/'hvc41b/control-replay.json').write_text(json.dumps(out,indent=2)+'\n');print(group,name,'identical',same,flush=True)
 if not same:print('STOP: changed control',group,name,flush=True);sys.exit(1)
print('COMPLETE',len(out),flush=True)
