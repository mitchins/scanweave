"""Publish numeric development-page metrics, excluding PDF text and pixels."""
import collections,json,pathlib,statistics
B=pathlib.Path('/data/coding/scanweave/work/books01');P=B/'stroke02/pages-refit';Q=pathlib.Path('/tmp/scanweave-books01/qualification/books01');pages=[p for p in json.loads((Q/'corpus.frozen.json').read_text())['pages'] if p['split']=='dev'];assert len(pages)==36
out=[]
for page in pages:
 k=page['id'].split('/')[-1];p=P/k/'metrics.json'
 if not p.exists():out.append({'id':page['id'],'status':'missing'});continue
 x=json.loads(p.read_text());x.pop('candidate_argv',None)
 for s in ('baseline','candidate'):
  if s in x:x[s].pop('regions',None)
 prepass=P/k/'prepass.json'
 if prepass.exists():
  raw=json.loads(prepass.read_text());lines=raw['lines']; sigmas=[line['sigma'] for line in lines];x['prepass_summary']={'lines':len(lines),'declined_fit_boundary':len(raw.get('declined',[])),'median_sigma_px':statistics.median(sigmas) if sigmas else None,'enclosed_paper_pixels':sum(line['veto_pixels'] for line in lines)}
 run=json.loads((B/'phase2/runs'/k/'runs.json').read_text());x['pdf_sha256_equal_to_baseline']=x.get('candidate_sha256')==run['rows']['sw-E'].get('output_sha256') if x.get('candidate_sha256') else None
 report=P/k/'candidate.pdf.json';x['latent_trace_mentions']=report.read_text().count('experimental_latent_curve') if report.exists() else 0
 for name,path in [('baseline',pathlib.Path(json.loads((B/'phase2/runs'/k/'runs.json').read_text())['rows']['sw-E']['path']+'.json')),('candidate',report)]:
  if name in x and path.exists():
   page_report=json.loads(path.read_text())['conversion']['page_reports'][0]
   x[name]['occurrence_owner_counts']=dict(collections.Counter(o['owner'] for o in page_report['occurrences']))
 out.append(x)
ok=[r for r in out if r.get('status')==0];s={'expected_pages':len(pages),'completed_pages':len(ok),'failures':[{'id':x['id'],'status':x.get('status'),'error':x.get('error')} for x in out if x.get('status')!=0]}
if ok:
 for name,field in [('baseline_pdf_bytes','baseline_pdf_bytes'),('candidate_pdf_bytes','candidate_pdf_bytes'),('baseline_wall_seconds','baseline_wall_seconds'),('candidate_wall_seconds','candidate_wall_seconds'),('baseline_render_median_seconds','baseline_render_median_seconds'),('candidate_render_median_seconds','candidate_render_median_seconds')]:
  v=[x[field] for x in ok if x.get(field) is not None];s[name]={'sum':sum(v),'median':statistics.median(v)} if v else None
 for name in ('baseline','candidate'):
  for field in ('raster_bytes','vector_units_proposed','raster_units_proposed'):
   v=[x[name][field] for x in ok];s[name+'_'+field]={'sum':sum(v),'median':statistics.median(v)}
  s[name+'_coverage_totals']={k:sum(x[name]['coverage'][k] for x in ok) for k in ('text_ink_px_total','text_ink_px_vector','text_ink_px_raster')}
 s['extension_totals']={k:sum(x.get('extensions',{}).get(k,0) for x in ok) for k in ('attempted','accepted','rejected_neighbour','rejected_disconnected','rejected_overlap','rejected_box','rejected_veto','pixels')};s['pages_with_extensions']=sum(x.get('extensions',{}).get('accepted',0)>0 for x in ok);s['ownership_moves']=dict(sum((collections.Counter(x.get('ownership_moves',{})) for x in ok),collections.Counter()));s['whitespace_only_pages']=sum(x['text_diff'].get('whitespace_only',False) for x in ok);s['nonwhitespace_changed_pages']=sum(x['text_diff'].get('nonwhitespace_removed',0)>0 or x['text_diff'].get('nonwhitespace_added',0)>0 or x['text_diff'].get('nonwhitespace_order_changed',False) for x in ok);s['byte_identical_pages']=sum(x['pdf_sha256_equal_to_baseline'] is True for x in ok);s['prepass_wall_seconds']={'sum':sum(x['prepass_wall_seconds'] for x in ok),'median':statistics.median(x['prepass_wall_seconds'] for x in ok)};s['actual_occurrence_owner_counts']={name:dict(sum((collections.Counter(x[name].get('occurrence_owner_counts',{})) for x in ok),collections.Counter())) for name in ('baseline','candidate')};s['baseline_ufffe']=sum(x['text_diff']['baseline_ufffe'] for x in ok);s['candidate_ufffe']=sum(x['text_diff']['candidate_ufffe'] for x in ok);s['text_changed_pages']=sum(not x['text_diff']['same'] for x in ok);s['new_ufffe']=sum(x['text_diff']['new_ufffe'] for x in ok);s['changed_region_pages']=sum(x['changed_region_dispositions']>0 for x in ok);s['pages_with_latent_trace_mentions']=sum(x['latent_trace_mentions']>0 for x in ok);s['mean_page_150dpi_delta']=statistics.mean(x['render_diff_150dpi']['mean_absolute_channel_delta'] for x in ok if 'mean_absolute_channel_delta' in x['render_diff_150dpi'])
result={'summary':s,'pages':out};pathlib.Path(__file__).with_name('results-refit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(s,indent=2))
