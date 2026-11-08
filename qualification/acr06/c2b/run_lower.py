#!/usr/bin/env python3
"""Trace spent 200- and 300-DPI sheets; identical runner settings to C2b."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os,subprocess
R=Path('/data/coding/scanweave'); OUT=R/'qualification/acr06/local/c2b'; BIN=Path('/tmp/scanweave-c2b/target/release/scanweave'); INPUT=R/'qualification/font04/local'
jobs=[(f'{name}-{i}',INPUT/folder/f'sheet-{i}.pdf',dpi) for name,folder in [('p2','P2'),('p2prime','P2prime'),('p2pp','P2pp')] for i,dpi in [(i,200 if i<3 else 300) for i in range(6)]]
jobs += [(f'font01-{split}-{i}',INPUT/'S1/font01'/f'{split}-{i}.pdf',dpi) for split in ('train','validation','test') for i,dpi in [(0,200),(1,300)]]
def run(job):
 name,src,dpi=job; dst=OUT/'trace'/f'{name}.pdf'; env=dict(os.environ,SCANWEAVE_PDFIUM_LIBRARY=str(R/'tools/src/pdfium/lib/libpdfium.so'),SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python',OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4',SCANWEAVE_RESEARCH_C2B_TRACE=str(dst)+'.funnel.json')
 with open(str(dst)+'.log','w') as f:p=subprocess.run([str(BIN),str(src),str(dst),'--dpi',str(dpi),'--profile','clearscan','--glyph-sharing','cover-2.0-ceiling-q3'],env=env,stdout=f,stderr=subprocess.STDOUT)
 print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(name)
with ThreadPoolExecutor(max_workers=3) as pool:
 futures=[pool.submit(run,j) for j in jobs]
 for f in as_completed(futures):f.result()
