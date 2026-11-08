#!/usr/bin/env python3
"""Compare exact main, instrumented switch-unset, and instrumented trace PDFs."""
from pathlib import Path
import hashlib,json,os,subprocess
R=Path('/data/coding/scanweave'); O=R/'qualification/acr06/local/c2b'; O.joinpath('identity').mkdir(exist_ok=True)
bins={'main':'/tmp/c2b-main-target/release/scanweave','unset':'/tmp/scanweave-c2b/target/release/scanweave'}
result={}
for dpi in (300,600):
    src=O/f'development/development-{dpi}.pdf'; hashes={}
    for arm,bin in bins.items():
        dst=O/f'identity/{arm}-{dpi}.pdf'; env=dict(os.environ,SCANWEAVE_PDFIUM_LIBRARY=str(R/'tools/src/pdfium/lib/libpdfium.so'),SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python',OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4');env.pop('SCANWEAVE_RESEARCH_C2B_TRACE',None)
        with open(str(dst)+'.log','w') as log: subprocess.run([bin,str(src),str(dst),'--dpi',str(dpi),'--profile','clearscan','--glyph-sharing','cover-2.0-ceiling-q3'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        hashes[arm]=hashlib.sha256(dst.read_bytes()).hexdigest(); print(dpi,arm,'done',flush=True)
    dst=O/f'trace/development-{dpi}.pdf';hashes['trace']=hashlib.sha256(dst.read_bytes()).hexdigest();result[str(dpi)]=hashes
(R/'qualification/acr06/c2b/identity.json').write_text(json.dumps(result,indent=2)+'\n')
