#!/usr/bin/env python3
"""Capture baseline masks on P-sheets and count the 600-DPI halo counterfactual."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os,subprocess
R=Path('/data/coding/scanweave');OUT=R/'qualification/acr06/local/c2b'; BIN=Path('/tmp/c2b-followup-target/release/scanweave'); INPUT=R/'qualification/font04/local'
jobs=[]
for name,folder in [('p2','P2'),('p2prime','P2prime'),('p2pp','P2pp')]:
 for i in range(3,9):jobs.append((f'{name}-{i}',INPUT/folder/f'sheet-{i}.pdf',300 if i<6 else 600,'detail'))
 for i in range(6,9):jobs.append((f'{name}-{i}',INPUT/folder/f'sheet-{i}.pdf',600,'halo'))
for split in ('train','validation','test'):
 jobs.append((f'font01-{split}-2',INPUT/'S1/font01'/f'{split}-2.pdf',600,'halo'))
def run(job):
 name,src,dpi,arm=job;dst=OUT/arm/f'{name}.pdf';dst.parent.mkdir(exist_ok=True,parents=True)
 env=dict(os.environ,SCANWEAVE_PDFIUM_LIBRARY=str(R/'tools/src/pdfium/lib/libpdfium.so'),SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python',OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4',SCANWEAVE_RESEARCH_C2B_TRACE=str(dst)+'.funnel.json')
 if arm=='detail':env['SCANWEAVE_RESEARCH_C2B_DETAIL']=str(dst)+'.detail.json'
 else:env['SCANWEAVE_RESEARCH_C2B_HALO']='1'
 with open(str(dst)+'.log','w') as f:p=subprocess.run([str(BIN),str(src),str(dst),'--dpi',str(dpi),'--profile','clearscan','--glyph-sharing','cover-2.0-ceiling-q3'],env=env,stdout=f,stderr=subprocess.STDOUT)
 print(arm,name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError((arm,name))
with ThreadPoolExecutor(max_workers=3) as pool:
 for f in as_completed([pool.submit(run,j) for j in jobs]):f.result()
