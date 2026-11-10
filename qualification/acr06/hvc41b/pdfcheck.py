import pathlib,subprocess,os,json,pikepdf,hashlib
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41b';p=L/'final/historical.pdf';env=dict(os.environ,LD_LIBRARY_PATH='/data/coding/scanweave/tools/dist/lib');q=subprocess.run(['/data/coding/scanweave/tools/dist/bin/qpdf','--check',str(p)],capture_output=True,text=True,env=env);fonts={}
with pikepdf.open(p) as doc:
 for obj in doc.objects:
  try:
   for k in ('/FontFile','/FontFile2','/FontFile3'):
    if k in obj:
     b=obj[k].read_bytes();h=hashlib.sha256(b).hexdigest()
     if h not in fonts:
      f=L/f'{h}.font';f.write_bytes(b);r=subprocess.run(['/data/coding/scanweave/tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize',str(f)],cwd=L,capture_output=True,text=True);fonts[h]={'exit':r.returncode,'output':r.stdout+r.stderr}
  except (ValueError,TypeError,AttributeError):pass
(R/'hvc41b/pdf-check.json').write_text(json.dumps({'qpdf_exit':q.returncode,'qpdf_output':q.stdout+q.stderr,'fonts':fonts},indent=2)+'\n');print('qpdf',q.returncode,'fonts',[(k,v['exit']) for k,v in fonts.items()])
