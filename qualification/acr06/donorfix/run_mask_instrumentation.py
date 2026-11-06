#!/usr/bin/env python3
import concurrent.futures,os,subprocess
from pathlib import Path
q=Path('/data/coding/scanweave/qualification'); out=q/'acr06/local/donorfix/mask-debug'; out.mkdir(parents=True,exist_ok=True); binary=q/'acr06/local/donorfix/scanweave-mask-instrumented'; env=dict(os.environ,SCANWEAVE_DONOR_MASK_DEBUG='1',SCANWEAVE_PDFIUM_LIBRARY='/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so',SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python',OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4')
def run(doc):
 src=q/('pdf_packaging/real/input/scan-c03-29.pdf' if doc=='single' else f'pdf_packaging/groups/{doc}-input.pdf'); dest=out/f'{doc}.pdf';cmd=[str(binary),str(src),str(dest),'--dpi','300','--profile','clearscan','--glyph-sharing','off']
 with (out/f'{doc}.log').open('w') as f: result=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
 print(doc,result.returncode,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: list(pool.map(run,('financial','single','forms','historical')))
