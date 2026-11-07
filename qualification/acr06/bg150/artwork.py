#!/usr/bin/env python3
"""Measure manually identified artwork/photo crops with 300-DPI PDFium renders."""
import argparse,json
from pathlib import Path
import numpy as np
import pypdfium2 as pdfium
from PIL import Image
from skimage.metrics import structural_similarity

regions={'historical':[(1,'ornament',[.20,.60,.85,.73]),(2,'decorative initial',[.07,.22,.36,.40]),(4,'decorative initial',[.22,.61,.60,.84])],
         'mixed':[(1,'illustration',[.02,.18,.36,.70])],
         'receipts':[(i,'receipt photograph',[0,0,1,1]) for i in range(1,11)],
         'fresh1':[(1,'halftone and synthetic tonal artwork',[.05,.76,.80,.95])],
         'fresh2':[(1,'halftone and synthetic tonal artwork',[.05,.76,.80,.95])]}
p=argparse.ArgumentParser(); p.add_argument('name');p.add_argument('source');p.add_argument('default');p.add_argument('candidate');p.add_argument('output');a=p.parse_args()
docs=[pdfium.PdfDocument(f) for f in (a.source,a.default,a.candidate)]; rows=[]
for page,label,rel in regions.get(a.name,[]):
    images=[d[page-1].render(scale=300/72).to_pil().convert('L') for d in docs]; size=images[0].size
    images=[im if im.size==size else im.resize(size,Image.Resampling.BICUBIC) for im in images]
    box=tuple(round(rel[j]*size[j%2]) for j in range(4)); images=[im.crop(box) for im in images]
    arrays=[np.asarray(im) for im in images]
    rows.append({'page':page,'region':label,'relative_box':rel,'box_300dpi':box,'ssim_default':float(structural_similarity(arrays[0],arrays[1],data_range=255)),'ssim_candidate':float(structural_similarity(arrays[0],arrays[2],data_range=255))})
Path(a.output).write_text(json.dumps(rows,indent=2)+'\n')
