#!/usr/bin/env python3
"""Run only the frozen six pages; never invoke Adobe or touch holdout files."""
import concurrent.futures,json,os,pathlib,shutil,subprocess,time
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]; Q=P/'pilot'; ids=json.loads((P/'corpus.frozen.json').read_text())['pilot_6']; lock=json.loads((P/'sources.lock.json').read_text())['pages']; frozen=json.loads((Q/'results/frozen-ocr-index.json').read_text())['pages']; assert len(ids)==6
SW='/data/coding/scanweave/work/scanweave-ab7dfba/target/release/scanweave'; V='/data/coding/scanweave/qualification/.venv/bin'; D=B/'pilot'; shimdir=D/'shim';shimdir.mkdir(parents=True,exist_ok=True); shutil.copy2(Q/'tesseract_shim.py',shimdir/'tesseract'); (shimdir/'tesseract').chmod(0o755)
base={**os.environ,'TMPDIR':str(B/'tmp'),'TESSDATA_PREFIX':str(B/'tessdata_best'),'OMP_THREAD_LIMIT':'1','PATH':V+':'+os.environ['PATH']}
def invoke(cmd,env,prefix):
 prefix.parent.mkdir(parents=True,exist_ok=True); start=time.monotonic()
 with open(str(prefix)+'.log','wb') as log:
  try: p=subprocess.run(['/usr/bin/time','-v','-o',str(prefix)+'.time']+cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=900); status=p.returncode
  except subprocess.TimeoutExpired:status=None
 return {'argv':cmd,'status':status,'wall_seconds':time.monotonic()-start,'time_file':str(prefix)+'.time','log_file':str(prefix)+'.log'}
def run(id):
 p=lock[id]; f=frozen[id]; key=id.split('/')[-1]; d=D/'runs'/key;d.mkdir(parents=True,exist_ok=True); src=str(B/p['source_pdf_path']); dpi=str(int(p['resolved_dpi'])); lang=p['language']; png=str(B/'ocr-frozen'/key/'page.png'); rec={'language':lang,'dpi':int(dpi),'decoded_pixel_sha256':p['decoded_pixel_sha256'],'hocr':{},'sha256':{}}
 for n in ['3','6']:
  rec['hocr'][n]=str(B/'ocr-frozen'/key/f'psm{n}-1.hocr');rec['sha256'][n]=f['runs'][n]['repeat'][0]['output_sha256']
 record=d/'shim-record.json'; record.write_text(json.dumps(rec)); state=d/'shim-state'; state.unlink(missing_ok=True); env={**base,'PATH':str(shimdir)+':'+base['PATH'],'BOOKS01_SHIM_RECORD':str(record),'BOOKS01_SHIM_STATE':str(state)}; rows={}
 for row,environment in [('sw-E',base),('sw-M',env)]:
  out=d/(row+'.pdf'); rows[row]=invoke([SW,src,str(out),'--dpi',dpi,'--lang',lang],environment,d/row)
  if rows[row]['status']!=0 or not out.exists():print(id,row,'failed',flush=True)
 report=d/'sw-M.pdf.json'
 if report.exists():
  raw=json.loads(report.read_text()); selected=str(raw['pages'][0]['selected_psm']); hocr=rec['hocr'][selected]
  rows['sw-build']=invoke([SW,'build',png,'--ocr',hocr,'--dpi',dpi,'--profile','clearscan','--output',str(d/'sw-build.pdf'),'--report',str(d/'sw-build.report.json')],base,d/'sw-build')
  rows['mrc-M']=invoke([V+'/recode_pdf','-P',src,'-T',hocr,'-o',str(d/'mrc-M.pdf'),'--mask-compression','ccitt','--threads','1'],base,d/'mrc-M')
 else: selected=None; rows['sw-build']={'status':None,'error':'sw-M failed'};rows['mrc-M']={'status':None,'error':'sw-M failed'}
 rows['ocrmypdf-E']=invoke([V+'/ocrmypdf','--output-type','pdf','-l',lang,src,str(d/'ocrmypdf-E.pdf')],base,d/'ocrmypdf-E')
 rows['adobe-E']={'path':str(B/'runs/adobe'/(key+'.adobe.pdf')),'source':'existing GUI output'}; rows['src']={'path':src}; result={'id':id,'source_type':p['source_type'],'dpi':int(dpi),'dpi_confidence':p['dpi_evidence']['confidence'],'selected_psm':selected,'rows':rows}; (d/'runs.json').write_text(json.dumps(result,indent=2)+'\n');print(id,' '.join(f'{k}={v.get("status")}' for k,v in rows.items()),flush=True);return id,result
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex: results=dict(ex.map(run,ids))
(Q/'results/runs.json').write_text(json.dumps(results,indent=2)+'\n')
