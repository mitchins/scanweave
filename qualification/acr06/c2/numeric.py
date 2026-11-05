#!/usr/bin/env python3
"""Use the PR #26 pristine-page and metric method on the already-open P sheets."""
import json
import time
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops
from analyze import paths, HERE
from run import INPUT
from pr26_metrics import render, measure, summary

sets=[('p2','P2','p2'),('p2prime','P2prime','p2prime'),('p2pp','P2pp','p2pp')]
rows_out=[]; summaries=[]
for name,folder,sub in sets:
    base=INPUT/folder/sub
    rows=[json.loads(s) for s in (base/'observations.jsonl').read_text().splitlines()]
    for i in range(9):
        while not (INPUT.parents[1]/'acr06/local/c2/corrected-only'/f'{name}-{i}.pdf.done').exists(): time.sleep(10)
        dpi=(200,300,600)[i//3]; sel=[r for r in rows if r['page']==i//3 and r['sheet']==i%3]
        ref=Image.new('L',(6*dpi,9*dpi),255)
        for r in sel:
            with Image.open(base/'oracle'/f"{r['id']}-pristine.png") as glyph:
                ref.paste(ImageChops.darker(ref.crop(r['bbox']),glyph),r['bbox'][:2])
        ref=np.asarray(ref); pp=paths(f'{name}-{i}')
        for engine in ('pdfium','poppler'):
            images={a:render(pp[a],0,dpi,engine) for a in ('off','q3','corrected')}
            vals={a:[] for a in images}
            for r in sel:
                x,y,xx,yy=r['bbox']; truth=1-ref[y:yy,x:xx].astype(float)/255
                rec=dict(document=f'{name}-{i}',id=r['id'],dpi=dpi,renderer=engine)
                cache={}
                for a,img in images.items():
                    crop=img[y:yy,x:xx]; key=crop.tobytes()
                    if key not in cache: cache[key]=measure(truth,1-crop.astype(float)/255)
                    rec[a]=cache[key]; vals[a].append(rec[a])
                rows_out.append(rec)
            summaries.append(dict(document=f'{name}-{i}',dpi=dpi,renderer=engine,metrics={a:summary(v) for a,v in vals.items()}))
        print(name,i,flush=True)
(HERE/'numeric-records.json').write_text(json.dumps(rows_out,separators=(',',':'))+'\n')
(HERE/'numeric-summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
