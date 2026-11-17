"""Run the research-only coverage experiment on exactly the frozen 36 dev pages."""
import collections,difflib,hashlib,json,os,pathlib,statistics,subprocess,sys,time
import numpy as np
import pypdfium2 as pdfium
B=pathlib.Path('/data/coding/scanweave/work/books01');O=B/'stroke02';R=O/'pages-extensions';Q=pathlib.Path('/tmp/scanweave-books01/qualification/books01');SW=str(O/'target/release/scanweave');PY='/data/coding/scanweave/qualification/.venv/bin/python';corpus=json.loads((Q/'corpus.frozen.json').read_text());pages=[p for p in corpus['pages'] if p['split']=='dev'];assert len(pages)==36 and len({p['id'] for p in pages})==36
baseenv={**os.environ,'TMPDIR':str(O/'tmp'),'TESSDATA_PREFIX':str(B/'tessdata_best'),'OMP_THREAD_LIMIT':'1','OPENBLAS_NUM_THREADS':'1'}
def text_pdf(path):
 doc=pdfium.PdfDocument(str(path));page=doc[0];tp=page.get_textpage();return tp.get_text_range()
def stats(report):
 data=json.loads(pathlib.Path(report).read_text())['conversion'];r=data['page_reports'][0];coverage=r['coverage'];vec=sum(x['units'] for x in r['regions'] if x['disposition']=='Vector');ras=sum(x['units'] for x in r['regions'] if isinstance(x['disposition'],dict) and 'Raster' in x['disposition']);return {'raster_bytes':data['raster_encoded_bytes'],'coverage':coverage,'vector_units_proposed':vec,'raster_units_proposed':ras,'selected':data['selected'],'regions':[{'id':x['id'],'units':x['units'],'disposition':x['disposition']} for x in r['regions']]}
def pix(path):
 doc=pdfium.PdfDocument(str(path));page=doc[0];page.render(scale=150/72).to_pil();t=[];im=None
 for _ in range(3):
  start=time.perf_counter();im=page.render(scale=150/72).to_pil().convert('RGB');t.append(time.perf_counter()-start)
 return np.asarray(im),statistics.median(t)
def run_page(record):
 key=record['id'].split('/')[-1];d=R/key;d.mkdir(parents=True,exist_ok=True);out=d/'metrics.json'
 if out.exists():return json.loads(out.read_text())
 run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());baseline=pathlib.Path(run['rows']['sw-E']['path']);src=run['rows']['src']['path'];saved=run['rows']['sw-E']['argv'];assert saved[1]==src and saved[3:]==['--dpi',str(run['dpi']),'--lang',run['lang']];assert hashlib.sha256(pathlib.Path(src).read_bytes()).hexdigest()==run['source_pdf_sha256']
 log=d/'prepass.log';t0=time.monotonic()
 with log.open('wb') as f:p=subprocess.run([PY,'-I','-B',str(pathlib.Path(__file__).with_name('coverage_prepass.py')),key],env=baseenv,stdout=f,stderr=subprocess.STDOUT)
 row={'id':record['id'],'prepass_status':p.returncode,'prepass_wall_seconds':time.monotonic()-t0,'baseline_pdf_bytes':baseline.stat().st_size,'baseline_wall_seconds':run['rows']['sw-E']['wall_seconds']}
 if p.returncode:row['status']='prepass failed';out.write_text(json.dumps(row,indent=2));return row
 candidate=d/'candidate.pdf';cmd=[SW,src,str(candidate),*saved[3:]];env={**baseenv,'SCANWEAVE_STROKE_COVERAGE':str(d/'coverage.png')};t0=time.monotonic()
 with (d/'candidate.log').open('wb') as f:p=subprocess.run(['/usr/bin/time','-v','-o',str(d/'candidate.time'),*cmd],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
 row.update({'status':p.returncode,'candidate_wall_seconds':time.monotonic()-t0,'candidate_argv':cmd})
 if p.returncode or not candidate.exists():out.write_text(json.dumps(row,indent=2));return row
 bt=text_pdf(baseline);ct=text_pdf(candidate);cb,cc=collections.Counter(bt),collections.Counter(ct);removed=cb-cc;added=cc-cb
 row['text_diff']={'same':bt==ct,'removed_characters':sum(removed.values()),'added_characters':sum(added.values()),'whitespace_only':' '.join(bt.split())==' '.join(ct.split()) and bt!=ct,'order_only':bt!=ct and cb==cc,'baseline_ufffe':bt.count('\ufffe'),'candidate_ufffe':ct.count('\ufffe'),'new_ufffe':max(0,ct.count('\ufffe')-bt.count('\ufffe'))}
 nonspace_old=collections.Counter(''.join(bt.split()));nonspace_new=collections.Counter(''.join(ct.split()));row['text_diff']['nonwhitespace_removed']=sum((nonspace_old-nonspace_new).values());row['text_diff']['nonwhitespace_added']=sum((nonspace_new-nonspace_old).values());row['text_diff']['nonwhitespace_order_changed']=(''.join(bt.split())!=''.join(ct.split()) and nonspace_old==nonspace_new)
 row['baseline']=stats(str(baseline)+'.json');row['candidate']=stats(str(candidate)+'.json');row['candidate_pdf_bytes']=candidate.stat().st_size
 def owners(path):
  report=json.loads(pathlib.Path(str(path)+'.json').read_text())['conversion']['page_reports'][0]
  return {(x['span_id'],x['symbol_id']):x['owner'] for x in report['occurrences'] if x['owner']!='unmapped'}
 old,new=owners(baseline),owners(candidate);row['ownership_moves']=dict(collections.Counter(old[k]+' -> '+new[k] for k in old.keys()&new.keys() if old[k]!=new[k]))
 ledger=d/'extensions.json'
 if ledger.exists():
  v=json.loads(ledger.read_text());row['extensions']={k:v[k] for k in ('attempted','accepted','rejected_neighbour','rejected_disconnected','rejected_overlap','rejected_box','rejected_veto')};row['extensions']['pixels']=sum(map(len,v['pixels'].values()))
 row['changed_region_dispositions']=sum(x!=y for x,y in zip(row['baseline']['regions'],row['candidate']['regions']))+abs(len(row['baseline']['regions'])-len(row['candidate']['regions']))
 a,at=pix(baseline);b,btm=pix(candidate);row['baseline_render_median_seconds']=at;row['candidate_render_median_seconds']=btm
 if a.shape==b.shape:
  delta=np.abs(a.astype(np.int16)-b.astype(np.int16));row['render_diff_150dpi']={'mean_absolute_channel_delta':float(delta.mean()),'changed_pixel_fraction':float(np.mean(np.any(delta>0,axis=2))),'max_channel_delta':int(delta.max())}
 else:row['render_diff_150dpi']={'shape_mismatch':[list(a.shape),list(b.shape)]}
 row['candidate_sha256']=hashlib.sha256(candidate.read_bytes()).hexdigest();out.write_text(json.dumps(row,indent=2));return row
if __name__=='__main__':
 for page in pages:
  try:
   result=run_page(page);print(result['id'],result['status'],'new_ufffe',result.get('text_diff',{}).get('new_ufffe'),flush=True)
  except Exception as e:
   result={'id':page['id'],'status':'exception','error':repr(e)};print(json.dumps(result),flush=True)
   (R/page['id'].split('/')[-1]/'metrics.json').write_text(json.dumps(result,indent=2))
