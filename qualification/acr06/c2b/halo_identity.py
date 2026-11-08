#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,subprocess
R=Path('/data/coding/scanweave');L=R/'qualification/acr06/local/c2b';p=R/'qualification/font04/local/P2'; rows={}
for dpi,num in [(200,0),(300,3)]:
 dst=L/'halo'/f'identity-{dpi}.pdf';src=p/f'sheet-{num}.pdf';env=dict(os.environ,SCANWEAVE_PDFIUM_LIBRARY=str(R/'tools/src/pdfium/lib/libpdfium.so'),SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python',OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4',SCANWEAVE_RESEARCH_C2B_HALO='1',SCANWEAVE_RESEARCH_C2B_TRACE=str(dst)+'.funnel.json')
 with open(str(dst)+'.log','w') as log:subprocess.run(['/tmp/c2b-followup-target/release/scanweave',str(src),str(dst),'--dpi',str(dpi),'--profile','clearscan','--glyph-sharing','cover-2.0-ceiling-q3'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 get=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
 rows[str(dpi)]={'main_trace':get(L/'trace'/f'p2-{num}.pdf'),'halo':get(dst)};print(dpi,rows[str(dpi)],flush=True)
(R/'qualification/acr06/c2b/halo-identity.json').write_text(json.dumps(rows,indent=2)+'\n')
