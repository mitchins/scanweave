"""Two-way causal ladder on the existing P1 corpus; never accesses P2.

Source preparation and fitting finish before evaluate() reads oracle labels or
pristine images. Native atlas translations are integer pixel shifts, preserving
original physical placement and fractional phase in each renderer.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import numpy as np
import pikepdf
from PIL import Image
from scipy import ndimage
from scipy.optimize import linear_sum_assignment

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from qualification.font01.context import source_lines
from qualification.font04.planner import local_source,crop_request,source_frame,mse
from qualification.font04.geometry import register,warp
from qualification.font04.metrics import inspect,matrix,operands,render,measure,summary,sha
from qualification.font04.pdf_helpers import font_resource

ROOT=Path(os.environ.get('FONT04_CAUSAL_ROOT','qualification/font04/local/causal'))
CORPUS=Path('qualification/font01/local/corpus-font01-v1')
CLASSES=os.environ.get('FONT04_CAUSAL_CLASSES','e1a8.!odynstrcul')
ARMS=['A0','A1','A2','A3','A4','F-self','F-medoid','R-floor','R-normalization','R-frame','cap-current','cap-raised']
BASELINES=dict(financial=Path('qualification/font04/local/financial-main.pdf'),train=Path('qualification/font04/local/train-main.pdf'),validation=Path('qualification/font02/local/hard-negatives/validation-product.pdf'),test=Path('qualification/font01/local/rust-control-test-v2.pdf'))


def owned(split,page):
    full=Path(f'qualification/font04/local/owned/{split}-{page}.json')
    if full.exists():return json.loads(full.read_text())
    root=Path('qualification/font03/local') if split=='train' else Path('qualification/font02/local/hard-negatives')
    return json.loads((root/f'{split}-{page}-owned.json').read_text())


def prep(split):
    destination=ROOT/split;destination.mkdir(parents=True,exist_ok=True)
    public=[json.loads(l) for l in (CORPUS/split/'observations.jsonl').read_text().splitlines()]
    exports={p:owned(split,p) for p in range(3)}
    units={o['id'].removeprefix('g'):o for e in exports.values() for o in e['observations']}
    lines={}
    for indices in source_lines(public):
        samples=[units[public[i]['id']] for i in indices if public[i]['id'] in units]
        for i in indices:lines[public[i]['id']]=[dict(text=o['text'],bbox=o['bbox']) for o in samples if not o['suspect']]
    pages={}
    for page in range(3):
        with Image.open(CORPUS/split/f'page-{page}.png') as image:pages[page]=np.round(np.asarray(image.convert('RGB'),float)@np.array([.2126,.7152,.0722]))
    current=inspect(BASELINES[split]);bindings={};abstentions=[]
    # Match emitted glyphs to public source units by label and spatial center.
    for page in range(3):
        dpi=[200,300,600][page]
        for char in CLASSES:
            src=[p for p in public if p['page']==page and p['character']==char and p['id'] in units]
            draws=[d for d in current['draws'] if d['page']==page and d['character']==char and 'center'in d]
            if not src or not draws:continue
            centers=np.array([[(units[p['id']]['bbox'][0]+units[p['id']]['bbox'][2])/2,(units[p['id']]['bbox'][1]+units[p['id']]['bbox'][3])/2] for p in src])
            dst=np.array([[d['center'][0]*dpi/72,(648-d['center'][1])*dpi/72] for d in draws])
            cost=np.linalg.norm(centers[:,None]-dst[None],axis=2)
            ii,jj=linear_sum_assignment(cost)
            for i,j in zip(ii,jj):
                if cost[i,j]<=max(5,units[src[i]['id']]['height']*.25):bindings[src[i]['id']]=draws[j]
    rows=[];fields=[];items=[]
    for p in public:
        if p['character'] not in CLASSES:continue
        identifier=p['id'];u=units.get(identifier)
        if not u or u['suspect'] or identifier not in bindings:
            abstentions.append(dict(id=identifier,character=p['character'],reason='no unambiguous emitted and owned glyph'));continue
        x0,y0,x1,y1=map(int,u['bbox']);gray=pages[p['page']]
        if min(x0,y0)<2 or x1+2>gray.shape[1] or y1+2>gray.shape[0]:continue
        source=dict(width=u['width'],height=u['height'],bbox=u['bbox'],ocr_bbox=u['ocr_bbox'],mask=u['mask'],gray=gray[y0:y1,x0:x1].astype(int).ravel().tolist(),halo=gray[y0-2:y1+2,x0-2:x1+2].astype(int).ravel().tolist())
        row=dict(geometric_line_filter=False,id=identifier,character=p['character'],page=p['page'],dpi=p['dpi'],source=source,paper=exports[p['page']]['paper'],line_units=lines[identifier],public_bbox=p['bbox'],current=bindings[identifier])
        try:field,frame=source_frame(row)
        except ValueError as error:abstentions.append(dict(id=identifier,character=p['character'],reason=str(error)));continue
        row['frame']=frame;fields.append(field);row['trace']={}
        gray_crop=np.array(source['gray'],float).reshape(source['height'],source['width'])
        paper=np.percentile(gray_crop,90);ink=np.percentile(gray_crop,5)
        cov=np.clip((paper-gray_crop)/max(1,paper-ink),0,1)
        local=local_source(source,row['paper'])[2:-2,2:-2]
        for kind,coverage,floor,local_target,raised in [('native-floor',cov,True,False,False),('native-off',cov,False,False,False),('native-local',local,False,True,False),('native-cap',cov,False,False,True)]:
            key=identifier+':'+kind
            item=dict(key=key,character=p['character'],width=source['width'],height=source['height'],coverage=coverage.ravel().tolist(),gray=source['gray'],mask=source['mask'],floor=floor,local=local_target,raised_cap=raised,preserve_frame=False)
            items.append(item);row['trace'][kind]=dict(key=key,bbox=u['bbox'])
        for kind,floor,local_target in [('line-local',False,True),('line-floor',True,True),('line-crop',False,False)]:
            item,origin=crop_request(identifier+':'+kind,p['character'],field,floor=floor)
            item['local']=local_target;items.append(item)
            x,y=origin;w,h=item['width'],item['height'];f=frame
            bb=[f['cx']+(x-32)/f['scale'],f['baseline']+(y-48)/f['scale'],f['cx']+(x+w-32)/f['scale'],f['baseline']+(y+h-48)/f['scale']]
            row['trace'][kind]=dict(key=item['key'],bbox=bb,origin=origin)
        rows.append(row)
    (destination/'source.json').write_text(json.dumps(dict(rows=rows,abstentions=abstentions,selected=sum(p['character'] in CLASSES for p in public),public_sha256=sha(CORPUS/split/'observations.jsonl'),baseline_sha256=sha(BASELINES[split]))))
    np.save(destination/'fields.npy',fields)
    # DPI batches bound request memory; the tracer is production code with switches.
    for page in range(3):
        keys={r['id'] for r in rows if r['page']==page};request=dict(items=[i for i in items if i['key'].split(':')[0] in keys])
        path=destination/f'trace-{page}.json';path.write_text(json.dumps(request));print(split,page,len(request['items']),'traces',flush=True)
        with path.open('rb') as stream:
            subprocess.run(['target/release/examples/font04_trace',str(destination/f'curves-{page}')],stdin=stream,check=True)
    print(split,'source preparation and tracing complete',len(rows),flush=True)


def source_native(row,left,top,side):
    s=row['source'];cov=local_source(s,row['paper']);x0,y0=s['bbox'][:2];yy,xx=np.mgrid[:side,:side]
    return ndimage.map_coordinates(cov,[yy+top-y0+2.,xx+left-x0+2.],order=1,mode='constant',prefilter=False)


def trace_canvas(row,o,kind):
    f=row['frame'];b=row['trace'][kind]['bbox'];yy,xx=np.mgrid[:64,:64]
    nx=f['cx']+(xx-32)/f['scale'];ny=f['baseline']+(yy-48)/f['scale']
    cov=np.array(o['coverage']).reshape(o['height'],o['width'])
    return ndimage.map_coordinates(cov,[(ny-b[1])/(b[3]-b[1])*o['height']-.5,(nx-b[0])/(b[2]-b[0])*o['width']-.5],order=1,mode='constant',prefilter=False)


def glyph_matrix(row,o,bbox):
    dpi=row['dpi'];x0,y0,x1,y1=bbox;pixel_x=row.get('pixel_x_pt',72/dpi);pixel_y=row.get('pixel_y_pt',72/dpi)
    # Match the production anchor-based placement, with 16 font units per pixel.
    sx=(x1-x0)/o['span'][0];sy=(y1-y0)/o['span'][1]
    return np.array([[sx*2048*pixel_x,0,(x0-o['anchor'][0]*sx)*pixel_x],[0,sy*2048*pixel_y,row.get('page_height',648)-(y1+o['anchor'][1]*sy)*pixel_y],[0,0,1.]])


def fit_bbox(row,bbox,parameters):
    dx,dy,s=parameters;f=row['frame']
    points=[]
    for x,y in [bbox[:2],bbox[2:]]:
        cx=32+(x-f['cx'])*f['scale'];cy=48+(y-f['baseline'])*f['scale']
        points.extend([f['cx']+(s*(cx-32)+dx)/f['scale'],f['baseline']+(s*(cy-48)+dy)/f['scale']])
    return points


def make_atlases(split):
    destination=ROOT/split;data=json.loads((destination/'source.json').read_text());rows=data['rows'];fields=np.load(destination/'fields.npy')
    # Source-only nearest independent witness; same label, distinct source shape.
    donors={}
    for i,r in enumerate(rows):
        others=[j for j,q in enumerate(rows) if q['character']==r['character'] and q['id']!=r['id'] and q['source']['mask']!=r['source']['mask']]
        if others:
            shortlist=sorted(others,key=lambda j:mse(fields[i],fields[j]))[:8]
            candidates=[(*register(fields[i],fields[j]),j) for j in shortlist]
            p,aligned,j=min(candidates,key=lambda entry:mse(fields[i],entry[1]));donors[i]=dict(donor=j,parameters=p.tolist())
    decisions=[]
    for page in sorted({r['page'] for r in rows}):
        outlines=json.loads((destination/f'curves-{page}/outlines.json').read_text())['records'];lookup={o['key']:o for o in outlines if 'gid'in o}
        with pikepdf.open(BASELINES[split]) as original:
            # Donor fonts can come from another DPI batch. Separate resources.
            pdf=pikepdf.Pdf.new();resources={}
            for donor_page in sorted({r['page'] for r in rows}):
                other=json.loads((destination/f'curves-{donor_page}/outlines.json').read_text())['records']
                resources['C'+str(donor_page)]=font_resource(pdf,destination/f'curves-{donor_page}/font.ttf',other)
            pdf.pages.append(original.pages[page]);basefont=pdf.pages[0].Resources.Font.F1;del pdf.pages[0]
            resources['B']=basefont
            selected=[(i,r) for i,r in enumerate(rows) if r['page']==page]
            # One isolated source-only A0 atlas per DPI, rather than rendering
            # the full original page once per target. Original pixel phase is kept.
            a0_fields={};probe=pikepdf.Pdf.new();probe.pages.append(original.pages[page]);bf=probe.pages[0].Resources.Font.F1;del probe.pages[0]
            a0meta=[];a0commands=[]
            for k,(i,row) in enumerate(selected):
                if k%100==0:
                    if a0commands:
                        pp=probe.add_blank_page(page_size=(1600*72/row['dpi'],1600*72/row['dpi']));pp.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(B=bf));pp.Contents=probe.make_stream(('\n'.join(a0commands)+'\n').encode());a0commands=[]
                cx=(k%10)*160;cy=((k%100)//10)*160;b=row['source']['bbox'];left=int((b[0]+b[2])/2)-80;top=int((b[1]+b[3])/2)-80;dpi=row['dpi']
                tf=np.array([[1.,0,(cx-left)*72/dpi],[0,1.,1600*72/dpi-row.get('page_height',648)-(cy-top)*72/dpi],[0,0,1.]])
                a0commands.append('BT 0 Tr 0 g /B 1 Tf '+' '.join(map(str,operands(tf@matrix(row['current']['matrix']))))+f" Tm <{row['current']['cid']:04x}> Tj ET")
                a0meta.append((i,k//100,cx,cy,left,top))
            if a0commands:
                pp=probe.add_blank_page(page_size=(1600*72/dpi,1600*72/dpi));pp.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(B=bf));pp.Contents=probe.make_stream(('\n'.join(a0commands)+'\n').encode())
            probe_path=destination/f'placement-{page}.pdf';probe.save(probe_path,deterministic_id=True)
            for sheet in sorted({m[1] for m in a0meta}):
                native=1-render(probe_path,sheet,dpi,'pdfium').astype(float)/255
                for i,sh,cx,cy,left,top in a0meta:
                    if sh!=sheet:continue
                    f=rows[i]['frame'];yy,xx=np.mgrid[:64,:64]
                    a0_fields[i]=ndimage.map_coordinates(native,[f['baseline']+(yy-48)/f['scale']-top+cy-.5,f['cx']+(xx-32)/f['scale']-left+cx-.5],order=1,mode='constant')

            side=160;cols=10;perpage=100;sheet_size=side*cols;dpi=next(r['dpi'] for r in rows if r['page']==page);records=[];commands=[]
            def flush():
                if not commands:return
                p=pdf.add_blank_page(page_size=(sheet_size*72/dpi,sheet_size*72/dpi));p.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(**resources));p.Contents=pdf.make_stream(('\n'.join(commands)+'\n').encode());commands.clear()
            for i,row in selected:
                for arm in ARMS:
                    k=len(records);sheet=k//perpage;cell=k%perpage;cellx=(cell%cols)*side;celly=(cell//cols)*side
                    bb=row['source']['bbox'];left=int((bb[0]+bb[2])/2)-side//2;top=int((bb[1]+bb[3])/2)-side//2
                    dx=cellx-left;dy=celly-top
                    transform=np.array([[1.,0,dx*72/dpi],[0,1.,sheet_size*72/dpi-row.get('page_height',648)-dy*72/dpi],[0,0,1.]])
                    fitted=[0.,0.,1.];donor=i
                    if arm in ['A0','A1']:
                        m=matrix(row['current']['matrix']);gid=row['current']['cid'];font='B'
                        # A0 isolated native glyph PDFium is source-only placement evidence.
                        if arm=='A1':
                            observed=a0_fields[i]
                            f=row['frame']
                            fitted,_=register(fields[i],observed)
                            # Refitting native PDF matrices about the source line anchor.
                            scale=fitted[2];center=np.array([f['cx'],f['baseline']]);shift=np.array(fitted[:2])/f['scale']
                            native_tf=np.array([[scale,0,center[0]*(1-scale)+shift[0]],[0,scale,center[1]*(1-scale)+shift[1]],[0,0,1.]])
                            pt=np.array([[72/dpi,0,0],[0,-72/dpi,row.get('page_height',648)],[0,0,1.]])
                            m=pt@native_tf@np.linalg.inv(pt)@m
                    else:
                        kinds={'A2':'native-off','A3':'native-local','A4':'line-local','F-self':'line-local','F-medoid':'line-local','R-floor':'line-floor','R-normalization':'line-crop','R-frame':'native-local','cap-current':'native-off','cap-raised':'native-cap'}
                        kind=kinds[arm];donor_page=page
                        if arm=='F-medoid' and i in donors:
                            donor=donors[i]['donor'];donor_row=rows[donor];donor_page=donor_row['page']
                            ds=json.loads((destination/f'curves-{donor_page}/outlines.json').read_text())['records'];o=next(o for o in ds if o['key']==donor_row['trace'][kind]['key']);origin=donor_row['trace'][kind]['origin'];f=row['frame']
                            bbox=[f['cx']+(origin[0]-32)/f['scale'],f['baseline']+(origin[1]-48)/f['scale'],f['cx']+(origin[0]+o['width']-32)/f['scale'],f['baseline']+(origin[1]+o['height']-48)/f['scale']]
                            canvas=np.zeros((64,64));x,y=origin;canvas[y:y+o['height'],x:x+o['width']]=np.array(o['coverage']).reshape(o['height'],o['width'])
                        else:
                            key=row['trace'][kind]['key'];o=lookup.get(key)
                            if o is None:raise ValueError(('trace failure',key))
                            bbox=row['trace'][kind]['bbox'];canvas=trace_canvas(row,o,kind)
                        if arm in ['F-self','F-medoid','R-floor','R-normalization','R-frame']:
                            fitted,_=register(fields[i],canvas);bbox=fit_bbox(row,bbox,fitted)
                        m=glyph_matrix(row,o,bbox);gid=o['gid'];font='C'+str(donor_page)
                    if cell==0 and commands:flush()
                    commands.append('BT 0 Tr 0 g /'+font+' 1 Tf '+' '.join(f'{v:.10f}' for v in operands(transform@m))+f' Tm <{gid:04x}> Tj ET')
                    records.append(dict(id=row['id'],index=i,character=row['character'],arm=arm,page=page,dpi=dpi,sheet=sheet,cell=[cellx,celly,cellx+side,celly+side],native_bounds=[left,top,left+side,top+side],parameters=list(map(float,fitted)),donor=rows[donor]['id']))
            flush();path=destination/f'atlas-{page}.pdf';pdf.save(path,deterministic_id=True)
            decisions.extend(records);print(split,page,'atlas glyphs',len(records),flush=True)
    (destination/'decisions.json').write_text(json.dumps(dict(records=decisions,source_only_freeze=True,source_sha256=sha(destination/'source.json'))))


def evaluate(split):
    destination=ROOT/split;decisions=json.loads((destination/'decisions.json').read_text())['records'];rows=json.loads((destination/'source.json').read_text())['rows'];byid={r['id']:r for r in rows}
    labels={r['id']:r for r in map(json.loads,(CORPUS/split/'oracle/labels.jsonl').read_text().splitlines())} if split!='financial' else {}
    results=[]
    for page in sorted({r['page'] for r in rows}):
        selected=[r for r in decisions if r['page']==page];dpi=next(r['dpi'] for r in rows if r['page']==page)
        sheets=sorted({r['sheet'] for r in selected})
        for engine in ['pdfium','poppler']:
            for sheet in sheets:
                image=1-render(destination/f'atlas-{page}.pdf',sheet,dpi,engine).astype(float)/255
                for r in selected:
                    if r['sheet']!=sheet:continue
                    row=byid[r['id']];x,y,xx,yy=r['cell'];b=image[y:yy,x:xx];left,top,right,bottom=r['native_bounds'];pristine=np.zeros_like(b)
                    native_source=source_native(row,left,top,b.shape[0])
                    record=dict(id=r['id'],character=r['character'],arm=r['arm'],renderer=engine,dpi=dpi,damage='real',source=measure(native_source,b))
                    if split!='financial':
                        px,py,pxx,pyy=row['public_bbox']
                        with Image.open(CORPUS/split/'oracle'/f'{r["id"]}-pristine.png') as p:pristine[py-top:pyy-top,px-left:pxx-left]=1-np.asarray(p.convert('L'),float)/255
                        record['damage']='D'+str(labels[r['id']]['severity']);record['pristine']=measure(pristine,b)
                    results.append(record)
            print(split,page,engine,'measured',flush=True)
    (destination/'evaluated.json').write_text(json.dumps(dict(records=results,decisions_sha256=sha(destination/'decisions.json'))))


def prep_financial():
    split='financial';destination=ROOT/split;destination.mkdir(parents=True,exist_ok=True)
    snapshot=json.loads(Path('qualification/font04/local/financial-experimental.pdf.font04/source.json').read_text())
    current=inspect(BASELINES[split]);bindings={}
    for page in range(13):
        src=[r for r in snapshot['rows'] if r['page']==page]
        draws=[d for d in current['draws'] if d['page']==page and d['character']=='e']
        centers=np.array([[(r['bbox'][0]+r['bbox'][2])/2,(r['bbox'][1]+r['bbox'][3])/2] for r in src])
        dst=np.array([[d['center'][0]*300/72,(src[0]['page_height']-d['center'][1])*300/72] for d in draws]) if src else np.empty((0,2))
        if not src:continue
        cost=np.linalg.norm(centers[:,None]-dst[None],axis=2);ii,jj=linear_sum_assignment(cost)
        for i,j in zip(ii,jj):bindings[src[i]['index']]=draws[j]
    rows=[];fields=[];items=[];abstentions=[]
    for r in snapshot['rows']:
        if r['source'] is None or r['index'] not in bindings:
            abstentions.append(dict(id=r['id'],reason='no safe owned binding'));continue
        row=dict(r,current=bindings[r['index']],public_bbox=r['source']['bbox']);row['original_id']=r['id'];row['id']=f"p{r['page']:02}@{r['id']}";source=row['source']
        try:field,frame=source_frame(row)
        except ValueError as error:abstentions.append(dict(id=r['id'],reason=str(error)));continue
        if not (field>.5).any():
            abstentions.append(dict(id=r['id'],reason='owned evidence outside source line frame'));continue
        row['frame']=frame;fields.append(field);row['trace']={};identifier=row['id']
        gray=np.array(source['gray'],float).reshape(source['height'],source['width']);paper=np.percentile(gray,90);ink=np.percentile(gray,5);cov=np.clip((paper-gray)/max(1,paper-ink),0,1)
        local=local_source(source,row['paper'])[2:-2,2:-2]
        for kind,coverage,floor,local_target,raised in [('native-floor',cov,True,False,False),('native-off',cov,False,False,False),('native-local',local,False,True,False),('native-cap',cov,False,False,True)]:
            item=dict(key=identifier+':'+kind,character='e',width=source['width'],height=source['height'],coverage=coverage.ravel().tolist(),gray=source['gray'],mask=source['mask'],floor=floor,local=local_target,raised_cap=raised,preserve_frame=False)
            items.append(item);row['trace'][kind]=dict(key=item['key'],bbox=source['bbox'])
        for kind,floor,local_target in [('line-local',False,True),('line-floor',True,True),('line-crop',False,False)]:
            item,origin=crop_request(identifier+':'+kind,'e',field,floor=floor);item['local']=local_target;items.append(item);x,y=origin;w,h=item['width'],item['height'];f=frame
            bb=[f['cx']+(x-32)/f['scale'],f['baseline']+(y-48)/f['scale'],f['cx']+(x+w-32)/f['scale'],f['baseline']+(y+h-48)/f['scale']]
            row['trace'][kind]=dict(key=item['key'],bbox=bb,origin=origin)
        rows.append(row)
    (destination/'source.json').write_text(json.dumps(dict(rows=rows,abstentions=abstentions,selected=291,baseline_sha256=sha(BASELINES[split]))));np.save(destination/'fields.npy',fields)
    for page in range(13):
        keys={r['id'] for r in rows if r['page']==page};request=dict(items=[i for i in items if i['key'].split(':')[0] in keys]);path=destination/f'trace-{page}.json';path.write_text(json.dumps(request))
        with path.open('rb') as stream:subprocess.run(['target/release/examples/font04_trace',str(destination/f'curves-{page}')],stdin=stream,check=True)
        print('financial',page,len(request['items']),'traces',flush=True)


if __name__=='__main__':
    action,split=sys.argv[1:]
    if split not in ['train','validation','test','financial']:raise ValueError('P1 split only')
    if action=='prepare' and split=='financial':prep_financial()
    else:{'prepare':prep,'atlas':make_atlases,'evaluate':evaluate}[action](split)
