"""Prepare blinded accepted/rejected and repeated-word native review sheets.

The key is created by a separate process and is never read by analysis. A reviewer
must save judgments before reveal_review.py is run. Rejected panels display the
actual attempted substitution, not the unchanged exception in the complete PDF.
"""
from pathlib import Path
import collections
import json
import random
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import numpy as np
import pikepdf
from PIL import Image,ImageDraw,ImageFont

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from qualification.font04.metrics import render,matrix,operands,sha
from qualification.font04.pdf_helpers import font_resource
from qualification.font04.causal import glyph_matrix

ROOT=Path('qualification/font04/local')


def key_process(ids,destination):
    # Deliberately separate lifecycle. stdout never reveals the mapping.
    request=json.dumps(dict(ids=ids,destination=str(destination)))
    subprocess.run([sys.executable,str(Path(__file__).with_name('review_key.py')),'create'],input=request,text=True,check=True)


def source_pages():
    pages=[]
    with pikepdf.open('qualification/pdf_packaging/groups/financial-input.pdf')as pdf:
        for page in pdf.pages:
            images=[obj for obj in page.Resources.XObject.values()if str(obj.get('/Subtype'))=='/Image']
            if len(images)!=1:raise ValueError('expected one native source image per page')
            pages.append(np.asarray(pikepdf.PdfImage(images[0]).as_pil_image().convert('L')).copy())
    return pages


def main(experiment):
    artifact=Path(str(experiment)+'.font04');directory=ROOT/(experiment.stem+'-review');directory.mkdir(exist_ok=True)
    snapshot=json.loads((artifact/'source.json').read_text());rows=snapshot['rows'];plan=json.loads((artifact/'plan.json').read_text());meta=json.loads((artifact/'frames.json').read_text());outlines=json.loads((artifact/'outlines.json').read_text())['records'];lookup={o['key']:o for o in outlines if 'gid'in o}
    page_geometry=json.loads((ROOT/'financial-default.pdf.json').read_text())['pages']
    for row in rows:
        g=page_geometry[row['page']];row['pixel_x_pt']=g['width_pt']/g['raster_width'];row['pixel_y_pt']=g['height_pt']/g['raster_height']
    assignments={a['member']:a for a in plan['assignments']};rejected={r['member']:r for r in plan['rejection_ledger']};pairs=json.loads((artifact/'pair-ledger.json').read_text());bound=json.loads((artifact/'emitted-bindings.json').read_text());measured=json.loads((ROOT/'checkpoint-B1-full.json').read_text())['per_member']
    if (artifact/'prime-metrics.json').exists():
        measured=[dict(member=r['member'],renderer=r['metric'],accepted=r['accepted'],experimental=r['candidate']) for r in json.loads((artifact/'prime-metrics.json').read_text())['records'] if r['metric'] in ('pdfium','poppler')]
    def page_render(engine,arm,page):
        cache=artifact/f'{engine}-{arm}-{page}.npy'
        if not cache.exists():np.save(cache,render(ROOT/'financial-default.pdf' if arm=='default' else experiment,page,300,engine))
        return np.load(cache)
    randomizer=random.Random(40411);accepted=sorted(assignments);rejects=sorted(rejected)
    sample=set(randomizer.sample(accepted,min(50,len(accepted))));random_rejected=randomizer.sample(rejects,min(50,len(rejects)))
    ownership=plan.get('ownership_veto')
    if ownership:random_rejected=sorted(set(random_rejected)|set(ownership['exceptions']))
    for engine in ['pdfium','poppler']:
        selected=[r for r in measured if r['accepted']and r['renderer']==engine]
        for metric in ['error','area_bias','contour_distance']:
            sample.update(r['member']for r in sorted(selected,key=lambda r:abs(r['experimental'][metric]),reverse=True)[:10])
    for metric in ['area','elongation','counter_difference']:
        candidates=[p for p in pairs if p['member']in assignments and p['canonical']==assignments[p['member']]['canonical']]
        sample.update(p['member']for p in sorted(candidates,key=lambda p:p['checks'].get(metric,{}).get('value',0),reverse=True)[:10])
    # Cross-page/style probes: retain an example from every canonical group and page.
    groups=collections.defaultdict(list)
    for i,a in assignments.items():groups[(a['canonical'],a['page'])].append(i)
    sample.update(min(v)for v in groups.values())
    selected=sorted(sample|set(random_rejected));panels=[]
    proposals={}
    for i in selected:
        if i in assignments:proposals[i]=assignments[i];continue
        attempted=[p for p in pairs if p['member']==i]
        if not attempted:continue
        r=rejected[i];j=r.get('canonical',min(attempted,key=lambda p:p['error'])['canonical'])
        pair=next(p for p in attempted if p['canonical']==j);o=lookup.get('font04-e-'+str(j));frame=meta['frames'][i]
        if o is None or frame is None:continue
        x,y=meta['origins'][j];dx,dy,s=pair['parameters'];left=32+s*(x-.5-32)+dx;top=48+s*(y-.5-48)+dy
        bb=[frame['cx']+(left-32)/frame['scale'],frame['baseline']+(top-48)/frame['scale'],frame['cx']+(left+s*o['width']-32)/frame['scale'],frame['baseline']+(top+s*o['height']-48)/frame['scale']]
        proposals[i]=dict(canonical=j,bbox=bb)
    # Every proposal replaces its current draw in full page context. The raster,
    # neighbouring ink and all other page content are identical on both sides.
    from qualification.font04.context_proposals import contextual_pdf
    proposal_pdf=directory/'attempted-substitutions.pdf'
    contextual_pdf(ROOT/'financial-default.pdf',proposal_pdf,rows,proposals,bound,outlines,artifact/'canonical.ttf')
    sources={engine:[render(Path('qualification/pdf_packaging/groups/financial-input.pdf'),page,300,engine)for page in range(13)]for engine in ['pdfium','poppler']}
    for engine in ['pdfium','poppler']:
        proposed={pi:render(proposal_pdf,pi,300,engine)for pi in sorted({rows[i]['page']for i in proposals})}
        for i in selected:
            row=rows[i];source=row['source']
            if source is None or i not in proposals:continue
            bb=source['bbox'];cx=(bb[0]+bb[2])/2;cy=(bb[1]+bb[3])/2;left=int(cx)-35;top=int(cy)-28;right=left+70;bottom=top+56;page=row['page']
            a=page_render(engine,'default',page);b=page_render(engine,'experimental',page)if i in assignments else proposed[page]
            panel_id=f'glyph-{i:03}-{engine}'
            panels.append(dict(id=panel_id,type='accepted'if i in assignments else'rejected',member=i,page=page,renderer=engine,bounds=[left,top,right,bottom],source=sources[engine][page][top:bottom,left:right],current=a[top:bottom,left:right],candidate=b[top:bottom,left:right],selection='random rejected'if i in random_rejected else'accepted random/tail/cross-page'))
    report=json.loads((ROOT/'financial-default.pdf.json').read_text());words=collections.defaultdict(list)
    for pi,page in enumerate(report['pages']):
        document=ET.fromstring(page['hocr'])
        for element in document.iter():
            if 'ocrx_word'not in element.attrib.get('class','').split():continue
            text=''.join(''.join(element.itertext()).split()).lower();match=re.search(r'\bbbox (\d+) (\d+) (\d+) (\d+)',element.attrib.get('title',''))
            if match and 'e' in text and re.fullmatch('[a-z]{4,}',text):words[text].append((pi,list(map(int,match.groups()))))
    frequent=[(word,instances)for word,instances in words.items()if len({p for p,b in instances})>=2]
    frequent.sort(key=lambda pair:(pair[0]!='expires',-len({p for p,b in pair[1]}),pair[0]))
    word_selection=[]
    for word,instances in frequent[:10]:
        for page,bb in [min(instances),max(instances)]:
            x,y,xx,yy=bb;bounds=[x-3,y-3,xx+3,yy+3];word_selection.append(dict(word=word,page=page,bounds=bounds))
            for engine in ['pdfium','poppler']:
                a=page_render(engine,'default',page);b=page_render(engine,'experimental',page);x,y,xx,yy=bounds
                panels.append(dict(id=f'word-{word}-{page}-{engine}',type='repeated-word',page=page,renderer=engine,bounds=bounds,source=sources[engine][page][y:yy,x:xx],current=a[y:yy,x:xx],candidate=b[y:yy,x:xx],selection='same word on distant pages'))
    ids=[p['id']for p in panels];key_process(ids,directory/'sealed-key.json')
    # Rendering U/V is delegated so this authoring process never reads the key.
    metadata=[];assets=directory/'assets';assets.mkdir(exist_ok=True)
    for panel in panels:
        for kind in ['source','current','candidate']:Image.fromarray(panel.pop(kind)).save(assets/(panel['id']+'-'+kind+'.png'))
        metadata.append(panel)
    (directory/'panels.json').write_text(json.dumps(metadata,indent=2))
    (directory/'selection.json').write_text(json.dumps(dict(seed=40411,accepted=sorted(sample),random_rejected=random_rejected,mandatory_rejected_n=len(random_rejected),repeated_words=word_selection,key_policy='Do not reveal until all judgments are saved.'),indent=2))
    subprocess.run([sys.executable,str(Path(__file__).with_name('review_key.py')),'render',str(directory)],check=True)
    compact=dict(panels=len(panels),random_rejected_members=len(random_rejected),accepted_members=len(sample),both_renderers=True,source_and_randomized_UV=True,reading_size_and_400_percent=True,review_pdf=str(directory/'blinded-review.pdf'),review_pdf_sha256=sha(directory/'blinded-review.pdf'),judgments=str(directory/'judgments-template.json'),key=str(directory/'sealed-key.json'),status='awaiting independent judgments; key not revealed')
    Path('qualification/font04/'+experiment.stem+'-review-manifest.json').write_text(json.dumps(compact,indent=2));print(compact)


if __name__=='__main__':main(Path(sys.argv[1]))
