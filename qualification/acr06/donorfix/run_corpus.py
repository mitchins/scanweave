#!/usr/bin/env python3
"""Run issue 29 qualification inputs using a named executable; save logs and timing."""
import concurrent.futures, json, os, subprocess, sys, time
from pathlib import Path
root=Path('/data/coding/scanweave'); q=root/'qualification'; dest=q/'acr06/local/donorfix'/sys.argv[1]; dest.mkdir(parents=True,exist_ok=True); binary=sys.argv[2]
docs=[('fresh',q/'acr06/local/donorfix/fresh/source.pdf',300),('competitive300',q/'clearscan_competitive/300/source.pdf',300),('competitive600',q/'clearscan_competitive/600/source.pdf',600)]
docs.extend((f'fresh-{name}', q/f'acr06/local/donorfix/fresh/page-{i}.pdf', dpi) for i,(name,dpi) in enumerate([('200',200),('300',300),('600',600),('fractional',300)]))
docs.append(('fresh2',q/'acr06/local/donorfix/fresh2/source.pdf',300))
docs.extend((f'fresh2-{name}', q/f'acr06/local/donorfix/fresh2/page-{i}.pdf', dpi) for i,(name,dpi) in enumerate([('200',200),('300',300),('600',600),('fractional',300)]))
for name,folder in [('p2','P2'),('p2prime','P2prime'),('p2pp','P2pp')]:
    for i in range(9): docs.append((f'{name}-{i}',q/f'font04/local/{folder}/sheet-{i}.pdf',(200,300,600)[i//3]))
for split in ('train','validation','test'):
    for i,dpi in enumerate((200,300,600)): docs.append((f'font01-{split}-{i}',q/f'font04/local/S1/font01/{split}-{i}.pdf',dpi))
if len(sys.argv)>3 and sys.argv[3]=='all':
    docs.extend((g,q/f'pdf_packaging/groups/{g}-input.pdf',300) for g in ('receipts','forms','historical','mixed','financial'))
    docs.append(('single',q/'pdf_packaging/real/input/scan-c03-29.pdf',300))
if len(sys.argv)>3 and sys.argv[3]=='singleonly': docs=[('single',q/'pdf_packaging/real/input/scan-c03-29.pdf',300)]
if len(sys.argv)>3 and sys.argv[3]=='groups':
    docs=[(g,q/f'pdf_packaging/groups/{g}-input.pdf',300) for g in ('financial','forms','historical','mixed','receipts')]+[('single',q/'pdf_packaging/real/input/scan-c03-29.pdf',300)]
if len(sys.argv)>3 and sys.argv[3]=='quick': docs=[('single',q/'pdf_packaging/real/input/scan-c03-29.pdf',300)]+[(g,q/f'pdf_packaging/groups/{g}-input.pdf',300) for g in ('forms','historical')]
if len(sys.argv)>3 and sys.argv[3]=='confirmed':
    docs=[('single',q/'pdf_packaging/real/input/scan-c03-29.pdf',300)]+[(g,q/f'pdf_packaging/groups/{g}-input.pdf',300) for g in ('forms','historical','financial')]
if len(sys.argv)>3 and sys.argv[3]=='fresh2only': docs=[doc for doc in docs if doc[0].startswith('fresh2')]
if len(sys.argv)>3 and sys.argv[3]=='freshonly': docs=[doc for doc in docs if doc[0].startswith('fresh-')]
if len(sys.argv)>3 and sys.argv[3]=='all': docs.sort(key=lambda x: (x[0] not in ('single','financial','forms','historical','mixed','receipts'),x[0]))
env=dict(os.environ,SCANWEAVE_PDFIUM_LIBRARY=str(root/'tools/src/pdfium/lib/libpdfium.so'),SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python',OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4')
def run(job):
    name,src,dpi=job; out=dest/f'{name}.pdf'; receipt=dest/f'{name}.run.json'
    if receipt.exists() and out.exists() and json.loads(receipt.read_text()).get('returncode')==0: return name+' cached'
    cmd=[binary,str(src),str(out),'--dpi',str(dpi),'--profile','clearscan','--glyph-sharing','off']; start=time.monotonic()
    with (dest/f'{name}.log').open('w') as log: p=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    row={'command':cmd,'returncode':p.returncode,'seconds':time.monotonic()-start,'pdf_bytes':out.stat().st_size if out.exists() else None}; receipt.write_text(json.dumps(row,indent=2)+'\n')
    if p.returncode: raise RuntimeError(f'{name} failed: {p.returncode}')
    return name+' done '+str(round(row['seconds'],1))+' s'
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    for result in pool.map(run,docs): print(result,flush=True)
