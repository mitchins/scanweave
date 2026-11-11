import pathlib,pikepdf,hashlib,subprocess,json
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41d';E=R/'hvc41d';f=L/'historical-rejected-243.pdf';pdf=pikepdf.open(f);rows=[];seen=set()
for page,pg in enumerate(pdf.pages,1):
 for name,font in pg.Resources.get('/Font',pikepdf.Dictionary()).items():
  for ff in font.get('/DescendantFonts',[]):
   desc=ff.get('/FontDescriptor',pikepdf.Dictionary())
   for key in ['/FontFile','/FontFile2','/FontFile3']:
    if key not in desc:continue
    b=desc[key].read_bytes();sha=hashlib.sha256(b).hexdigest()
    if sha in seen:continue
    seen.add(sha);path=L/f'font-{sha}.ttf';path.write_bytes(b);p=subprocess.run(['/data/coding/scanweave/tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize',str(path)],capture_output=True,text=True);rows.append({'page':page,'font':str(name),'sha256':sha,'ots_exit':p.returncode,'output':(p.stdout+p.stderr).strip()})
(E/'ots-checks.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows)
