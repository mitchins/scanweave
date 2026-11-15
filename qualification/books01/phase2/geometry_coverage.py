#!/usr/bin/env python3
"""Apply the pilot's source-grid crop coverage measurement to stored transforms."""
import json,math,pathlib
import numpy as np
from PIL import Image
B=pathlib.Path('/data/coding/scanweave/work/books01');p=B/'phase2/metrics';count=0
for f in p.glob('*/*.json'):
 x=json.loads(f.read_text());g=x.get('geometry',{})
 if g.get('status')!='accepted':continue
 key=x['id'].split('/')[-1];src=B/'phase2/renders'/key/'src/pdfium-native.png';dst=B/'phase2/renders'/key/x['row']/'pdfium-native.png'
 if not src.exists() or not dst.exists():continue
 with Image.open(src) as a,Image.open(dst) as b:
  w,h=a.size;W,H=b.size;g['source_dimensions']=[w,h];g['output_dimensions']=[W,H];angle=math.radians(g['rotation_degrees']);scale=g['scale_x'];tx,ty=g['translation_px'];xx,yy=np.meshgrid((np.arange(128)+.5)*w/128,(np.arange(128)+.5)*h/128);xx-=tx;yy-=ty;u=(math.cos(angle)*xx+math.sin(angle)*yy)/scale;v=(-math.sin(angle)*xx+math.cos(angle)*yy)/scale;g['out_of_bounds_fraction']=float(((u<0)|(u>=W)|(v<0)|(v>=H)).mean());g['coverage_method']='128x128 source-grid samples inverse-mapped to output; possible crop, not proof of lost content'
 f.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');count+=1
print('geometry coverage:',count)
