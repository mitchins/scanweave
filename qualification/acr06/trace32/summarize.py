import json,statistics,re,hashlib
from pathlib import Path
root=Path('/data/coding/scanweave/qualification/acr06/local/trace32/runs'); rows={}
for name in ('single','competitive600','mixed','historical','competitive300','financial','forms','receipts','competitive600-q3','single-q3'):
 rows[name]={}
 for arm in ('main','candidate'):
  entries=[]
  for p in sorted(root.glob(f'{name}-{arm}-[123].pdf')):
   log=p.with_suffix('.log').read_text();mem=int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',log).group(1));s=re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (\S+)',log).group(1);v=[float(x) for x in s.split(':')];wall=sum(x*60**i for i,x in enumerate(v[::-1]));d=json.loads(Path(str(p)+'.json').read_text()); page=d['conversion']['page_reports']; timing={k:sum(x['stage_timings_ms'][k] for x in page)/1000 for k in page[0]['stage_timings_ms']};entries.append({'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'wall':wall,'rss_kib':mem,'page_stages_s':timing,'document_stages_ms':d['conversion']['stage_timings'],'import_ms':d['import_ms']})
  rows[name][arm]=entries
print(json.dumps(rows,indent=2))
