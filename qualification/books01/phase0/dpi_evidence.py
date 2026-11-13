#!/usr/bin/env python3
"""Collect raw DPI evidence for dev TIFFs; never infer a DPI from dimensions."""
import json, pathlib, xml.etree.ElementTree as ET
from PIL import Image
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]
result={}
for p in json.loads((P/'corpus.proposed.json').read_text())['pages']:
    if p['source']!='ocr-d-quiver' or p['split']!='dev': continue
    directory=B/'src/quiver'/p['repo'].split('/')[1]/'data'/p['work']; image=directory/'GT-PAGE'/(p['page']+'.tif')
    with Image.open(image) as im:
        size=im.size; tags=im.tag_v2; x=tags.get(282); y=tags.get(283); unit=tags.get(296)
        x=float(x) if x else None; y=float(y) if y else None
        inch_per_unit={2:1.0,3:1/2.54}.get(unit)
        implied=[round(size[0]/x*inch_per_unit*25.4,2),round(size[1]/y*inch_per_unit*25.4,2)] if x and y and inch_per_unit else None
    root=ET.parse(directory/'mets.xml').getroot(); extent=[]
    for e in root.iter():
        if e.tag.rsplit('}',1)[-1]=='extent':
            value=' '.join(''.join(e.itertext()).split())
            if value: extent.append(value)
    result[p['id']]={'pixels':size,'tiff_x_resolution':x,'tiff_y_resolution':y,'tiff_resolution_unit':unit,'implied_size_mm':implied,'mets_extents':extent,'resolved_dpi':None,'resolution_status':'unresolved; compare physical description and catalogue evidence'}
(B/'dpi-evidence.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
