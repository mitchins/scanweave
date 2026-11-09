from pathlib import Path
import subprocess,os,hashlib,json,pikepdf
base=Path('/data/coding/scanweave/qualification/acr06/local/ink37'); out=base/'gate37';rows=[];fonts={}
paths=list((out).glob('*-candidate.pdf')) + list((out).glob('controls/*.pdf'))+list((out).glob('controls-supplemental/*.pdf'))+list((out).glob('positive-controls/*.pdf'))+list((out).glob('table-candidates/*.pdf'))+[out/'table-context.pdf']
env=dict(os.environ,LD_LIBRARY_PATH='/data/coding/scanweave/tools/dist/lib')
for p in sorted(set(paths)):
 if not p.exists():continue
 q=subprocess.run(['/data/coding/scanweave/tools/dist/bin/qpdf','--check',str(p)],capture_output=True,text=True,env=env)
 row={'file':str(p),'qpdf_exit':q.returncode,'qpdf_output':q.stdout+q.stderr,'fonts':[]}
 with pikepdf.open(p) as pdf:
  for obj in pdf.objects:
   try:
    for k in ('/FontFile','/FontFile2','/FontFile3'):
     if k in obj:
      data=obj[k].read_bytes(); digest=hashlib.sha256(data).hexdigest();row['fonts'].append(digest)
      if digest not in fonts:
       path=out/f'{digest}.font';path.write_bytes(data);r=subprocess.run(['/data/coding/scanweave/tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize',str(path)],capture_output=True,text=True);fonts[digest]={'exit':r.returncode,'output':r.stdout+r.stderr}
   except (ValueError,TypeError,AttributeError):pass
 row['fonts']=sorted(set(row['fonts']));rows.append(row);print(p.name,q.returncode,flush=True)
Path('/data/coding/scanweave/qualification/acr06/ink37/polarity37/gate-pdf-checks.json').write_text(json.dumps({'pdfs':rows,'fonts':fonts},indent=2)+'\n')
