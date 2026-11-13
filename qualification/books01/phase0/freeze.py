#!/usr/bin/env python3
"""Record selected pages and byte-only holdout evidence; no holdout decoding."""
import hashlib,json,pathlib,subprocess,os
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]
corpus=json.loads((P/'corpus.proposed.json').read_text()); inv=json.loads((B/'inventory.unfrozen.json').read_text())['pages']; lock=json.loads((P/'sources.lock.json').read_text())
lock['sealed_holdout']={p['id']:inv[p['id']]['files'] for p in corpus['pages'] if p['split']=='holdout'}
(P/'sources.lock.json').write_text(json.dumps(lock,indent=2,ensure_ascii=False)+'\n')
pilot=['quiver/aventinus_grammatica_1515_0008','quiver/luther_babstum_1526_0011','quiver/arnold_ketzerhistorie01_1699_0114','quiver/benner_herrnhuterey04_1748_0013','finebooks/conchologiaiconi05reev/8967333','finebooks/trudyrusskagoent161881russ/12342014']
assert len(set(pilot))==6 and all(x in lock['pages'] for x in pilot)
dev={p['work'] for p in corpus['pages'] if p['split']=='dev'}; hold={p['work'] for p in corpus['pages'] if p['split']=='holdout'}; assert dev.isdisjoint(hold)
entries=[]
for p in corpus['pages']:
 q=dict(p); q['pilot_6']=p['id'] in pilot
 q['source_lock_reference']=('pages/'+p['id'] if p['split']=='dev' else 'sealed_holdout/'+p['id'] if p['split']=='holdout' else None)
 if p['split']=='dev':q['language']=lock['pages'][p['id']]['language']
 entries.append(q)
frozen={'schema':'books01-corpus-frozen/1','status':'selection frozen; see PHASE0.md for limitations','proposed_sha256':hashlib.sha256((P/'corpus.proposed.json').read_bytes()).hexdigest(),'book_disjoint_assertion':{'dev_works':len(dev),'holdout_works':len(hold),'intersection':sorted(dev&hold)},'pilot_6':pilot,'deviations':[],'pages':entries}
(P/'corpus.frozen.json').write_text(json.dumps(frozen,indent=2,ensure_ascii=False)+'\n')
def usage(path):
 return sum(p.stat().st_size for p in path.rglob('*') if p.is_file()) if path.exists() else 0
sizes={n:usage(B/n) for n in ['src','sources','gt','qa','smoke','tmp','tessdata_best']}
fetch=json.loads((B/'src/fetch-results.json').read_text())['files']+json.loads((B/'src/finebooks/fetch-results.json').read_text())+list(json.loads((B/'src/ia/dev-jp2.json').read_text()).values())
version=subprocess.check_output(['/usr/bin/tesseract','--version'],stderr=subprocess.STDOUT,text=True,env={**os.environ,'TESSDATA_PREFIX':str(B/'tessdata_best')})
res={'disk_bytes_logical_by_category':sizes,'unique_source_file_bytes':sum(x['bytes'] for x in fetch),'download_bytes_note':'Sum of saved official files, excluding retried transfers; actual network bytes were not instrumented.','wall_seconds':{'source_pdf_gt_build':float((B/'build-seconds.txt').read_text()),'fetch':None,'registration':None,'smoke':None},'wall_time_note':'Fetch, registration and smoke elapsed times were not instrumented; unknown values are not estimates.','tesseract_version_full':version,'hocr_config_sha256':hashlib.sha256((B/'tessdata_best/configs/hocr').read_bytes()).hexdigest(),'smoke_report_sha256':hashlib.sha256((B/'smoke/aventinus.pdf.json').read_bytes()).hexdigest(),'smoke_raster_import':'native_source_samples'}
(P/'provenance/phase0-costs.json').write_text(json.dumps(res,indent=2)+'\n')
