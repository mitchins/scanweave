"""Classify baseline raster ink using existing per-page decision records.

Regions lack unit IDs, so geometry assignment is made only where one region
uniquely contains a unit box; ambiguous units are reported separately. Donor
decisions are non-exclusive diagnostic signals, not raster causes.
"""
import collections,json,pathlib
B=pathlib.Path('/data/coding/scanweave/work/books01');Q=pathlib.Path('/tmp/scanweave-books01/qualification/books01/corpus.frozen.json');out=[]
for page in json.loads(Q.read_text())['pages']:
 if page['split']!='dev':continue
 key=page['id'].split('/')[-1];run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());p=json.loads(pathlib.Path(run['rows']['sw-E']['path']+'.json').read_text())['conversion']['page_reports'][0];cov=p['coverage'];observations=p['reconstruction']['observations'];occs={x['symbol_id']:x for x in p['reconstruction']['occurrences']};reasons=collections.Counter();signals=collections.Counter();regions=p['regions'];ambiguous=0
 whole=p['selected'] in ('raster_baseline','raster_baseline_compact') or p['polarity_raster_baseline']
 if whole:
  reasons['whole_page_polarity' if p['polarity_raster_baseline'] else 'whole_page_baseline']+=cov['text_ink_px_raster']
 else:
  for o in observations:
   b=o['bbox_px'];ink=o['ink_pixels'];matches=[]
   for region in regions:
    a=region['bbox_px']
    if a[0]<=b[0] and a[1]<=b[1] and a[2]>=b[2] and a[3]>=b[3]:matches.append(region)
   if len(matches)!=1:
    ambiguous+=ink;continue
   disposition=matches[0]['disposition']
   if isinstance(disposition,dict) and 'Raster' in disposition:
    reason=disposition['Raster']['reason'];reasons[reason]+=ink
   occ=occs.get(o['symbol_id'],{});decision=occ.get('decision')
   if decision:signals[decision]+=ink
  # Region boxes can overlap or reflect earlier planning; keep the residual
  # separate rather than invent a causal classification.
  difference=cov['text_ink_px_raster']-sum(reasons.values());reasons['unattributed_or_geometry_ambiguous']+=difference
 out.append({'id':page['id'],'raster_ink_pixels':cov['text_ink_px_raster'],'whole_page_selected':p['selected'],'polarity_raster_baseline':p['polarity_raster_baseline'],'region_attribution':dict(reasons),'ambiguous_observation_ink_pixels':ambiguous,'reconstruction_signals_nonexclusive':dict(signals),'observed_ink_pixels':sum(o['ink_pixels'] for o in observations),'all_text_ink_pixels':cov['text_ink_px_total']})
totals=collections.Counter();pages=collections.Counter();sig=collections.Counter()
for p in out:
 totals.update(p['region_attribution']);pages.update(k for k,v in p['region_attribution'].items() if v);sig.update(p['reconstruction_signals_nonexclusive'])
obj={'method':'Whole-page selected fallback first; otherwise unique region-box containment. Non-exclusive reconstruction decisions are not causal raster categories. Residual includes ambiguity and planning/report mismatches.','raster_ink_pixels':sum(p['raster_ink_pixels'] for p in out),'reason_pixels':dict(totals),'pages_by_reason':dict(pages),'nonexclusive_reconstruction_ink_signals':dict(sig),'pages':out}
pathlib.Path(__file__).with_name('raster-reason-audit.json').write_text(json.dumps(obj,indent=2)+'\n');print(json.dumps({k:v for k,v in obj.items() if k!='pages'},indent=2))
