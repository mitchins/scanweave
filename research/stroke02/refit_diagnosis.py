"""Numeric-only per-unit gate evidence for the two authorized target pages."""
import json,pathlib
B=pathlib.Path('/data/coding/scanweave/work/books01');D=B/'stroke02/pages-refit';out={}
for key in ('8967062','12342014'):
 run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());d=D/key;ledger=json.loads((d/'extensions.json').read_text());pre=json.loads((d/'prepass.json').read_text())
 def report(path):return json.loads(pathlib.Path(str(path)+'.json').read_text())['conversion']['page_reports'][0]
 old=report(run['rows']['sw-E']['path']);new=report(d/'candidate.pdf');oldobs={x['symbol_id']:x for x in old['reconstruction']['observations']};newobs={x['symbol_id']:x for x in new['reconstruction']['observations']};oldowner={x['symbol_id']:x['owner'] for x in old['occurrences'] if x['owner']!='unmapped'};newowner={x['symbol_id']:x['owner'] for x in new['occurrences'] if x['owner']!='unmapped'};records=[]
 decisions={x['symbol_id']:x for x in ledger['decisions']}
 selected=[]
 for sid,x in oldobs.items():
  a,b,c,e=x['bbox_px'];inside=key=='8967062' and c>=1165 and a<=1236 and e>=748 and b<=791
  if sid in set(ledger['symbols']) or inside:selected.append(sid)
 for sid in selected:
  x=oldobs[sid];y=newobs.get(sid,{});entry={'symbol_id':sid,'bbox':x['bbox_px'],'baseline_ink_pixels':x['ink_pixels'],'candidate_ink_pixels':y.get('ink_pixels'),'baseline_owner':oldowner.get(sid),'candidate_owner':newowner.get(sid),'extension_decision':decisions.get(sid)}
  for label,rep in [('baseline',old),('candidate',new)]:
   occurrence=next((v for v in rep['reconstruction']['occurrences'] if v['symbol_id']==sid),None)
   if occurrence:entry[label+'_reconstruction']={k:occurrence.get(k) for k in ('decision','source_mask_iou','prototype_trace_iou','restoration_evidence_passed')}
  records.append(entry)
 if key=='8967062':
  fits=[]
  for x in pre.get('declined',[]):
   a,b,c,e=x['bbox']
   if a<1200<c and b<770<e:fits.append(x)
 else:fits=[]
 out[key]={'extension_counts':{k:ledger[k] for k in ('attempted','accepted','rejected_neighbour','rejected_disconnected','rejected_overlap','rejected_box','rejected_veto')},'extension_pixels':sum(map(len,ledger['pixels'].values())),'target_fit_declines':fits,'units':records}
pathlib.Path(__file__).with_name('refit-diagnosis.json').write_text(json.dumps(out,indent=2)+'\n');print({k:{'counts':v['extension_counts'],'pixels':v['extension_pixels'],'target_units':len(v['units']),'fit_declines':v['target_fit_declines']} for k,v in out.items()})
