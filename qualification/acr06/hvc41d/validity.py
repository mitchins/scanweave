import pathlib,subprocess,os,json,hashlib
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41d';E=R/'hvc41d';env=os.environ.copy();env['LD_LIBRARY_PATH']='/data/coding/scanweave/tools/dist/lib';out={}
for name,path in [('rejected_trial',L/'historical-rejected-243.pdf'),('retained_baseline',L/'historical-candidate.pdf')]:
 q=subprocess.run(['/data/coding/scanweave/tools/dist/bin/qpdf','--check',str(path)],env=env,text=True,capture_output=True);t=subprocess.check_output(['pdftotext','-f','1','-l','1','-enc','UTF-8',str(path),'-']).decode();fonts=subprocess.check_output(['pdffonts',str(path)]).decode();out[name]={'qpdf_exit':q.returncode,'qpdf_output':(q.stdout+q.stderr).strip(),'poppler_search_Bacharias_count':t.count('Bacharias'),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pdffonts':fonts}
(E/'validity.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
