#!/usr/bin/env python3
"""Native-render cross-check and contact sheets for all 600-DPI N members."""
import collections, hashlib, json, math
from pathlib import Path
import numpy as np
import pikepdf
from PIL import Image, ImageDraw
from scipy import ndimage
from analyze import paths, conv, HERE
from run import documents, OUT
from pr26_metrics import render

D={n:(p,d) for n,p,d in documents()}; data=json.loads((HERE/'measurements.json').read_text()); ns=data['n_members']
cache={}; panel_dir=OUT/'panels';panel_dir.mkdir(parents=True,exist_ok=True)
def img(p,page,dpi,engine):
    key=(str(p),page,dpi,engine)
    if key not in cache: cache[key]=render(p,page,dpi,engine)
    return cache[key]
def text_only(path,name,arm):
    # Remove all image/form XObject draws, leaving emitted text and its transforms.
    target=OUT/'isolated-text'/f'{name}-{arm}.pdf'; target.parent.mkdir(parents=True,exist_ok=True)
    with pikepdf.open(path) as pdf:
        for page in pdf.pages:
            ops=[op for op in pikepdf.parse_content_stream(page) if str(op.operator) not in ('Do','INLINE IMAGE')]
            page.Contents=pdf.make_stream(pikepdf.unparse_content_stream(ops))
        pdf.save(target)
    return target

def bboxmap(c):
    return {(p,o['symbol_id']):o['bbox_px'] for p,pr in enumerate(c['page_reports']) for o in pr['reconstruction']['observations']}
def crop(a,b,pad=4):
    x,y,x1,y1=[int(round(x)) for x in b];return a[max(0,y-pad):min(a.shape[0],y1+pad),max(0,x-pad):min(a.shape[1],x1+pad)]
def check(src,default,candidate):
    h=min(src.shape[0],default.shape[0],candidate.shape[0]);w=min(src.shape[1],default.shape[1],candidate.shape[1])
    s=1-src[:h,:w].astype(float)/255;cur=1-default[:h,:w].astype(float)/255;can=1-candidate[:h,:w].astype(float)/255
    lab,n=ndimage.label(s>.25,structure=ndimage.generate_binary_structure(2,1))
    own=np.bincount(lab[cur>.15],minlength=n+1);body=int(np.argmax(own[1:])+1) if n else 0
    cd=ndimage.distance_transform_edt(~(cur>.15));nd=ndimage.distance_transform_edt(~(can>.10))
    fired=[]
    for k in range(1,n+1):
        component=lab==k; lost=component & (cur>.15) & (nd>1);area=int(lost.sum());mass=float(s[lost].sum());detached=k!=body and float(cd[component].min())<=1.5
        if own[k]>0 and ((area>=3 and mass>=1.5) if detached else (area>=4 and mass>=3)): fired.append(dict(area=area,mass=mass))
    return fired

checks=[];panels=[]
bydoc=collections.defaultdict(list)
for n in ns: bydoc[n['document']].append(n)
# At most 100 members (two renderer rows each), distributed round-robin by document.
strata={k:sorted((x for x in v if x['dpi']==600),key=lambda x:x['member']) for k,v in sorted(bydoc.items())}
selected=[]
while len(selected)<100 and any(strata.values()):
    for name in strata:
        if strata[name] and len(selected)<100: selected.append(strata[name].pop(0))
selected_ids={(x['document'],x['member']) for x in selected}
for name,items in bydoc.items():
    source,dpi=D[name]; pp=paths(name); isolated={a:text_only(pp[a],name,a) for a in ('off','corrected')}; c=conv(pp['corrected']); boxes=bboxmap(c); ds={x['member']:x for x in c['glyph_sharing']['decisions']}
    for item in items:
        p=item['page'];b=boxes[(p,item['id'])]; canonical=ds[item['canonical']]; cb=boxes[(canonical['page'],canonical['id'])]
        for engine in ('pdfium','poppler'):
            imgs=[crop(img(source,p,dpi,engine),b),crop(img(pp['off'],p,dpi,engine),b),crop(img(pp['corrected'],p,dpi,engine),b),crop(img(pp['corrected'],canonical['page'],dpi,engine),cb)]
            isolated_crops=[crop(img(isolated[a],p,dpi,engine),b) for a in ('off','corrected')]
            fired=check(imgs[0],*isolated_crops);checks.append(dict(document=name,page=p,id=item['id'],engine=engine,fired=fired))
            if dpi==600 and (name,item['member']) in selected_ids:
                panels.append((name,p,item['id'],engine,imgs))
    cache.clear();print(name,len(items),flush=True)
# Each row uses the same unscaled 600-DPI pixels.
files=[]
for start in range(0,len(panels),30):
    chunk=panels[start:start+30]; cw=max(160, max(max(a.shape[1] for a in v[4]) for v in chunk)+12); rh=max(max(a.shape[0] for a in v[4]) for v in chunk)+42
    canvas=Image.new('RGB',(4*cw,len(chunk)*rh),'white');draw=ImageDraw.Draw(canvas)
    for row,(name,p,id_,engine,imgs) in enumerate(chunk):
        draw.text((2,row*rh+2),f'{name} page {p} id {id_} renderer {engine}',fill='black')
        for col,a in enumerate(imgs):
            draw.text((col*cw+5,row*rh+17),('source','default','corrected','canonical')[col],fill='black')
            canvas.paste(Image.fromarray(a).convert('RGB'),(col*cw+5,row*rh+32))
    path=panel_dir/f'contact-{start//30:03}.png';canvas.save(path);files.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=len(chunk)))
(HERE/'panels-and-owned-check.json').write_text(json.dumps(dict(method='Native render of source and emitted text-only default/corrected PDFs with image and form XObjects removed, cropped by observation bbox; existing owned-component thresholds. Nearby text can overlap and the source mask is inferred from grayscale, so this is an independent approximate check, not exact ownership proof.',checks=checks,panels=files,member_count_600=sum(x['dpi']==600 for x in ns),sampling=('none' if sum(x['dpi']==600 for x in ns)<=100 else 'deterministic document-stratified round robin, first 100 members by member index'),selected_members=[dict(document=x['document'],member=x['member']) for x in selected],panel_rows=len(panels)),indent=2)+'\n')
