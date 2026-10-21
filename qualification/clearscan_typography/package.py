"""Select this mission's deliverables; retain all raw/unrelated working files."""
from pathlib import Path
import json,gzip,hashlib

JSON_SUFFIX = '.json'
METRICS_JSON = 'metrics.json'

B=Path(__file__).resolve().parent;ROOT=B.parents[1];selected=set();archives=[]
def add(p):
 p=Path(p)
 if p.exists() and p.is_file() and not p.is_symlink():selected.add(p)
def archive(p):
 if not p.exists():return
 dest=Path(str(p)+'.gz');dest.write_bytes(gzip.compress(p.read_bytes(),mtime=0));add(dest)
 archives.append({'original':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'archive':str(dest.relative_to(ROOT)),'archive_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
for pattern in ['*.py','*.md','*.log','*.txt','*.patch','*.rs']:
 for p in B.glob(pattern):
  if p.name!='source-gate-trial-trace.rs':add(p)
for p in B.glob('*.json'):
 if p.stat().st_size>1_000_000:archive(p)
 else:add(p)
for dpi in [300,600]:
 d=B/str(dpi)
 for pattern in ['*.log','*.txt','*.png','*.svg','*-geometry.json','family-rankings.json']:
  for p in d.glob(pattern):
   if p.suffix==JSON_SUFFIX and p.stat().st_size>1_000_000:archive(p)
   elif p.suffix!='.png' or p.name.startswith(('final-','adobe-')):add(p)
 for name in ['adobe','previous','final']:add(d/(name+'.pdf'))
 for name in ['previous','final']:archive(d/(name+JSON_SUFFIX))
 archive(d/'identity.json')
 for arm in ['adobe','previous','final']:
  for name in [METRICS_JSON,'audit.json','stages/stage-errors.json']:add(d/arm/name)
  if arm=='final':
   for name in ['stages/S3-nominal-witness.pdf','stages/S4-vector-only.pdf','raster-only.pdf','ownership-audit.json']:add(d/arm/name)
 for p in (d/'source-gate-trial').glob('*'):add(p)
for arm in ['smooth','subpixel','fit','fair','strong','edgefit','blur','continuous']:
 add(B/'300'/(arm+'.pdf'))
 if arm=='fit':archive(B/'300'/(arm+JSON_SUFFIX))
 add(B/'300'/arm/METRICS_JSON)
for name in ['owner-small-frame.pdf','owner-em.pdf']:add(B/'300'/name)
for p in (B/'composition-review').glob('*'):add(p)
for p in (B/'inherited-m1d-generated').glob('*'):
 if p.suffix==JSON_SUFFIX and p.stat().st_size>200_000:archive(p)
 else:add(p)
for p in (B/'real').glob('*'):
 if p.is_file() and p.suffix in ['.py',JSON_SUFFIX,'.log','.txt','.pdf']:add(p)
for p in (B/'real/final').glob('*'):
 if p.name in [METRICS_JSON,'runs.json'] or (p.name.endswith('.comparison.png') and p.name.split('.')[0] in ['cord-00','cord-02','cord-05','cord-09','history-00','history-04']) or p.suffix in ['.pdf','.log','.txt']:add(p)
 elif p.suffix==JSON_SUFFIX:archive(p)
add(ROOT/'CLEARSCAN_TYPOGRAPHY_REPORT.md');add(B/'.gitattributes')
(B/'archives.json').write_text(json.dumps(archives,indent=2)+'\n');add(B/'archives.json')
paths=sorted(str(p.relative_to(ROOT)) for p in selected);paths.append(str((B/'deliverables.list').relative_to(ROOT)))
(B/'deliverables.list').write_text('\n'.join(paths)+'\n')
print(len(paths),'files,',round(sum((ROOT/p).stat().st_size for p in paths)/1e6,2),'MB (raw scratch evidence remains preserved)')
