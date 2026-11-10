import pathlib,json,hashlib,re,pikepdf
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41b';L=R/'local/hvc41b';B=R/'local/ink33r';docs=[];pages=[]
def perf(path):
 s=path.read_text();m=re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (.+)',s);r=re.search(r'Maximum resident set size \(kbytes\): (\d+)',s);return {'elapsed':m.group(1) if m else None,'peak_rss_kib':int(r.group(1)) if r else None}
for doc in ('historical','receipts','financial','mixed','forms'):
 paths=[B/f'{doc}.pdf',L/'default'/f'{doc}.pdf',L/'corpus'/f'{doc}.pdf'];reports=[json.loads((B/f'{doc}.pdf.json').read_text()),json.loads((L/'corpus'/f'{doc}.pdf.json').read_text())];h=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths];docs.append({'document':doc,'baseline_bytes':paths[0].stat().st_size,'default_bytes':paths[1].stat().st_size,'corner_switch_bytes':paths[2].stat().st_size,'baseline_sha256':h[0],'default_sha256':h[1],'corner_switch_sha256':h[2],'default_byte_identical':h[0]==h[1],'corner_switch_byte_identical':h[0]==h[2],'baseline_time':perf(B/f'{doc}.time'),'default_time':perf(L/'default'/f'{doc}.time'),'corner_switch_time':perf(L/'corpus'/f'{doc}.time')})
 with pikepdf.open(paths[2]) as pdf:
  for i,(p,a,b) in enumerate(zip(pdf.pages,reports[0]['conversion']['page_reports'],reports[1]['conversion']['page_reports']),1):
   art=json.loads((L/'corpus'/doc/f'p{i:06}-outlines.json').read_text())['artwork'];ims=[]
   for obj in p.Resources.get('/XObject',{}).values():
    if str(obj.get('/Subtype'))=='/Image':ims.append(len(obj.read_raw_bytes()))
   pages.append({'document':doc,'page':i,'baseline_selected':a['selected'],'corner_selected':b['selected'],'polarity_inverted':b['polarity_inverted'],'visible_proposals':b['polarity_visible_occurrences'],'fallback':b['polarity_raster_baseline'],'baseline_page_report_elapsed_ms':a.get('elapsed_ms'),'corner_page_report_elapsed_ms':b.get('elapsed_ms'),'page_peak_rss_kib':None,'corner_border_component_count':sum(x['border_eligible'] for x in art),'encoded_page_image_resource_bytes_sum':sum(ims),'note':'Image stream bytes visible in this page resource dictionary; resources may be shared; this is not an isolated page PDF size.'})
controls=json.loads((E/'control-replay.json').read_text())
for c in controls:
 d=L/'controls'/c['set']/c['case'];a=json.loads((d/'p000001-outlines.json').read_text())['artwork'];c['corner_border_component_count']=sum(x['border_eligible'] for x in a);c['baseline_time']=perf(d/'baseline.time');c['border_time']=perf(d/'border.time')
(E/'corpus-results.json').write_text(json.dumps({'documents':docs,'pages':pages},indent=2)+'\n');(E/'control-results.json').write_text(json.dumps(controls,indent=2)+'\n');print('docs',[(x['document'],x['default_byte_identical'],x['corner_switch_byte_identical']) for x in docs]);print('pages',len(pages),'controls',len(controls),'corner components total',sum(x['corner_border_component_count'] for x in pages))
