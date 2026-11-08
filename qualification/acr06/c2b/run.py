#!/usr/bin/env python3
"""Run instrumented main q3 on the frozen development and spent 600-DPI sheets."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import os, subprocess
R=Path('/data/coding/scanweave')
OUT=R/'qualification/acr06/local/c2b'
BIN=Path('/tmp/scanweave-c2b/target/release/scanweave')
INPUT=R/'qualification/font04/local'
jobs=[(f'development-{d}',OUT/f'development/development-{d}.pdf',d) for d in (300,600)]
jobs += [(f'{name}-{i}',INPUT/folder/f'sheet-{i}.pdf',600) for name,folder in [('p2','P2'),('p2prime','P2prime'),('p2pp','P2pp')] for i in (6,7,8)]
jobs += [(f'font01-{split}-2',INPUT/'S1/font01'/f'{split}-2.pdf',600) for split in ('train','validation','test')]
def run(job):
    name,src,dpi=job
    dest=OUT/'trace'/f'{name}.pdf'; dest.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ, SCANWEAVE_PDFIUM_LIBRARY=str(R/'tools/src/pdfium/lib/libpdfium.so'), SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python', OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4', SCANWEAVE_RESEARCH_C2B_TRACE=str(dest)+'.funnel.json')
    with open(str(dest)+'.log','w') as log:
        p=subprocess.run([str(BIN),str(src),str(dest),'--dpi',str(dpi),'--profile','clearscan','--glyph-sharing','cover-2.0-ceiling-q3'],env=env,stdout=log,stderr=subprocess.STDOUT)
    print(name, p.returncode, flush=True)
    if p.returncode: raise RuntimeError(name)
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        for f in as_completed([pool.submit(run,j) for j in jobs]): f.result()
