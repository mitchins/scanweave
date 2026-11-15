#!/usr/bin/env python3
"""Phase 2 stock CLI runs on frozen dev PDFs only; resume after interruption."""
import concurrent.futures,hashlib,json,os,pathlib,subprocess,time,traceback
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];D=B/'phase2';lock=json.loads((P/'sources.lock.json').read_text())['pages']; corpus=json.loads((P/'corpus.frozen.json').read_text());pages=[p for p in corpus['pages'] if p['split']=='dev'];assert len(pages)==36 and len({x['id'] for x in pages})==36;pilot=json.loads((P/'pilot/results/runs.json').read_text());SW='/data/coding/scanweave/work/scanweave-ab7dfba/target/release/scanweave';V='/data/coding/scanweave/qualification/.venv/bin';sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest();assert sha(SW)=='53908c50537e5cdcf2ee5bf84d6ca5f56ca4c6c2560ca43aade0c8deee4914c9';env={**os.environ,'TMPDIR':str(B/'tmp'),'TESSDATA_PREFIX':str(B/'tessdata_best'),'OMP_THREAD_LIMIT':'1','OPENBLAS_NUM_THREADS':'1','PATH':V+':'+os.environ['PATH']}
def invoke(cmd,d,row):
 start=time.monotonic();o=d/(row+'.pdf');tf=d/(row+'.time');log=d/(row+'.log')
 try:
  with log.open('wb') as f:r=subprocess.run(['/usr/bin/time','-v','-o',str(tf)]+cmd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  status=r.returncode
 except Exception as e:status=None;log.write_text(repr(e))
 return {'status':status,'wall_seconds':time.monotonic()-start,'argv':cmd,'path':str(o),'time_file':str(tf),'log_file':str(log),'output_sha256':sha(o) if status==0 and o.exists() else None}
def run(p):
 id=p['id'];k=id.split('/')[-1];src=B/lock[id]['source_pdf_path'];assert sha(src)==lock[id]['source_pdf_sha256'];d=D/'runs'/k;d.mkdir(parents=True,exist_ok=True);resultfile=d/'runs.json'
 if resultfile.exists():return
 base={'id':id,'dpi':int(lock[id]['resolved_dpi']),'lang':lock[id]['language'],'source_pdf_sha256':sha(src),'rows':{'src':{'status':0,'path':str(src),'output_sha256':sha(src)}}}
 try:
  if id in pilot:
   for row in ['sw-E','mrc-M','ocrmypdf-E']:
    x=pilot[id]['rows'][row].copy();x['path']=str(B/'pilot/runs'/k/(row+'.pdf'));assert x['status']==0 and sha(x['path'])==x['output_sha256'];x['reused_pilot']=True;base['rows'][row]=x
   report=B/'pilot/runs'/k/'sw-E.pdf.json';assert json.loads(report.read_text())['input_sha256']==sha(src)
  else:
   dpi=str(base['dpi']);lang=base['lang'];sw=d/'sw-E.pdf';base['rows']['sw-E']=invoke([SW,str(src),str(sw),'--dpi',dpi,'--lang',lang],d,'sw-E');report=d/'sw-E.pdf.json'
   if report.exists() and base['rows']['sw-E']['status']==0:
    page=json.loads(report.read_text())['pages'][0];h=page['hocr'];assert hashlib.sha256(h.encode()).hexdigest()==page['hocr_sha256'];(d/'selected.hocr').write_text(h);base['rows']['mrc-M']=invoke([V+'/recode_pdf','-P',str(src),'-T',str(d/'selected.hocr'),'-o',str(d/'mrc-M.pdf'),'--mask-compression','ccitt','--threads','1'],d,'mrc-M')
   else:base['rows']['mrc-M']={'status':None,'error':'ScanWeave report missing'}
   base['rows']['ocrmypdf-E']=invoke([V+'/ocrmypdf','--output-type','pdf','-l',lang,str(src),str(d/'ocrmypdf-E.pdf')],d,'ocrmypdf-E')
  if report.exists():
   obj=json.loads(report.read_text()); pg=obj['pages'][0];h=pg['hocr'];assert hashlib.sha256(h.encode()).hexdigest()==pg['hocr_sha256'];(d/'selected.hocr').write_text(h);base['selected_psm']=pg['selected_psm'];base['hocr_sha256']=pg['hocr_sha256'];base['raster_import']=pg['raster_import']
 except Exception as e:base['error']=repr(e);base['traceback']=traceback.format_exc()
 resultfile.write_text(json.dumps(base,indent=2)+'\n');print(id,[(k,v.get('status')) for k,v in base['rows'].items()],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,pages))
print('CLI BATCH FINISHED',flush=True)
