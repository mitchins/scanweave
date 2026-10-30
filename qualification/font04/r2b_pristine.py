"""Score every P2 observation in its original page context at native DPI."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops
from qualification.font04.metrics import measure, render, sha, summary

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'qualification/font04/local/P2'
def main():
    rows=[json.loads(x) for x in (P/'p2/observations.jsonl').read_text().splitlines()]
    truth={x['id']:x for x in map(json.loads,(P/'p2/oracle/labels.jsonl').read_text().splitlines())}
    records=[]
    for i in range(9):
        dpi=(200,300,600)[i//3]; selected=[r for r in rows if r['page']==i//3 and r['sheet']==i%3]
        pristine=Image.new('L',(6*dpi,9*dpi),255)
        for r in selected:
            box=r['bbox']
            with Image.open(P/'p2/oracle'/f"{r['id']}-pristine.png") as glyph:
                pristine.paste(ImageChops.darker(pristine.crop(box),glyph),box[:2])
        reference=np.asarray(pristine)
        for engine in ('pdfium','poppler'):
            images=[render(P/f'sheet-{i}-{arm}.pdf',0,dpi,engine) for arm in ('off','cover-2.0')]
            assert all(im.shape[0]>=reference.shape[0] and im.shape[1]>=reference.shape[1] and im.shape[0]<=reference.shape[0]+1 and im.shape[1]<=reference.shape[1]+1 for im in images)
            for r in selected:
                x,y,xx,yy=r['bbox']; ref=1-reference[y:yy,x:xx].astype(float)/255
                v=[measure(ref,1-im[y:yy,x:xx].astype(float)/255) for im in images]
                t=truth[r['id']];records.append(dict(id=r['id'],character=t['character'],face=t['face'],dpi=dpi,damage='D'+str(t['severity']),renderer=engine,default=v[0],candidate=v[1]))
        print('scored',i,flush=True)
    (P/'pristine-records.json').write_text(json.dumps(records)+'\n')
    classes=defaultdict(list); strata=defaultdict(list)
    for r in records:
        classes[r['character'],r['renderer']].append(r)
        strata[r['dpi'],r['damage'],r['renderer']].append(r)
    def aggregate(group):
        result={a:summary([r[a] for r in group]) for a in ('default','candidate')}
        result['n']=len(group)
        result['pass']=all(result['candidate']['error'][k]<=result['default']['error'][k] for k in ('mean','p95'))
        return result
    classout={f'{c}|{engine}':aggregate(v) for (c,engine),v in classes.items() if len(v)>=10}
    output=dict(method='Original physical-coordinate observation boxes, including any overlapping neighbors; pristine reference is the composited pristine page; all generated observations included.',records=len(records),classes=classout,strata={f'{d}|{band}|{engine}':aggregate(v) for (d,band,engine),v in strata.items()},overall={engine:aggregate([r for r in records if r['renderer']==engine]) for engine in ('pdfium','poppler')},product_hashes={f'{i}-{arm}':sha(P/f'sheet-{i}-{arm}.pdf') for i in range(9) for arm in ('off','cover-2.0')})
    (P/'pristine-summary.json').write_text(json.dumps(output,indent=2)+'\n')
    print('class failures', [k for k,v in classout.items() if not v['pass']],flush=True)
if __name__=='__main__':main()
