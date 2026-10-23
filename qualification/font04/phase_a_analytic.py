"""Add the primary supersampled reference to corrected frozen Phase A arms."""
from pathlib import Path
import json,os
import numpy as np
import pypdfium2 as pdfium
from PIL import Image
from qualification.font04.causal import CORPUS,source_native
from qualification.font04.metrics import measure,sha,render
BASE=Path('qualification/font04/local')

def analytic(path,page,dpi):
    doc=pdfium.PdfDocument(path);p=doc[page];bitmap=p.render(scale=dpi*4/72,grayscale=True);a=np.asarray(bitmap.to_pil().convert('L'),float);h,w=a.shape;a=1-a[:h//4*4,:w//4*4].reshape(h//4,4,w//4,4).mean((1,3))/255;bitmap.close();p.close();doc.close();return a

def main():
    financial_only=os.environ.get('FONT04_PHASE_A_FINANCIAL_ONLY')=='1'
    floors=[r for r in json.loads((BASE/'prime-phase-a-renderer-floors.json').read_text()) if r['population']!='financial'] if financial_only else []
    for name in ['prime-causal','prime-causal-extension']:
        for split in ['train','validation','test']+(['financial'] if name=='prime-causal' else []):
            if financial_only and split!='financial':continue
            root=BASE/name/split;rows=json.loads((root/'source.json').read_text())['rows'];byid={r['id']:r for r in rows};decisions=json.loads((root/'decisions.json').read_text())['records'];evaluation=json.loads((root/'evaluated.json').read_text());records=[r for r in evaluation['records'] if r['renderer']!='analytic'];floor=json.loads((root/'floor-control-evaluated.json').read_text());frecords=[r for r in floor['records'] if r['renderer']!='analytic'];labels={r['id']:r for r in map(json.loads,(CORPUS/split/'oracle/labels.jsonl').read_text().splitlines())} if split!='financial' else {}
            for pi in sorted({r['page'] for r in rows}):
                subset=[r for r in rows if r['page']==pi];dpi=300 if split=='financial' else subset[0]['dpi'];selected=[d for d in decisions if d['page']==pi]
                if split=='financial':
                    source=analytic(root/'native-source.pdf',pi,dpi)
                    for arm in sorted({d['arm'] for d in selected}):
                        image=analytic(root/f'native-{arm}.pdf',pi,dpi)
                        for row in subset:
                            x,y,xx,yy=map(int,row['source']['bbox']);sl=(slice(y-4,yy+4),slice(x-4,xx+4));records.append(dict(id=row['id'],character=row['character'],arm=arm,renderer='analytic',dpi=dpi,damage='real',source=measure(source[sl],image[sl])))
                    image=analytic(root/f'floor-control-{pi}.pdf',0,dpi)
                    for row in subset:
                        x,y,xx,yy=map(int,row['source']['bbox']);sl=(slice(y-4,yy+4),slice(x-4,xx+4));frecords.append(dict(id=row['id'],character=row['character'],arm='A-floor-self',renderer='analytic',dpi=dpi,damage='real',source=measure(source[sl],image[sl])))
                    reference=analytic(root/'native-A0.pdf',pi,dpi)
                    for engine in ['pdfium','poppler']:
                        native=1-render(root/'native-A0.pdf',pi,dpi,engine).astype(float)/255
                        for row in subset:
                            x,y,xx,yy=map(int,row['source']['bbox']);sl=(slice(y-4,yy+4),slice(x-4,xx+4));floors.append(dict(population=split,cohort=name,id=row['id'],character=row['character'],dpi=dpi,renderer=engine,**measure(reference[sl],native[sl])))
                else:
                    pristine={}
                    for row in subset:
                        with Image.open(CORPUS/split/'oracle'/f'{row["id"]}-pristine.png') as im:pristine[row['id']]=1-np.asarray(im.convert('L'),float)/255
                    for sheet in sorted({d['sheet'] for d in selected}):
                        image=analytic(root/f'atlas-{pi}.pdf',sheet,dpi)
                        for d in selected:
                            if d['sheet']!=sheet:continue
                            row=byid[d['id']];x,y,xx,yy=d['cell'];crop=image[y:yy,x:xx];left,top,right,bottom=d['native_bounds'];p=np.zeros_like(crop);u,v,uu,vv=row['public_bbox'];p[v-top:vv-top,u-left:uu-left]=pristine[row['id']]
                            records.append(dict(id=row['id'],character=row['character'],arm=d['arm'],renderer='analytic',dpi=dpi,damage='D'+str(labels[row['id']]['severity']),source=measure(source_native(row,left,top,crop.shape[0]),crop),pristine=measure(p,crop)))
                    for sheet in range((len(subset)+99)//100):
                        image=analytic(root/f'floor-control-{pi}.pdf',sheet,dpi);reference=analytic(root/f'placement-{pi}.pdf',sheet,dpi);natives={engine:1-render(root/f'placement-{pi}.pdf',sheet,dpi,engine).astype(float)/255 for engine in ['pdfium','poppler']}
                        for k,row in enumerate(subset):
                            if k//100!=sheet:continue
                            cx=(k%10)*160;cy=((k%100)//10)*160;b=row['source']['bbox'];left=int((b[0]+b[2])/2)-80;top=int((b[1]+b[3])/2)-80;sl=(slice(cy,cy+160),slice(cx,cx+160));crop=image[sl];p=np.zeros_like(crop);u,v,uu,vv=row['public_bbox'];p[v-top:vv-top,u-left:uu-left]=pristine[row['id']]
                            frecords.append(dict(id=row['id'],character=row['character'],arm='A-floor-self',renderer='analytic',dpi=dpi,damage='D'+str(labels[row['id']]['severity']),source=measure(source_native(row,left,top,160),crop),pristine=measure(p,crop)))
                            for engine,native in natives.items():floors.append(dict(population=split,cohort=name,id=row['id'],character=row['character'],dpi=dpi,renderer=engine,**measure(reference[sl],native[sl])))
                print('analytic Phase A',name,split,pi,flush=True)
            evaluation['records']=records;evaluation['analytic_reference']='PDFium at fourfold native DPI, box averaged; original physical grids retained.';(root/'evaluated.json').write_text(json.dumps(evaluation));floor['records']=frecords;(root/'floor-control-evaluated.json').write_text(json.dumps(floor))
    path=BASE/'prime-phase-a-renderer-floors.json';path.write_text(json.dumps(floors));summary={}
    for pop,engine,dpi in sorted({(r['population'],r['renderer'],r['dpi']) for r in floors}):
        v=[r['error'] for r in floors if r['population']==pop and r['renderer']==engine and r['dpi']==dpi];summary[f'{pop}:{engine}:{dpi}']=dict(n=len(v),mean=float(np.mean(v)),p95=float(np.quantile(v,.95)))
    Path('qualification/font04/phase-a-renderer-floors.json').write_text(json.dumps(dict(reference='identical A0 outlines at same physical placements, native renderer vs 4x analytic',strata=summary,per_member=dict(path=str(path),sha256=sha(path))),indent=2)+'\n')

if __name__=='__main__':main()
