"""Identical-context B2-prime panels; private staging, separate blinding process."""
from pathlib import Path
import collections,json,multiprocessing,os,random,re,subprocess,sys,math,shutil
import numpy as np,pypdfium2 as pdfium
from PIL import Image
from qualification.font04.metrics import inspect,render,sha
from qualification.font04.class_metrics import bind,crop_render
from qualification.font04.context_instances import contextual_instances
from qualification.font04.composite_transport import emit
from qualification.font04.planner import frame_bbox
from qualification.font04.b2prime import BASE,ROOT,ART
CTX=None

def init_worker(cache,pdf):
    global CTX
    CTX=(cache,Path(pdf),pdfium.PdfDocument(pdf))

def panel_worker(task):
    cache,path,doc=CTX;i,page,engine,bounds=task;x,y,xx,yy=bounds
    source=np.load(cache/f'{engine}-source-{page}.npy',mmap_mode='r')[y:yy,x:xx].copy();current=np.load(cache/f'{engine}-default-{page}.npy',mmap_mode='r')[y:yy,x:xx].copy();a=crop_render(path,doc,i,bounds,engine);candidate=np.rint((1-a)*255).astype('uint8');return source,current,candidate

def write_panels(staging,cache,context_pdf,jobs,metadata):
    # workers have separately opened PDFium files, never inherited seek state.
    with multiprocessing.get_context('spawn').Pool(8,initializer=init_worker,initargs=(cache,str(context_pdf))) as pool:
        for meta,(source,current,candidate) in zip(metadata,pool.imap(panel_worker,jobs,chunksize=2)):
            assert source.shape==current.shape==candidate.shape,(meta,source.shape,current.shape,candidate.shape)
            for name,array in [('source',source),('current',current),('candidate',candidate)]:Image.fromarray(array).save(staging/'assets'/(meta['asset']+'-'+name+'.png'))
    return metadata

def bounds_for(r):
    x,y,xx,yy=map(int,r['source']['bbox']);return [max(0,x-25),max(0,y-16),min(math.ceil(r['page_width']*300/72),xx+25),min(math.ceil(r['page_height']*300/72),yy+16)]

def main():
    points=json.loads((BASE/'b2prime-points.json').read_text())['points'];snapshot=json.loads((ART/'source.json').read_text());rows=snapshot['rows'];old=json.loads((ROOT/'financial-B2-PV.pdf.font04/plan.json').read_text());pv={a['member'] for a in old['assignments']};rng=random.Random(241024);staging=ROOT/'B2prime-review-private-staging';assert not staging.exists();staging.mkdir(mode=0o700);(staging/'assets').mkdir();cache=ROOT/'B2prime-review-page-cache';cache.mkdir(exist_ok=True)
    for engine in ['pdfium','poppler']:
        for name,path in [('source',Path('qualification/pdf_packaging/groups/financial-input.pdf')),('default',ROOT/'financial-default.pdf')]:
            for page in range(13):
                p=cache/f'{engine}-{name}-{page}.npy'
                if not p.exists():np.save(p,render(path,page,300,engine))
    allmeta=[];selection={};plans={};metrics={}
    for point in points:
        label=point['label'];path=Path(point['pdf']);art=Path(str(path)+'.font04');plan=json.loads((art/'plan.json').read_text());plans[label]=plan;mm=json.loads((art/'class-metrics.json').read_text());metrics[label]=mm;aa={a['member'] for a in plan['assignments']};new=sorted(aa-pv);random_new=rng.sample(new,200) if len(new)>200 else new;selected=set(random_new)
        # Protocol tails: each class, all four references, plus area/shape screens.
        for metric in ['analytic','direct','pdfium','poppler']:
            for char in sorted({r['character'] for r in rows}):
                rr=[r for r in mm['records'] if r['metric']==metric and r['character']==char and r['accepted']]
                for key in ['error','area_bias','contour_distance']:
                    selected.update(r['member'] for r in sorted(rr,key=lambda r:abs(r['candidate'][key]),reverse=True)[:10])
                selected.update(r['member'] for r in sorted(rr,key=lambda r:r['candidate']['error']-r['default']['error'],reverse=True)[:10])
                population=sorted(i for i in aa if rows[i]['character']==char);selected.update(rng.sample(population,min(3,len(population))))
        # Structural tails in the retained pair ledger (same hard-check values).
        assignments={a['member']:a for a in plan['assignments']};pairlookup={(p['member'],p['canonical']):p for p in json.loads((ART/'pair-ledger.json').read_text())}
        for char in sorted({r['character'] for r in rows}):
            pp=[pairlookup[i,a['canonical']] for i,a in assignments.items() if rows[i]['character']==char and (i,a['canonical']) in pairlookup]
            for key in ['area','elongation','counter_difference']:
                selected.update(p['member'] for p in sorted(pp,key=lambda p:p['checks'].get(key,{}).get('value',0),reverse=True)[:10])
        selection[label]=dict(pdf_sha256=sha(path),substituted=len(aa),newly_admitted=len(new),random_newly_admitted=sorted(random_new),reviewed_accepted=sorted(selected),random_seed=241024)
        if not selected:continue
        bound=bind(snapshot,inspect(path));context=staging/f'context-{label}.pdf';page_map=contextual_instances(ROOT/'financial-default.pdf',path,context,rows,selected,bound);jobs=[];meta=[]
        for i,review_page in page_map.items():
            b=bounds_for(rows[i])
            for engine in ['pdfium','poppler']:
                asset=f'item{len(allmeta)+len(meta):06}';m=dict(asset=asset,member=i,point=label,type='accepted',newly_admitted=i not in pv,page=rows[i]['page'],renderer=engine,bounds=b,context_pdf=str(context),context_page=review_page);meta.append(m);jobs.append((review_page,rows[i]['page'],engine,b))
        allmeta.extend(write_panels(staging,cache,context,jobs,meta));print('review accepted',label,len(selected),flush=True)
    rejected_sets=[{r['member'] for r in p['rejection_ledger'] if rows[r['member']]['source'] is not None and 'canonical'in r} for p in plans.values()];common=set.intersection(*rejected_sets);assert len(common)>=150;random_rejected=rng.sample(sorted(common),150);owned=set().union(*(set(p['ownership_veto']['exceptions']) for p in plans.values()));rejected=set(random_rejected)|owned
    # Mandatory material cases: exact reviewed attempts, not the current-side case.
    material=json.loads((BASE/'b2prime-material-regressions.json').read_text())['regressions'];b1rows=json.loads((ROOT/'financial-B1prime-PV.pdf.font04/source.json').read_text())['rows'];identity={(r['page'],r['id'],r['character']):r['index'] for r in rows};material_pairs={}
    for case in material:
        i,j=case['member'],case['canonical']
        if 'b1prime' in case['review']:
            i=identity[(b1rows[i]['page'],b1rows[i]['id'],b1rows[i]['character'])];j=identity[(b1rows[j]['page'],b1rows[j]['id'],b1rows[j]['character'])]
        material_pairs[i]=j;rejected.add(i)
    pairs=json.loads((ART/'pair-ledger.json').read_text());by=collections.defaultdict(list)
    for p in pairs:by[p['member']].append(p)
    meta=json.loads((ART/'frames.json').read_text());out=json.loads((ART/'outlines.json').read_text())['records'];lookup={int(o['key'].rsplit('-',1)[1]):o for o in out if 'gid'in o};proposals={};members=[]
    from qualification.font04.geometry import register
    fields=np.load(ART/'fields.npy')
    for i in sorted(rejected):
        pp=by[i]
        if not pp:continue
        if i in material_pairs:
            j=material_pairs[i];p=next((p for p in pp if p['canonical']==j),None)
            if p is None:
                o=lookup[j];canvas=np.zeros((64,64));x,y=meta['origins'][j];canvas[y:y+o['height'],x:x+o['width']]=np.array(o['coverage']).reshape(o['height'],o['width']);p=dict(canonical=j,parameters=register(fields[i],canvas)[0])
        else:p=min(pp,key=lambda p:(len(p['reasons']),p['error']));j=p['canonical']
        o=lookup[j];proposals[i]=dict(canonical=j,bbox=frame_bbox(meta['frames'][i],meta['origins'][j],(o['width'],o['height']),p['parameters']));members.append(i)
    # Pixel-to-point geometry is explicit, matching complete-output placement.
    geometry=json.loads((ROOT/'financial-default.pdf.json').read_text())['pages']
    for r in rows:
        g=geometry[r['page']];r.update(pixel_x_pt=g['width_pt']/g['raster_width'],pixel_y_pt=g['height_pt']/g['raster_height'])
    baseline_bound=json.loads((ART/'emitted-bindings.json').read_text());attempt_plan=dict(assignments=[dict(p,member=i,page=rows[i]['page'],occurrence=rows[i]['occurrence'],id=rows[i]['id'],character=rows[i]['character']) for i,p in proposals.items()]);attempt_pdf=staging/'rejected-attempts-metric-transport.pdf';attempt_account=emit(attempt_pdf,attempt_plan);(staging/'rejected-attempts-account.json').write_text(json.dumps(attempt_account,indent=2)+'\n')
    # This is a review-only counterfactual containing vetoed attempts, never an
    # admitted operating point. The real metric-preserving compositor is used.
    attempted_bound=bind(snapshot,inspect(attempt_pdf));context=staging/'context-common-attempts.pdf';page_map=contextual_instances(ROOT/'financial-default.pdf',attempt_pdf,context,rows,set(proposals),attempted_bound);jobs=[];panelmeta=[]
    for i,review_page in page_map.items():
        b=bounds_for(rows[i])
        for engine in ['pdfium','poppler']:
            asset=f'item{len(allmeta)+len(panelmeta):06}';m=dict(asset=asset,member=i,type='rejected' if i in common else 'mandatory-regression-or-owned-attempt',points=[k for k,p in plans.items() if i not in {a['member'] for a in p['assignments']}],random_rejected=i in random_rejected,material_regression=i in material_pairs,renderer=engine,page=rows[i]['page'],bounds=b,context_pdf=str(context),context_page=review_page);panelmeta.append(m);jobs.append((review_page,rows[i]['page'],engine,b))
    allmeta.extend(write_panels(staging,cache,context,jobs,panelmeta));assert set(random_rejected)<=set(page_map)
    # Repeated words and amounts/dates on distant pages, in both engines.
    import xml.etree.ElementTree as ET
    report=json.loads((ROOT/'financial-default.pdf.json').read_text());words=collections.defaultdict(list)
    for pi,page in enumerate(report['pages']):
        for element in ET.fromstring(page['hocr']).iter():
            if 'ocrx_word' not in element.attrib.get('class','').split():continue
            token=''.join(''.join(element.itertext()).split()).lower();match=re.search(r'\bbbox (\d+) (\d+) (\d+) (\d+)',element.attrib.get('title',''))
            if match and (re.fullmatch('[a-z]{4,}',token) or re.fullmatch(r'[$€£]?[0-9][0-9,./:-]*',token)):words[token].append((pi,list(map(int,match.groups()))))
    frequent=sorted([(w,v) for w,v in words.items() if len({pi for pi,b in v})>=2],key=lambda p:(-len(p[1]),p[0]));chosen=[p for p in frequent if re.fullmatch('[a-z]{4,}',p[0])][:5]+[p for p in frequent if re.search('[0-9]',p[0])][:5]
    for point in points:
        label=point['label'];path=Path(point['pdf'])
        for engine in ['pdfium','poppler']:
            pages={}
            for word,instances in chosen:
                for pi,b in [min(instances),max(instances)]:
                    if pi not in pages:pages[pi]=render(path,pi,300,engine)
                    x,y,xx,yy=b;x=max(0,x-3);y=max(0,y-3);xx+=3;yy+=3;asset=f'item{len(allmeta):06}';m=dict(asset=asset,type='repeated-word',point=label,word=word,page=pi,renderer=engine,bounds=[x,y,xx,yy]);allmeta.append(m)
                    arrays=dict(source=np.load(cache/f'{engine}-source-{pi}.npy',mmap_mode='r'),current=np.load(cache/f'{engine}-default-{pi}.npy',mmap_mode='r'),candidate=pages[pi])
                    for name,array in arrays.items():Image.fromarray(array[y:yy,x:xx]).save(staging/'assets'/(asset+'-'+name+'.png'))
    (staging/'panels.json').write_text(json.dumps(allmeta,indent=2)+'\n');selection['rejected']=dict(common_population=len(common),random_members=sorted(random_rejected),reviewed_members=sorted(page_map),all_owned_exceptions_included=owned<=set(page_map),material_cases=16)
    (staging/'selection.json').write_text(json.dumps(selection,indent=2)+'\n');public=ROOT/'B2prime-blind-review';key=ROOT/'B2prime-review-keys'/'key.json';subprocess.run([sys.executable,'-m','qualification.font04.seal_b2prime_review',str(staging),str(public),str(key)],check=True)
    manifest=dict(status='reviewer-pending; key never opened by analysis',review_pdf=str(public/'blinded-review.pdf'),sha256=sha(public/'blinded-review.pdf'),public_directory=str(public),key_separate=str(key),selection_private=str(staging/'selection.json'),points={label:{k:v for k,v in d.items() if k not in ['random_newly_admitted','reviewed_accepted']}|dict(random_new_review_n=len(d['random_newly_admitted']),accepted_review_n=len(d['reviewed_accepted'])) for label,d in selection.items() if label!='rejected'},rejected_members=len(page_map),random_rejected_members=150,both_renderers=True,context='Every glyph comparison uses identical complete default page context; only the target draw is replaced using its exact emitted composite. Rejected attempts also replace only the target.',blinding='Separate process, cryptographic random opaque panel IDs and order, random U/V; public assets contain Source/U/V only. Key and private arm-labelled staging are outside the public directory.',panels=len(allmeta),material_regressions=16)
    (BASE/'b2prime-review-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');shutil.rmtree(staging/'assets');print('REVIEW SEALED',len(allmeta),flush=True)

if __name__=='__main__':main()
