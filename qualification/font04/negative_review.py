"""Retain every curated FONT-02 native negative and render P1 style probes."""
from pathlib import Path
import json
import random
import subprocess
import sys
import numpy as np
import pikepdf
from PIL import Image
from qualification.font04.causal import ROOT,CORPUS,glyph_matrix,fit_bbox
from qualification.font04.geometry import register
from qualification.font04.metrics import render,matrix,operands,sha
from qualification.font04.pdf_helpers import font_resource
from qualification.font04.review_sheets import key_process


def save_panel(directory,metadata,identifier,source,current,candidate,details):
    assets=directory/'assets';assets.mkdir(exist_ok=True)
    dpi=details['dpi'];factor=300/dpi
    for name,image in [('source',source),('current',current),('candidate',candidate)]:
        if image.dtype!=np.uint8:image=np.uint8(np.round((1-np.clip(image,0,1))*255))
        im=Image.fromarray(image).convert('L')
        if dpi!=300:im=im.resize((max(1,round(im.width*factor)),max(1,round(im.height*factor))),Image.Resampling.LANCZOS)
        im.save(assets/(identifier+'-'+name+'.png'))
    metadata.append(dict(id=identifier,type='curated-negative',renderer=details['renderer'],**{k:v for k,v in details.items()if k!='renderer'}))


def main():
    directory=Path('qualification/font04/local/review-negatives');directory.mkdir(exist_ok=True);data=json.loads(Path('qualification/font04/calibration-and-negatives.json').read_text());metadata=[]
    for split in ['validation','test']:
        root=Path('qualification/font02/local/hard-negatives');maps=np.load(root/f'{split}-rendered-coverage.npz');decisions=json.loads((root/f'{split}-source-decisions.json').read_text())['records'];by_pair={(r['target'],r['donor'],r['renderer']):r for r in decisions};pages={}
        for index,control in enumerate(data['curated_negatives']['retained_font02']):
            if control['split']!=split:continue
            for engine in ['pdfium','poppler']:
                target,donor=control['target'],control['donor'];r=by_pair[target,donor,engine];pi=r['source_page'];dpi=r['dpi']
                if pi not in pages:
                    with Image.open(CORPUS/split/f'page-{pi}.png')as im:pages[pi]=np.asarray(im.convert('L')).copy()
                x,y,xx,yy=r['bounds'];source=pages[pi][y:yy,x:xx];a=maps[f'{engine}-{target}-baseline'];b=maps[f'{engine}-{target}-{donor}']
                save_panel(directory,metadata,f'known-{index:03}-{engine}',source,a,b,dict(renderer=engine,dpi=dpi,split=split,target=target,donor=donor,category=control['category']))
    for split in ['train','validation','test']:
        root=ROOT/split;rows=json.loads((root/'source.json').read_text())['rows'];byid={r['id']:(i,r)for i,r in enumerate(rows)};fields=np.load(root/'fields.npy');controls=[r for r in data['curated_negatives']['style_pairs']if r['split']==split]
        lookups={page:{o['key']:o for o in json.loads((root/f'curves-{page}/outlines.json').read_text())['records']if'gid'in o}for page in range(3)}
        for page in range(3):
            selected=[r for r in controls if byid[r['target']][1]['page']==page]
            if not selected:continue
            dpi=[200,300,600][page];original=pikepdf.Pdf.open({'train':'qualification/font04/local/train-main.pdf','validation':'qualification/font02/local/hard-negatives/validation-product.pdf','test':'qualification/font01/local/rust-control-test-v2.pdf'}[split]);pdf=pikepdf.Pdf.new();resources={}
            for pi in range(3):resources['C'+str(pi)]=font_resource(pdf,root/f'curves-{pi}/font.ttf',list(lookups[pi].values()))
            pdf.pages.append(original.pages[page]);resources['B']=pdf.pages[0].Resources.Font.F1;del pdf.pages[0]
            commands=[];entries=[]
            for k,control in enumerate(selected):
                i,target=byid[control['target']];j,donor=byid[control['donor']];o=lookups[donor['page']][donor['trace']['line-local']['key']]
                # Fit the completed traced candidate, not an evaluator font.
                x,y=donor['trace']['line-local']['origin'];candidate=np.zeros((64,64));candidate[y:y+o['height'],x:x+o['width']]=np.array(o['coverage']).reshape(o['height'],o['width']);parameters,_=register(fields[i],candidate);f=target['frame'];bbox=[f['cx']+(x-32)/f['scale'],f['baseline']+(y-48)/f['scale'],f['cx']+(x+o['width']-32)/f['scale'],f['baseline']+(y+o['height']-48)/f['scale']];bbox=fit_bbox(target,bbox,parameters)
                bb=target['source']['bbox'];left=int((bb[0]+bb[2])/2)-80;top=int((bb[1]+bb[3])/2)-80;cell=k*2
                for arm,m,gid,font in [('current',matrix(target['current']['matrix']),target['current']['cid'],'B'),('candidate',glyph_matrix(target,o,bbox),o['gid'],'C'+str(donor['page']))]:
                    c=cell+(arm=='candidate');cx=(c%10)*160;cy=(c//10)*160;tf=np.array([[1.,0,(cx-left)*72/dpi],[0,1.,1600*72/dpi-648-(cy-top)*72/dpi],[0,0,1.]])
                    commands.append('BT 0 Tr 0 g /'+font+' 1 Tf '+' '.join(map(str,operands(tf@m)))+f' Tm <{gid:04x}> Tj ET')
                entries.append((control,target,left,top,cell))
            pp=pdf.add_blank_page(page_size=(1600*72/dpi,1600*72/dpi));pp.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(**resources));pp.Contents=pdf.make_stream(('\n'.join(commands)+'\n').encode());path=directory/f'styles-{split}-{page}.pdf';pdf.save(path,deterministic_id=True);original.close()
            with Image.open(CORPUS/split/f'page-{page}.png')as im:source=np.asarray(im.convert('L')).copy()
            for engine in ['pdfium','poppler']:
                rendered=render(path,0,dpi,engine)
                for k,(control,target,left,top,cell)in enumerate(entries):
                    x,y,xx,yy=map(int,target['source']['bbox']);pad=5;x-=pad;y-=pad;xx+=pad;yy+=pad;parts=[]
                    for c in [cell,cell+1]:
                        cx=(c%10)*160;cy=(c//10)*160;parts.append(rendered[y-top+cy:yy-top+cy,x-left+cx:xx-left+cx])
                    identifier=f'style-{split}-{page}-{k}-{engine}'
                    save_panel(directory,metadata,identifier,source[y:yy,x:xx],parts[0],parts[1],dict(renderer=engine,dpi=dpi,split=split,target=control['target'],donor=control['donor'],category=control['category']))
    (directory/'panels.json').write_text(json.dumps(metadata,indent=2));key_process([r['id']for r in metadata],directory/'sealed-key.json');subprocess.run([sys.executable,str(Path(__file__).with_name('review_key.py')),'render',str(directory)],check=True)
    manifest=dict(status='blinded judgments pending',panels=len(metadata),all_74_retained_font02_pairs=True,style_pairs=len(data['curated_negatives']['style_pairs']),pdf=str(directory/'blinded-review.pdf'),sha256=sha(directory/'blinded-review.pdf'),repair_failure='Preserved original artifact and prohibition recorded in calibration-and-negatives.json; no new repair performed.',cross_label='Rejected structurally by label partition before grouping; no cross-label font substitution is generated.')
    Path('qualification/font04/negative-review-manifest.json').write_text(json.dumps(manifest,indent=2));print(manifest)


if __name__=='__main__':main()
