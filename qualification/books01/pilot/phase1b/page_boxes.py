#!/usr/bin/env python3
"""Add page-box changes and fitted source-frame coverage to registrations."""
import json,math,pathlib
import numpy as np,pikepdf
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[2];Q=P/'pilot';p=Q/'results/phase1b/geometry.json';data=json.loads(p.read_text());runs=json.loads((Q/'results/runs.json').read_text()); ADOBE='Acrobat default OCR language (not matched); no Fraktur support; page straightened (deskew)'
def boxes(path):
 with pikepdf.open(path) as f:
  page=f.pages[0];return {'media_box_pt':[float(x) for x in page.mediabox],'crop_box_pt':[float(x) for x in page.cropbox],'page_rotation_degrees':int(page.obj.get('/Rotate',0))}
for id,rows in data['pages'].items():
 key=id.split('/')[-1];source=pathlib.Path(runs[id]['rows']['src']['path']);src=boxes(source)
 for row,renderers in rows.items():
  path=pathlib.Path(runs[id]['rows'][row].get('path',B/'pilot/runs'/key/(row+'.pdf')));out=boxes(path)
  for renderer,dpis in renderers.items():
   for dpi,r in dpis.items():
    r['source_page_boxes']=src;r['output_page_boxes']=out;r['page_box_changed']=src!=out;r['adobe_label']=ADOBE if row=='adobe-E' else None
    if r['status']=='accepted':
     ow,oh=r['output_dimensions'];sw,sh=r['source_dimensions'];ang=math.radians(r['rotation_degrees']);sc=r['scale_x'];tx,ty=r['translation_px']; c=math.cos(ang)*sc;s=math.sin(ang)*sc;x,y=np.meshgrid(np.linspace(0,sw-1,128),np.linspace(0,sh-1,128));dx=x-tx;dy=y-ty;invx=(c*dx+s*dy)/(sc*sc);invy=(-s*dx+c*dy)/(sc*sc);r['out_of_bounds_fraction']=float(((invx<0)|(invy<0)|(invx>=ow)|(invy>=oh)).mean());r['coverage_method']='128x128 uniform source-grid samples outside inverse-mapped output'
p.write_text(json.dumps(data,indent=2)+'\n')
