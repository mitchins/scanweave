#!/usr/bin/env python3
"""Collect GNU time records and pilot disk usage without reading blind keys."""
import json,pathlib,re
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot'; runs=json.loads((Q/'results/runs.json').read_text()); frozen=json.loads((Q/'results/frozen-ocr-index.json').read_text()); timings={x['page']:x for x in [json.loads(s) for s in (B/'runs/adobe/timing.jsonl').read_text().splitlines()]}; rendering=json.loads((Q/'results/render-costs.json').read_text())
def parse(path):
 if not pathlib.Path(path).exists():return None
 txt=pathlib.Path(path).read_text();out={}
 for key,pat,typ in [('user_seconds',r'User time \(seconds\):\s*([\d.]+)',float),('system_seconds',r'System time \(seconds\):\s*([\d.]+)',float),('peak_rss_kib',r'Maximum resident set size \(kbytes\):\s*(\d+)',int)]:
  m=re.search(pat,txt);out[key]=typ(m.group(1)) if m else None
 m=re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*([0-9:.]+)',txt)
 if m:
  vals=[float(x) for x in m.group(1).split(':')];out['wall_seconds']=sum(x*60**i for i,x in enumerate(reversed(vals)))
 return out
def disk(p):return sum(q.stat().st_size for q in p.rglob('*') if q.is_file()) if p.exists() else 0
result={}
for id,entry in runs.items():
 key=id.split('/')[-1];result[id]={'dpi_confidence':entry['dpi_confidence'],'rows':{}}
 for row,r in entry['rows'].items():
  if row=='adobe-E':result[id]['rows'][row]={'dpi_confidence':entry['dpi_confidence'],'wall_seconds':timings.get(key,{}).get('wall_s'),'peak_rss_kib':None,'note':'GUI wall includes sleeps and startup, not comparable to CLI'}
  elif row=='src':result[id]['rows'][row]={'dpi_confidence':entry['dpi_confidence'],'note':'reference, no conversion'}
  else:result[id]['rows'][row]={'dpi_confidence':entry['dpi_confidence'],'wall_seconds':r.get('wall_seconds'),'status':r.get('status'),'time':parse(r.get('time_file','')) if r.get('time_file') else None}
 for row in ['sw-E','sw-M']:
  report=B/'pilot/runs'/key/(row+'.pdf.json')
  if report.exists():
   x=json.loads(report.read_text());result[id]['rows'][row]['baseline_report_timing']={'pdf_import_including_ocr_ms':x.get('import_ms'),'image_encoding_ms':x.get('conversion',{}).get('image_encoding_ms'),'assembly_ms':x.get('conversion',{}).get('assembly_ms')}
 for row,v in entry['rows'].items():
  for extra in ['previous_attempt','strict_call_order_recheck']:
   if extra in v:
    e=v[extra];result[id]['rows'][row][extra]={'wall_seconds':e.get('wall_seconds'),'status':e.get('status'),'time':parse(e['time_file']) if e.get('time_file') else None}
 result[id]['frozen_ocr']={psm:[{'wall_seconds':x['wall_seconds'],'time':parse(x['time_file'])} for x in data['repeat']] for psm,data in frozen['pages'][id]['runs'].items()}
 result[id]['initial_psm6_argument_order_runs']=[parse(B/'ocr-frozen'/key/('psm6-'+str(i)+'.time')) for i in [1,2]]
 for row,renderers in rendering.get(id,{}).items():
  for renderer,resolutions in renderers.items():
   for dpi,r in resolutions.items():
    r['cpu_and_process_rss']=parse(str(r.get('output',''))+'.time') if r.get('output') else None
(Q/'results/render-costs.json').write_text(json.dumps(rendering,indent=2)+'\n')
stages=['ocr-frozen','pilot/runs','pilot/renders','pilot/blind','qa/pilot-alignment','runs/adobe'];costs={'pages':result,'logical_disk_bytes_by_stage':{x:disk(B/x) for x in stages},'stage_times':{name:parse(B/'pilot'/(name+'-stage.time')) for name in ['render','text','path','search','alignment','extraction','visual','triage','objects','adobe-repeat','strict','poppler-crop','visual-poppler','repair']},'note':'Disk is logical file bytes. Peak RSS comes from GNU time, except Adobe GUI output.'}
costs['negative_shim_tests']={name:parse(B/'pilot/negative'/(name+'.time')) for name in ['wrong_pixels','wrong_language','unexpected_psm']}
costs['six_page_cli_wall_seconds_by_row']={row:sum((x['rows'].get(row,{}).get('wall_seconds') or 0) for x in result.values()) for row in ['sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M']}
costs['linear_36_page_projection_seconds_by_row']={k:v*6 for k,v in costs['six_page_cli_wall_seconds_by_row'].items()}
costs['projection_note']='Six times the measured six-page sequential sum, not a runtime prediction; page complexity and concurrency vary. Adobe excluded.'
(Q/'results/performance.json').write_text(json.dumps(costs,indent=2)+'\n')
