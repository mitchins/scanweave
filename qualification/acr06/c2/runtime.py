#!/usr/bin/env python3
"""Serial runtime measurement: run only after all other study work is complete."""
import json, os, re, subprocess, time
from run import ROOT, INPUT, OUT, BIN

out=OUT/'runtime';out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,SCANWEAVE_PDFIUM_LIBRARY=str(ROOT/'tools/src/pdfium/lib/libpdfium.so'),OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4',SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python')
env.pop('SCANWEAVE_RESEARCH_OWNERSHIP_TRACE',None)
items=[(f'p2pp-{i}', INPUT/'P2pp'/f'sheet-{i}.pdf',600) for i in (6,7,8)]+[('financial', ROOT/'qualification/pdf_packaging/groups/financial-input.pdf',300)]
rows=[]
for name,src,dpi in items:
    for arm in ('q3','corrected-only'):
        env.pop('SCANWEAVE_RESEARCH_OWNERSHIP',None)
        if arm=='corrected-only':env['SCANWEAVE_RESEARCH_OWNERSHIP']=arm
        dest=out/f'{name}-{arm}.pdf'; log=out/f'{name}-{arm}.log'; timing=out/f'{name}-{arm}.time'
        cmd=['/usr/bin/time','-v','-o',str(timing),'taskset','-c','0,6,10,18,22',str(BIN),str(src),str(dest),'--dpi',str(dpi),'--profile','clearscan','--glyph-sharing','cover-2.0-ceiling-q3']
        before=time.monotonic()
        with log.open('w') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
        data=timing.read_text();rss=re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)',data); elapsed=re.search(r'Elapsed \(wall clock\) time .*?:\s*([\d:.]+)',data)
        rows.append(dict(document=name,arm=arm,returncode=r.returncode,wall_seconds=time.monotonic()-before,time_wall=elapsed.group(1) if elapsed else None,peak_rss_kb=int(rss.group(1)) if rss else None,time_file=str(timing)))
        print(rows[-1],flush=True)
        if r.returncode: raise RuntimeError(f'{name} {arm} failed')
        (out/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
