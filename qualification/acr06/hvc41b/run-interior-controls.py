import json,pathlib,subprocess,os,sys,hashlib
import numpy as np,pypdfium2 as pdfium
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41b';old=R/'local/ink37';rows=json.loads((R/'hvc41b/control-admission.json').read_text());folders={'control':('controls','control-measured'),'supplemental':('controls-supplemental','control-supplemental-measured'),'positive':('positive-controls','control-positive-measured')};out=[]
for row in rows:
 group=row['set'];name=row['case'];folder,measure=folders[group];src=old/folder/f'{name}.pdf';side=old/measure/f'{name}.pdf.json';dest=L/'controls'/group/name;basepdf=dest/'baseline.pdf';testpdf=dest/'interior-probe.pdf';env=os.environ.copy()
 for k in ['SCANWEAVE_HVC41_INTERIOR','SCANWEAVE_HVC41_PIXEL_CONTACT','SCANWEAVE_HVC41_DUMP_DIR','SCANWEAVE_HVC41B_TRACE_DIR']:env.pop(k,None)
 env['PATH']='/tmp/hvc41b-noocr:'+env['PATH'];env['SCANWEAVE_PDFIUM_LIBRARY']='/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so';env['SCANWEAVE_HVC41B_OCR_SIDECAR']=str(side);env['SCANWEAVE_HVC41B_INTERIOR']='1';env['SCANWEAVE_HVC41B_BORDER_CONTACT']='1'
 cmd=['/usr/bin/time','-v','-o',str(dest/'interior-probe.time'),'/tmp/scanweave-hvc41/target/release/scanweave',str(src),str(testpdf),'--dpi','300','--profile','clearscan','--glyph-sharing','off']
 with (dest/'interior-probe.log').open('w') as f:rc=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
 if rc:print('STOP execution',group,name,rc,flush=True);sys.exit(rc)
 a,b=[pdfium.PdfDocument(str(p)) for p in (basepdf,testpdf)];pa,pb=a[0],b[0];ta,tb=pa.get_textpage(),pb.get_textpage();pdftext=ta.get_text_range()==tb.get_text_range();ta.close();tb.close();diffs={}
 for dpi in (96,300):
  xa=np.asarray(pa.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB'));xb=np.asarray(pb.render(scale=dpi/72,rev_byteorder=True).to_pil().convert('RGB'));diffs[str(dpi)]=int(np.any(xa!=xb,axis=2).sum()) if xa.shape==xb.shape else None
 pa.close();pb.close();a.close();b.close();texts=[subprocess.run(['pdftotext',str(p),'-'],check=True,stdout=subprocess.PIPE).stdout for p in (basepdf,testpdf)];x={'set':group,'case':name,'changed_pixels_pdfium':diffs,'pdfium_text_identical':pdftext,'poppler_text_identical':texts[0]==texts[1],'baseline_bytes':basepdf.stat().st_size,'probe_bytes':testpdf.stat().st_size,'baseline_sha256':hashlib.sha256(basepdf.read_bytes()).hexdigest(),'probe_sha256':hashlib.sha256(testpdf.read_bytes()).hexdigest()};out.append(x);(R/'hvc41b/interior-control-replay.json').write_text(json.dumps(out,indent=2)+'\n');print(group,name,x,flush=True)
 if not pdftext or texts[0]!=texts[1] or any(v!=0 for v in diffs.values()):print('STOP changed control',group,name,flush=True);sys.exit(2)
print('COMPLETE',len(out),flush=True)
