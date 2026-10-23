"""Audit complete financial PDFs, independently of the planner's estimates."""
from pathlib import Path
import collections
import io
import json
import os
import re
import subprocess
import sys
import numpy as np
import pikepdf
import pypdfium2 as pdfium
from PIL import Image
from scipy import ndimage
from scipy.optimize import linear_sum_assignment

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from qualification.font04.metrics import inspect,render,measure,summary,sha,matrix,operands
from qualification.font04.planner import local_source

ROOT=Path('qualification/font04/local');BASE=ROOT/'financial-default.pdf'


def bindings(snapshot,inventory):
    result={}
    for page in range(13):
        src=[r for r in snapshot['rows'] if r['page']==page];draws=[r for r in inventory['draws'] if r['page']==page and r['character']=='e']
        if not src:continue
        a=np.array([[(r['bbox'][0]+r['bbox'][2])/2,(r['bbox'][1]+r['bbox'][3])/2]for r in src]);b=np.array([[r['center'][0]*300/72,(src[0]['page_height']-r['center'][1])*300/72]for r in draws])
        costs=np.linalg.norm(a[:,None]-b[None],axis=2);ii,jj=linear_sum_assignment(costs)
        for i,j in zip(ii,jj):
            if costs[i,j]>10:raise ValueError('ambiguous financial emitted binding')
            result[src[i]['index']]=draws[j]
    return result


def isolated_glyphs(snapshot,inventory,path,tag):
    from qualification.font04.native_financial import emitted_layer
    bound=bindings(snapshot,inventory);destination=ROOT/f'financial-{tag}-isolated-e.pdf'
    emitted_layer(snapshot,inventory,bound,path,destination)
    result={}
    for engine in ['pdfium','poppler']:
        for pi in range(13):
            image=render(destination,pi,300,engine)
            for row in snapshot['rows']:
                if row['page']!=pi:continue
                b=row['source']['bbox']if row['source']else row['bbox'];left=int((b[0]+b[2])/2)-80;top=int((b[1]+b[3])/2)-80
                result[(engine,row['index'])]=(image[top:top+160,left:left+160],[left,top])
    return result


def runtime(path):
    text=path.read_text();out={}
    for key in ['User time (seconds)','System time (seconds)','Maximum resident set size (kbytes)']:
        found=re.search(re.escape(key)+r':\s*([\d.]+)',text)
        if found:out[key]=float(found[1])
    found=re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\S+)',text)
    if found:out['wall_time']=found[1]
    return out


def check_pdf(path):
    env=dict(os.environ,LD_LIBRARY_PATH=str(Path('tools/dist/lib').resolve()))
    q=subprocess.run(['tools/dist/bin/qpdf','--check',str(path)],env=env,capture_output=True,text=True)
    with pikepdf.open(path)as pdf:
        data=pdf.pages[0].Resources.Font.F1.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()
    font=Path(str(path)+'.ttf');font.write_bytes(data)
    ots=subprocess.run(['tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize',str(font),str(font)+'.sanitized'],capture_output=True,text=True)
    return dict(qpdf=dict(returncode=q.returncode,output=q.stdout+q.stderr),ots=dict(returncode=ots.returncode,output=ots.stdout+ots.stderr))


def main(experiment):
    artifact=Path(str(experiment)+'.font04');snapshot=json.loads((artifact/'source.json').read_text());plan=json.loads((artifact/'plan.json').read_text());assigned={r['member']:r for r in plan['assignments']}
    inventories={name:inspect(path)for name,path in [('default',BASE),('experimental',experiment)]}
    bound=bindings(snapshot,inventories['default']);(artifact/'emitted-bindings.json').write_text(json.dumps(bound))
    programs={}
    for name,inv in inventories.items():
        visible_fonts={r['font_hash']for r in inv['draws']}
        fonts=[f for k,f in inv['fonts'].items()if k in visible_fonts]
        programs[name]=collections.Counter(h for f in fonts for h in f['hashes'][1:])
    retired=programs['default']-programs['experimental'];added=programs['experimental']-programs['default']
    stats={}
    for name,inv in inventories.items():
        draws=inv['draws'];es=[r for r in draws if r['character']=='e'];fonts={r['font_hash']for r in draws}
        stats[name]=dict(complete_pdf_bytes=inv['bytes'],sha256=inv['sha256'],visible_draws=len(draws),visible_designs=len({(r['font_hash'],r['gid'])for r in draws}),e_draws=len(es),e_designs=len({(r['font_hash'],r['gid'])for r in es}),e_draws_per_design=len(es)/len({(r['font_hash'],r['gid'])for r in es}),required_slots=sum(f['slots']for k,f in inv['fonts'].items()if k in fonts),encoded_font_bytes=sum(f['encoded_bytes']for k,f in inv['fonts'].items()if k in fonts),decoded_font_bytes=sum(f['decoded_bytes']for k,f in inv['fonts'].items()if k in fonts),outline_points=sum(f['outline_points']for k,f in inv['fonts'].items()if k in fonts),validation=check_pdf(BASE if name=='default'else experiment))
    isolated={name:isolated_glyphs(snapshot,inv,BASE if name=='default'else experiment,name)for name,inv in inventories.items()}
    from qualification.font04.native_financial import source_layer
    source_pdf=ROOT/'financial-source-owned.pdf';source_layer(snapshot,BASE,source_pdf)
    records=[];page_renders=[]
    for engine in ['pdfium','poppler']:
        for page in range(13):
            source_image=1-render(source_pdf,page,300,engine).astype(float)/255
            cached_a=artifact/f'{engine}-default-{page}.npy';cached_b=artifact/f'{engine}-experimental-{page}.npy'
            a=np.load(cached_a) if cached_a.exists() else render(BASE,page,300,engine);b=np.load(cached_b) if cached_b.exists() else render(experiment,page,300,engine)
            if a.shape!=b.shape:raise ValueError('render geometry changed')
            np.save(artifact/f'{engine}-default-{page}.npy',a);np.save(artifact/f'{engine}-experimental-{page}.npy',b)
            page_renders.append(dict(renderer=engine,page=page,changed_pixels=int((a!=b).sum())))
            for row in snapshot['rows']:
                if row['page']!=page or row['source']is None:continue
                source=row['source'];x0,y0,x1,y1=map(int,source['bbox']);pad=4;left,top,right,bottom=x0-pad,y0-pad,x1+pad,y1+pad;h,w=bottom-top,right-left
                halo=local_source(source,row['paper']);yy,xx=np.mgrid[:h,:w];target=source_image[top:bottom,left:right]
                iso_a,(ax,ay)=isolated['default'][(engine,row['index'])];iso_b,(bx,by)=isolated['experimental'][(engine,row['index'])]
                current=1-iso_a[top-ay:bottom-ay,left-ax:right-ax].astype(float)/255;candidate=1-iso_b[top-by:bottom-by,left-bx:right-bx].astype(float)/255
                records.append(dict(member=row['index'],page=page,id=row['id'],renderer=engine,accepted=row['index']in assigned,baseline=measure(target,current),experimental=measure(target,candidate)))
            print('B1 measured',engine,page,flush=True)
    equality={}
    for engine in ['pdfium','poppler']:
        texts=[];searches=[]
        for path in [BASE,experiment]:
            if engine=='poppler':
                texts.append(subprocess.check_output(['pdftotext','-layout',str(path),'-']))
            else:
                doc=pdfium.PdfDocument(path);pages=[];counts=[]
                for page in doc:
                    text=page.get_textpage();value=text.get_text_range();pages.append(value)
                    words=sorted(set(re.findall(r'[A-Za-z]{3,}',value)))
                    result={}
                    for word in words:
                        search=text.search(word);n=0
                        while search.get_next() is not None:n+=1
                        search.close();result[word]=n
                    counts.append(result);text.close();page.close()
                texts.append(pages);searches.append(counts);doc.close()
        equality[engine]=dict(extraction_equal=texts[0]==texts[1],search_equal=searches[0]==searches[1] if searches else None)
    serialization={}
    for name,path in [('default',BASE),('experimental',experiment)]:
        out=ROOT/f'financial-{name}-save-only.pdf'
        with pikepdf.open(path)as pdf:pdf.save(out,deterministic_id=True,object_stream_mode=pikepdf.ObjectStreamMode.generate)
        serialization[name]=dict(bytes=out.stat().st_size,sha256=sha(out))
    result=dict(schema='font04-checkpoint-b1-v1',population='P3 financial, 13 pages, every visible e',baseline_commit='c10e3dff93ca12ac410c0f6626a4ef74ce34e0c1',pdfs=dict(default=str(BASE),experimental=str(experiment)),scorecard=stats,program_accounting=dict(added=sum(added.values()),retired=sum(retired.values()),net=sum(added.values())-sum(retired.values()),method='multiset of compiled glyf programs, all required font slots, checked against all visible and invisible users',added_programs=dict(added),retired_programs=dict(retired)),default_matches_current_main=sha(BASE)==sha(ROOT/'financial-main.pdf'),source_metric_method='Native isolated emitted e programs, original MediaBox and authoritative raster-to-page transform, black normalized ink against an ownership-normalized source layer rendered by the same engine; complete PDF renders separately checked and retained for review.',source_error={engine:{arm:summary([r[arm]for r in records if r['renderer']==engine])for arm in ['baseline','experimental']}for engine in ['pdfium','poppler']},per_member=records,render_changes=page_renders,text_search=equality,serialization_control=serialization,runtime=dict(main=runtime(ROOT/'main.time'),default=runtime(ROOT/'default.time'),experimental=runtime(ROOT/'experimental-v2.time')),runtime_limit='Runs overlapped other discovery jobs; wall-time differences are not isolated performance evidence.',blinded_review=dict(status='prepared; independent judgments pending',material_defects=None),frontier=plan['frontier'],rejection_ledger=plan['rejection_ledger'],unique_rejections=plan['unique_pair_rejections'],plan_selected=plan['selected'])
    (ROOT/'checkpoint-B1-full.json').write_text(json.dumps(result,indent=2));compact=dict(result);compact.pop('per_member');compact.pop('rejection_ledger');compact['per_member_artifact']=dict(path=str(ROOT/'checkpoint-B1-full.json'),sha256=sha(ROOT/'checkpoint-B1-full.json'))
    Path('qualification/font04/checkpoint-B1.json').write_text(json.dumps(compact,indent=2));Path('qualification/font04/rejection-ledger.json').write_text(json.dumps(plan['rejection_ledger'],indent=2));Path('qualification/font04/reuse-fidelity-frontier.json').write_text(json.dumps(plan['frontier'],indent=2))
    print(json.dumps(stats,indent=2));print('accounting',result['program_accounting']['added'],result['program_accounting']['retired'])


if __name__=='__main__':main(Path(sys.argv[1]))
