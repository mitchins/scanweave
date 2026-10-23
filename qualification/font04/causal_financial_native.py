"""Re-evaluate financial ladder on original pages, never on a nominal-DPI atlas."""
from pathlib import Path
import json
import sys
import numpy as np
import pikepdf
from qualification.font04.causal import ROOT,ARMS,glyph_matrix,fit_bbox
from qualification.font04.metrics import render,matrix,operands,measure,sha
from qualification.font04.pdf_helpers import font_resource
from qualification.font04.native_financial import source_layer


def main():
    root=ROOT/'financial';data=json.loads((root/'source.json').read_text());rows=data['rows'];byid={r['id']:r for r in rows};decisions=json.loads((root/'decisions.json').read_text())['records'];geometry=json.loads(Path('qualification/font04/local/financial-default.pdf.json').read_text())['pages']
    lookup={page:{o['key']:o for o in json.loads((root/f'curves-{page}/outlines.json').read_text())['records']if'gid'in o}for page in range(13)}
    for row in rows:
        g=geometry[row['page']];row['pixel_x_pt']=g['width_pt']/g['raster_width'];row['pixel_y_pt']=g['height_pt']/g['raster_height']
    for arm in ARMS:
        with pikepdf.open('qualification/font04/local/financial-default.pdf')as original:
            pdf=pikepdf.Pdf.new();resources={}
            for pi in range(13):resources['C'+str(pi)]=font_resource(pdf,root/f'curves-{pi}/font.ttf',list(lookup[pi].values()))
            pdf.pages.append(original.pages[0]);resources['B']=pdf.pages[0].Resources.Font.F1;del pdf.pages[0]
            for pi in range(13):
                pdf.pages.append(original.pages[pi]);page=pdf.pages[-1];page.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(**resources));commands=[]
                for decision in decisions:
                    if decision['arm']!=arm or decision['page']!=pi:continue
                    row=byid[decision['id']];parameters=decision['parameters']
                    if arm in ['A0','A1']:
                        m=matrix(row['current']['matrix']);gid=row['current']['cid'];font='B'
                        if arm=='A1':
                            f=row['frame'];dx,dy,scale=parameters;center=[f['cx'],f['baseline']];shift=np.array([dx,dy])/f['scale'];native=np.array([[scale,0,center[0]*(1-scale)+shift[0]],[0,scale,center[1]*(1-scale)+shift[1]],[0,0,1.]])
                            pt=np.array([[row['pixel_x_pt'],0,0],[0,-row['pixel_y_pt'],row['page_height']],[0,0,1.]])
                            m=pt@native@np.linalg.inv(pt)@m
                    else:
                        kind={'A2':'native-off','A3':'native-local','A4':'line-local','F-self':'line-local','F-medoid':'line-local','R-floor':'line-floor','R-normalization':'line-crop','R-frame':'native-local','cap-current':'native-off','cap-raised':'native-cap'}[arm]
                        donor=byid[decision['donor']];o=lookup[donor['page']][donor['trace'][kind]['key']];font='C'+str(donor['page']);gid=o['gid']
                        if arm=='F-medoid':
                            x,y=donor['trace'][kind]['origin'];f=row['frame'];bbox=[f['cx']+(x-32)/f['scale'],f['baseline']+(y-48)/f['scale'],f['cx']+(x+o['width']-32)/f['scale'],f['baseline']+(y+o['height']-48)/f['scale']]
                        else:bbox=row['trace'][kind]['bbox']
                        if arm in ['F-self','F-medoid','R-floor','R-normalization','R-frame']:bbox=fit_bbox(row,bbox,parameters)
                        m=glyph_matrix(row,o,bbox)
                    commands.append('BT 0 Tr 0 g /'+font+' 1 Tf '+' '.join(map(str,operands(m)))+f' Tm <{gid:04x}> Tj ET')
                page.Contents=pdf.make_stream(('\n'.join(commands)+'\n').encode())
            pdf.save(root/f'native-{arm}.pdf',deterministic_id=True)
        print('financial native built',arm,flush=True)
    snapshot=json.loads(Path('qualification/font04/local/financial-experimental-v2.pdf.font04/source.json').read_text());source_pdf=root/'native-source.pdf';source_layer(snapshot,Path('qualification/font04/local/financial-default.pdf'),source_pdf)
    results=[]
    for engine in ['pdfium','poppler']:
        for pi in range(13):
            target_page=1-render(source_pdf,pi,300,engine).astype(float)/255
            for arm in ARMS:
                actual=1-render(root/f'native-{arm}.pdf',pi,300,engine).astype(float)/255
                for row in rows:
                    if row['page']!=pi:continue
                    x,y,xx,yy=map(int,row['source']['bbox']);pad=4;x-=pad;y-=pad;xx+=pad;yy+=pad
                    results.append(dict(id=row['id'],character='e',arm=arm,renderer=engine,dpi=300,damage='real',source=measure(target_page[y:yy,x:xx],actual[y:yy,x:xx])))
            print('financial native measured',engine,pi,flush=True)
    old=root/'evaluated-atlas-superseded.json'
    if not old.exists()and(root/'evaluated.json').exists():old.write_bytes((root/'evaluated.json').read_bytes())
    (root/'evaluated.json').write_text(json.dumps(dict(records=results,decisions_sha256=sha(root/'decisions.json'),measurement='Original MediaBox and authoritative raster-to-page transform; source layer rendered per engine. Supersedes nominal-DPI atlas financial metrics.')))


if __name__=='__main__':main()
