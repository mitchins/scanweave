"""Fresh native self-trace with floor on: isolate floor from legacy witness choice."""
from pathlib import Path
import json
import numpy as np
import pikepdf
from PIL import Image
from qualification.font04.causal import ROOT,CORPUS,BASELINES,glyph_matrix,source_native
from qualification.font04.pdf_helpers import font_resource
from qualification.font04.metrics import render,measure,operands,sha


def evaluate(root,split):
    destination=root/split;rows=json.loads((destination/'source.json').read_text())['rows'];results=[]
    labels={r['id']:r for r in map(json.loads,(CORPUS/split/'oracle/labels.jsonl').read_text().splitlines())}if split!='financial'else{}
    if split=='financial':geometry=json.loads(Path('qualification/font04/local/financial-default.pdf.json').read_text())['pages']
    for pi in sorted({r['page']for r in rows}):
        subset=[r for r in rows if r['page']==pi];dpi=subset[0]['dpi'];outlines=json.loads((destination/f'curves-{pi}/outlines.json').read_text())['records'];lookup={o['key']:o for o in outlines if'gid'in o};pdf=pikepdf.Pdf.new();font=font_resource(pdf,destination/f'curves-{pi}/font.ttf',outlines);commands=[];metadata=[]
        for k,row in enumerate(subset):
            o=lookup[row['trace']['native-floor']['key']]
            if split=='financial':
                g=geometry[pi];row['pixel_x_pt']=g['width_pt']/g['raster_width'];row['pixel_y_pt']=g['height_pt']/g['raster_height'];m=glyph_matrix(row,o,row['trace']['native-floor']['bbox']);cx=cy=0;left=top=0
            else:
                b=row['source']['bbox'];left=int((b[0]+b[2])/2)-80;top=int((b[1]+b[3])/2)-80;cx=(k%10)*160;cy=((k%100)//10)*160
                tf=np.array([[1.,0,(cx-left)*72/dpi],[0,1.,1600*72/dpi-648-(cy-top)*72/dpi],[0,0,1.]])
                m=tf@glyph_matrix(row,o,row['trace']['native-floor']['bbox'])
                if k%100==0 and commands:
                    p=pdf.add_blank_page(page_size=(1600*72/dpi,1600*72/dpi));p.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(C=font));p.Contents=pdf.make_stream(('\n'.join(commands)+'\n').encode());commands=[]
            commands.append('BT 0 Tr 0 g /C 1 Tf '+' '.join(map(str,operands(m)))+f" Tm <{o['gid']:04x}> Tj ET")
            metadata.append(dict(row=row,sheet=0 if split=='financial'else k//100,cell=[cx,cy],native=[left,top]))
        if commands:
            size=(subset[0]['page_width'],subset[0]['page_height'])if split=='financial'else(1600*72/dpi,1600*72/dpi);p=pdf.add_blank_page(page_size=size);p.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(C=font));p.Contents=pdf.make_stream(('\n'.join(commands)+'\n').encode())
        path=destination/f'floor-control-{pi}.pdf';pdf.save(path,deterministic_id=True)
        for engine in ['pdfium','poppler']:
            images={sheet:1-render(path,sheet,dpi,engine).astype(float)/255 for sheet in sorted({m['sheet']for m in metadata})}
            if split=='financial':native_source=1-render(destination/'native-source.pdf',pi,dpi,engine).astype(float)/255
            for meta in metadata:
                row=meta['row'];image=images[meta['sheet']];record=dict(id=row['id'],character=row['character'],arm='A-floor-self',renderer=engine,dpi=dpi,damage='real')
                if split=='financial':
                    x,y,xx,yy=map(int,row['source']['bbox']);x-=4;y-=4;xx+=4;yy+=4;record['source']=measure(native_source[y:yy,x:xx],image[y:yy,x:xx])
                else:
                    cx,cy=meta['cell'];left,top=meta['native'];crop=image[cy:cy+160,cx:cx+160];pristine=np.zeros_like(crop);x,y,xx,yy=row['public_bbox']
                    with Image.open(CORPUS/split/'oracle'/f'{row["id"]}-pristine.png')as im:pristine[y-top:yy-top,x-left:xx-left]=1-np.asarray(im.convert('L'),float)/255
                    record['damage']='D'+str(labels[row['id']]['severity']);record['pristine']=measure(pristine,crop);record['source']=measure(source_native(row,left,top,160),crop)
                results.append(record)
        print('floor control',root,split,pi,flush=True)
    (destination/'floor-control-evaluated.json').write_text(json.dumps(dict(records=results,source_sha256=sha(destination/'source.json'))))


if __name__=='__main__':
    for root in [ROOT,Path('qualification/font04/local/causal-extension')]:
        for split in ['train','validation','test']:
            evaluate(root,split)
    evaluate(ROOT,'financial')
