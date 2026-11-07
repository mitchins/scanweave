#!/usr/bin/env python3
"""Create one indexed review sheet per page with a changed image stream."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pikepdf
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from scipy.ndimage import uniform_filter

P=argparse.ArgumentParser(); P.add_argument('name'); P.add_argument('source'); P.add_argument('default'); P.add_argument('candidate'); P.add_argument('outdir'); P.add_argument('--adobe'); P.add_argument('--archive'); A=P.parse_args()
out=Path(A.outdir); out.mkdir(parents=True,exist_ok=True)
docs=[pdfium.PdfDocument(x) for x in (A.source,A.default,A.candidate)]; pdfs=[pikepdf.open(x) for x in (A.default,A.candidate)]
refs=[pdfium.PdfDocument(x) for x in (A.adobe,A.archive)] if A.adobe and A.archive else []
def imhashes(pg):
    return sorted(hashlib.sha256(x.read_raw_bytes()).hexdigest() for x in (pg.get('/Resources',{}).get('/XObject') or {}).values() if x.get('/Subtype')=='/Image')
def render(doc,i): return doc[i].render(scale=300/72).to_pil().convert('RGB')
def sheet(images,labels,box,path):
    thumbs=[]; crops=[]
    for im in images:
        im=im.resize(images[0].size,Image.Resampling.BICUBIC)
        thumb=im.copy(); thumb.thumbnail((700,900),Image.Resampling.LANCZOS)
        thumbs.append(thumb); crops.append(im.crop(box).resize(((box[2]-box[0])*3,(box[3]-box[1])*3),Image.Resampling.NEAREST))
    tw=max(im.width for im in thumbs); th=max(im.height for im in thumbs); cw=max(im.width for im in crops); ch=max(im.height for im in crops)
    rowh=th+ch+50; sheet=Image.new('RGB',(max(tw,cw)*len(images),rowh),'white'); d=ImageDraw.Draw(sheet)
    for j,(t,c,label) in enumerate(zip(thumbs,crops,labels)):
        x=j*max(tw,cw); d.text((x+5,5),label,fill='black'); sheet.paste(t,(x,25)); sheet.paste(c,(x,th+40))
    sheet.save(path,optimize=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()
index=[]
(out/f'{A.name}-index.json').write_text('[]\n')
for i in range(len(docs[0])):
    if imhashes(pdfs[0].pages[i])==imhashes(pdfs[1].pages[i]): continue
    images=[render(doc,i) for doc in docs]
    if images[2].size!=images[1].size: images[2]=images[2].resize(images[1].size,Image.Resampling.BICUBIC)
    diff=np.mean(np.abs(np.asarray(images[1],dtype=np.float32)-np.asarray(images[2],dtype=np.float32)),axis=2)
    small=np.asarray(Image.fromarray(diff).resize((max(1,diff.shape[1]//8),max(1,diff.shape[0]//8)),Image.Resampling.BOX))
    smooth=uniform_filter(small,size=16); y,x=np.unravel_index(np.argmax(smooth),smooth.shape); cx=int(x*8); cy=int(y*8)
    x0=max(0,min(images[0].width-128,cx-64)); y0=max(0,min(images[0].height-128,cy-64)); box=(x0,y0,x0+128,y0+128)
    path=out/f'{A.name}-p{i+1:03d}.png'; digest=sheet(images,['source','default','150-DPI option'],box,path)
    row={'page':i+1,'crop_300dpi':box,'panel':str(path),'sha256':digest}
    if refs:
        rp=out/f'{A.name}-p{i+1:03d}-references.png'; row['references']=str(rp)
        reference_images=[render(d,i).resize(images[0].size,Image.Resampling.BICUBIC) for d in refs]
        row['references_sha256']=sheet(reference_images,['Adobe XI','Archive MRC'],box,rp)
    index.append(row); (out/f'{A.name}-index.json').write_text(json.dumps(index,indent=2)+'\n')
    print(path,flush=True)
