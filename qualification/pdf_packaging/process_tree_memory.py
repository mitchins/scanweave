"""One ordinary genuine 3-page conversion with sampled process-tree RSS.
RSS sums double-count shared pages; this is not PSS or a unique-RAM claim.
"""
import subprocess,time,json
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[1];out=B/'real/receipt-three-pages-tree.pdf';cmd=[str(R/'target/release/scanweave'),str(B/'real/receipt-three-pages.pdf'),str(out)]
def tree(pid):
 result=[]
 try:
  status=Path(f'/proc/{pid}/status').read_text();rss=next(int(l.split()[1]) for l in status.splitlines() if l.startswith('VmRSS:'));name=next(l.split(':',1)[1].strip() for l in status.splitlines() if l.startswith('Name:'));result.append({'pid':pid,'name':name,'rss_kib':rss})
  for child in Path(f'/proc/{pid}/task/{pid}/children').read_text().split():result+=tree(int(child))
 except (OSError,StopIteration):pass
 return result
start=time.monotonic();peak=0;snapshot=[];samples=0
with (B/'process-tree-memory.log').open('w') as log:
 p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT)
 while p.poll() is None:
  members=tree(p.pid);total=sum(r['rss_kib'] for r in members);samples+=1
  if total>peak:peak=total;snapshot=members
  time.sleep(.05)
status=p.wait();assert status==0
assert out.read_bytes()==(B/'real/receipt-three-pages-final.pdf').read_bytes()
(B/'process-tree-memory.json').write_text(json.dumps({'command':cmd,'pages':3,'seconds':time.monotonic()-start,'status':status,'sample_interval_seconds':.05,'sample_count':samples,'peak_summed_rss_kib':peak,'peak_members':snapshot,'pixel_and_byte_identical_to_previous':True,'scope':'sampled sum of CLI and all descendants RSS; shared pages counted per process; not PSS'},indent=2))
