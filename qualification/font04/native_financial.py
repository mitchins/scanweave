"""Native financial evaluation layers retain the original MediaBox and transform.

The real scan's 1813×2655 raster maps to 435×637 pt; nominal 300 DPI is
not an exact raster-to-page transform. This module does not replace it with 72/DPI.
"""
from pathlib import Path
import json
import numpy as np
import pikepdf
from qualification.font04.planner import local_source
from qualification.font04.metrics import operands,matrix


def source_layer(snapshot,base,destination):
    report=json.loads(Path(str(base)+'.json').read_text());geometry=report['pages']
    with pikepdf.open(base)as original:
        pdf=pikepdf.Pdf.new()
        for pi,oldpage in enumerate(original.pages):
            pdf.pages.append(oldpage);page=pdf.pages[-1];objects=pikepdf.Dictionary();commands=[];g=geometry[pi];sx=g['width_pt']/g['raster_width'];sy=g['height_pt']/g['raster_height']
            for row in snapshot['rows']:
                if row['page']!=pi or row['source']is None:continue
                source=row['source'];cov=local_source(source,row['paper']);pixels=np.round((1-cov)*255).astype('uint8');h,w=pixels.shape
                stream=pdf.make_stream(pixels.tobytes());stream.Type=pikepdf.Name.XObject;stream.Subtype=pikepdf.Name.Image;stream.Width=w;stream.Height=h;stream.ColorSpace=pikepdf.Name.DeviceGray;stream.BitsPerComponent=8
                name='I'+str(row['index']);objects['/'+name]=stream;x,y=source['bbox'][:2];x-=2;y-=2
                commands.append(f'q {w*sx:.12f} 0 0 {h*sy:.12f} {x*sx:.12f} {g["height_pt"]-(y+h)*sy:.12f} cm /{name} Do Q')
            page.Resources=pikepdf.Dictionary(XObject=objects);page.Contents=pdf.make_stream(('\n'.join(commands)+'\n').encode())
        pdf.save(destination,deterministic_id=True)


def emitted_layer(snapshot,inventory,bound,path,destination):
    with pikepdf.open(path)as original:
        pdf=pikepdf.Pdf.new()
        for pi,oldpage in enumerate(original.pages):
            pdf.pages.append(oldpage);page=pdf.pages[-1];commands=[]
            for row in snapshot['rows']:
                if row['page']!=pi:continue
                draw=bound[row['index']]
                commands.append('BT 0 Tr 0 g /F1 1 Tf '+' '.join(map(str,draw['matrix']))+f" Tm <{draw['cid']:04x}> Tj ET")
            page.Contents=pdf.make_stream(('\n'.join(commands)+'\n').encode())
        pdf.save(destination,deterministic_id=True)
