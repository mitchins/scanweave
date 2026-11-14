#!/usr/bin/env python3
"""Re-score all prior OCR word and artwork candidates after global alignment."""
import collections,json,pathlib
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[2];Q=P/'pilot';source=Q/'phase1b/calibrate.py';ns={'__file__':str(source),'__name__':'pilot_triage'};exec(compile(source.read_text().split('records=[]')[0],str(source),'exec'),ns);getim=ns['getim'];calc=ns['calc'];dets=['glyph_shape','missing_ink','spurious_ink','illustration_colour','border_inversion'];cal=json.loads((Q/'results/phase1b/calibration.json').read_text());threshold={d:cal['detectors'][d]['threshold'] for d in dets};candidates=[];counts=collections.Counter();seen=set();out=B/'pilot/phase1b/triage-raw.jsonl';out.parent.mkdir(parents=True,exist_ok=True)
with out.open('w') as dest, (B/'pilot/raw-scores.jsonl').open() as sourcefile:
 for line in sourcefile:
  old=json.loads(line);det=old['detector'];
  if det not in ('glyph_shape','illustration_colour','border_inversion'):continue
  id=old['page'];row=old['row'];box=old['bbox'];key=(id,row,tuple(box),det)
  if key in seen:continue
  seen.add(key);src=getim(id,'src');im=getim(id,row)
  if src is None or im is None:continue
  s=calc(src,im,box,id)
  if s is None:continue
  applicable=['glyph_shape','missing_ink','spurious_ink'] if det=='glyph_shape' else [det]
  for name in applicable:
   val=s[name];t=threshold[name];flag=val is not None and t is not None and val>=t;counts[(name,'examined')]+=1;counts[(name,'valid')]+=val is not None;counts[(name,'suspected')]+=flag;rec={'page':id,'row':row,'bbox':box,'detector':name,'score':val,'threshold':t,'suspected':flag,'source_ink_pixels':s['source_ink_pixels'],'local_contrast':s['local_contrast'],'min_dimension_lt_10_px':min(box[2]-box[0],box[3]-box[1])<10,'assessment':'automated suspicion; AI-assessed calibration provisional (not human-adjudicated)'};dest.write(json.dumps(rec)+'\n')
   if flag:candidates.append(rec)
  if len(seen)%2000==0:print('rescored',len(seen),'crop/row cases',flush=True)
(B/'pilot/phase1b/triage-candidates.json').write_text(json.dumps(candidates,indent=2)+'\n')
(Q/'results/phase1b/triage-summary.json').write_text(json.dumps({'assessment':'automated suspicions calibrated on AI-assessed, provisional (not human-adjudicated) examples','source':'all prior hOCR word candidates and GT-scoped artwork/border tiles, globally aligned PDFium source-DPI renders','per_detector':{d:{k:counts[(d,k)] for k in ['examined','valid','suspected']} for d in dets},'raw_scores_local':'$B/pilot/phase1b/triage-raw.jsonl','calibration':'results/phase1b/calibration.json'},indent=2)+'\n')
