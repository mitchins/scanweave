#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os,subprocess
R=Path('/data/coding/scanweave');O=R/'qualification/acr06/local/c2b'; B='/tmp/c2b-followup-target/release/scanweave'
def run(split):
 name=f'font01-{split}-2';src=R/'qualification/font04/local/S1/font01'/f'{split}-2.pdf';dst=O/'detail'/f'{name}.pdf'
 env=dict(os.environ,SCANWEAVE_PDFIUM_LIBRARY=str(R/'tools/src/pdfium/lib/libpdfium.so'),SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python',OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4',SCANWEAVE_RESEARCH_C2B_TRACE=str(dst)+'.funnel.json',SCANWEAVE_RESEARCH_C2B_DETAIL=str(dst)+'.detail.json')
 with open(str(dst)+'.log','w') as log:r=subprocess.run([B,str(src),str(dst),'--dpi','600','--profile','clearscan','--glyph-sharing','cover-2.0-ceiling-q3'],env=env,stdout=log,stderr=subprocess.STDOUT)
 print(name,r.returncode,flush=True)
 if r.returncode:raise RuntimeError(name)
with ThreadPoolExecutor(max_workers=2) as p:list(p.map(run,['train','validation','test']))
