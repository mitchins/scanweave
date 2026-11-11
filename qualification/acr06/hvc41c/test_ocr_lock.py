import copy,hashlib,json,pathlib,subprocess,tempfile,sys
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41c';L=R/'local/hvc41c';src=R/'local/ink37/controls/white.pdf';side=R/'local/ink37/control-measured/white.pdf.json';runner=E/'locked_run.py';data=json.loads(side.read_text());out=[]
with tempfile.TemporaryDirectory(dir=L) as temp:
 t=pathlib.Path(temp)
 for kind in ('missing','source_hash','dimensions','pixel_hash','hocr_hash','valid'):
  d=copy.deepcopy(data);path=t/f'{kind}.json';output=t/f'{kind}.pdf'
  if kind=='source_hash':d['input_sha256']='0'*64
  if kind=='dimensions':d['pages'][0]['raster_width']+=1
  if kind=='pixel_hash':d['pages'][0]['pixel_sha256']='0'*64
  if kind=='hocr_hash':d['pages'][0]['hocr_sha256']='0'*64
  if kind!='missing':path.write_text(json.dumps(d))
  r=subprocess.run([sys.executable,'-I',str(runner),str(src),str(output),'--sidecar',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);valid=kind=='valid';ok=(r.returncode==0 and output.exists() and 'Tesseract stub not invoked' in r.stderr) if valid else (r.returncode!=0 and not output.exists());out.append({'case':kind,'exit':r.returncode,'pass':ok,'output_exists':output.exists(),'stderr_tail':r.stderr[-500:]});print(kind,'PASS' if ok else 'FAIL',flush=True)
  if not ok:raise SystemExit(1)
(E/'ocr-lock-tests.json').write_text(json.dumps(out,indent=2)+'\n')
