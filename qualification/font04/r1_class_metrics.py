"""R1 native output scoring: render every candidate, including unchanged draws.
One draw per original-size page prevents adjacent ownership layers overwriting
each other. Bitmap cropping preserves the renderers' original full-page rounding.
"""
from pathlib import Path
import io,json,os,sys
import numpy as np
import pikepdf
from fontTools.ttLib import TTFont
from scipy.optimize import linear_sum_assignment
from qualification.font04.metrics import inspect,matrix,operands,render,measure,sha
from qualification.font04.planner import local_source
from qualification.font04.prime_metrics import analytic,direct,headline
ROOT=Path('qualification/font04/local')


def bind(snapshot,inv):
    # The snapshot exports the compositor's occurrence index. Its assembler
    # preserves that order (page_pdf occurrence emission); use the exact identity
    # rather than a centroid heuristic, which fails on asymmetric source crops.
    pages={pi:[d for d in inv['draws'] if d['page']==pi] for pi in range(13)}
    result={}
    for row in snapshot['rows']:
        draw=pages[row['page']][row['occurrence']]
        if draw['character']!=row['character']:raise ValueError(('occurrence label mismatch',row['index']))
        result[row['index']]=draw
    if len({(r['page'],r['occurrence']) for r in snapshot['rows']})!=len(snapshot['rows']):raise ValueError('duplicate source occurrence')
    if len(result)!=len(snapshot['rows']):raise ValueError('non-bijective occurrence binding')
    return result


def isolated_pages(path,snap,basebound,bound,only_candidate=False):
    art=Path(str(path)+'.font04');rows=snap['rows'];geometry=json.loads((ROOT/'financial-default.pdf.json').read_text())['pages']
    for name,inputpath,draws in [('default',ROOT/'financial-default.pdf',basebound),('candidate',path,bound),('source',ROOT/'financial-default.pdf',None)]:
        if only_candidate and name!='candidate':continue
        with pikepdf.open(inputpath) as original:
            pdf=pikepdf.Pdf.new()
            for r in rows:
                i=r['index'];pdf.pages.append(original.pages[r['page']]);page=pdf.pages[-1]
                if draws is not None:
                    d=draws[i];commands='BT 0 Tr 0 g '+d['font']+' 1 Tf '+' '.join(map(str,d['matrix']))+f" Tm <{d['cid']:04x}> Tj ET\n"
                elif r['source'] is not None:
                    ss=r['source'];cov=local_source(ss,r['paper']);pixels=np.round((1-cov)*255).astype('uint8');h,w=pixels.shape;g=geometry[r['page']];sx=g['width_pt']/g['raster_width'];sy=g['height_pt']/g['raster_height'];x,y=ss['bbox'][:2]
                    obj=pdf.make_stream(pixels.tobytes());obj.Type=pikepdf.Name.XObject;obj.Subtype=pikepdf.Name.Image;obj.Width=w;obj.Height=h;obj.ColorSpace=pikepdf.Name.DeviceGray;obj.BitsPerComponent=8
                    page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj))
                    commands=f'q {w*sx:.12f} 0 0 {h*sy:.12f} {(x-2)*sx:.12f} {g["height_pt"]-(y-2+h)*sy:.12f} cm /I Do Q\n'
                else:commands=''
                page.Contents=pdf.make_stream(commands.encode())
            pdf.save(art/f'class-isolated-{name}.pdf',deterministic_id=True)

def crop_render(path,doc,page,bounds,engine):
    import math,subprocess,tempfile
    from PIL import Image
    x,y,xx,yy=bounds
    if engine=='poppler':
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run(['pdftoppm','-f',str(page+1),'-l',str(page+1),'-singlefile','-r','300','-x',str(x),'-y',str(y),'-W',str(xx-x),'-H',str(yy-y),'-gray','-png',str(path),temp+'/crop'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            with Image.open(temp+'/crop.png') as im:return 1-np.asarray(im.convert('L'),float)/255
    if engine=='pdfium':
        p=doc[page];bitmap=p.render(scale=300/72)
        a=np.asarray(bitmap.to_pil().convert('L'),float)[y:yy,x:xx].copy()
        bitmap.close();p.close();return 1-a/255
    k=4 if engine=='analytic' else 1;scale=300*k/72;p=doc[page]
    width=math.ceil(p.get_width()*scale);height=math.ceil(p.get_height()*scale)
    # pypdfium rounds full-page dimensions before cropping. Keep those exact
    # dimensions and integer crop offsets; an atlas would change hinting phase.
    crop=tuple(max(0,v/scale-1e-9) for v in [x*k,height-yy*k,width-xx*k,y*k])
    bitmap=p.render(scale=scale,crop=crop,**({'grayscale':True} if k==4 else {}));a=np.asarray(bitmap.to_pil().convert('L'),float)
    if k==4:a=a.reshape(yy-y,k,xx-x,k).mean((1,3))
    bitmap.close();p.close();return 1-a/255


_ROW_CONTEXT=None
def _init_measure_worker():
    # PDFium callbacks hold seekable file descriptors. Reopen after fork so
    # processes cannot race on one inherited open-file description.
    global _ROW_CONTEXT
    art,cached,acc,docs,fonts,basebound,bound,path=_ROW_CONTEXT
    names=list(docs)
    for doc in docs.values():doc.close()
    import pypdfium2 as pdfium
    docs={name:pdfium.PdfDocument(art/f'class-isolated-{name}.pdf') for name in names}
    _ROW_CONTEXT=(art,cached,acc,docs,fonts,basebound,bound,path)

def _measure_row(r):
    art,cached,acc,docs,fonts,basebound,bound,path=_ROW_CONTEXT
    records=[];crops={}
    i=r['index']
    if r['source'] is None:return [],{}
    x,y,xx,yy=map(int,r['source']['bbox']);bounds=[x-4,y-4,xx+4,yy+4]
    for engine in ['pdfium','poppler','analytic']:
        arrays={name:crop_render(art/f'class-isolated-{name}.pdf',doc,i,bounds,engine) for name,doc in docs.items()}
        if cached is not None:arrays.update(source=cached[f'{i}-{engine}-source'],default=cached[f'{i}-{engine}-default'])
        for name,value in arrays.items():crops[f'{i}-{engine}-{name}']=value
        records.append(dict(member=i,character=r['character'],page=r['page'],metric=engine,accepted=i in acc,default=measure(arrays['source'],arrays['default']),candidate=measure(arrays['source'],arrays['candidate'])))
    a=cached[f'{i}-direct-default'] if cached is not None else direct(fonts['default'],basebound[i],bounds,r['page_height']);b=direct(fonts['candidate'],bound[i],bounds,r['page_height']);src=crops[f'{i}-analytic-source'];crops[f'{i}-direct-default']=a;crops[f'{i}-direct-candidate']=b
    records.append(dict(member=i,character=r['character'],page=r['page'],metric='direct',accepted=i in acc,default=measure(src,a),candidate=measure(src,b)))
    if i%25==0:print(path.name,i,flush=True)
    return records,crops


def main(path):
    art=Path(str(path)+'.font04');snap=json.loads((art/'source.json').read_text());rows=snap['rows'];plan=json.loads((art/'plan.json').read_text());acc={r['member'] for r in plan['assignments']};inv=inspect(path);baseinv=inspect(ROOT/'financial-default.pdf');basebound=bind(snap,baseinv);bound=bind(snap,inv)
    (art/'emitted-bindings.json').write_text(json.dumps(basebound))
    reference=os.environ.get('FONT04_CLASS_REFERENCE');cached=None;reuse=None
    if reference:
        ref=Path(str(reference)+'.font04');reuse=json.loads((ref/'class-metrics.json').read_text())
        assert json.loads((ref/'source.json').read_text())==snap, 'class-reference source mismatch'
        assert reuse['default_sha256']==sha(ROOT/'financial-default.pdf'), 'class-reference default mismatch'
        assert reuse['sha256']==sha(Path(reference)), 'class-reference PDF changed'
        cached=np.load(ref/'class-crops.npz')
    isolated_pages(path,snap,basebound,bound,only_candidate=bool(reference));records=[];crops={};fonts={}
    for name,p in [('default',ROOT/'financial-default.pdf'),('candidate',path)]:
        with pikepdf.open(p) as pdf:fonts[name]=TTFont(io.BytesIO(next(iter(pdf.pages[0].Resources.Font.values())).DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()))
    import pypdfium2 as pdfium
    docs={name:pdfium.PdfDocument(art/f'class-isolated-{name}.pdf') for name in (['candidate'] if reference else ['source','default','candidate'])}
    global _ROW_CONTEXT
    if cached is not None:
        cache_arrays={key:cached[key] for key in cached.files};cached.close();cached=cache_arrays
    _ROW_CONTEXT=(art,cached,acc,docs,fonts,basebound,bound,path)
    workers=max(1,min(8,int(os.environ.get('FONT04_METRIC_WORKERS','1'))))
    if workers>1:
        import multiprocessing
        with multiprocessing.get_context('fork').Pool(workers,initializer=_init_measure_worker) as pool:
            for rr,cc in pool.imap(_measure_row,rows,chunksize=4):records.extend(rr);crops.update(cc)
    else:
        for row in rows:
            rr,cc=_measure_row(row);records.extend(rr);crops.update(cc)
    for doc in docs.values():doc.close()
    if cached is not None and hasattr(cached,'close'):cached.close()
    byclass={}
    for char in sorted({r['character'] for r in rows}):
        rr=[r for r in records if r['character']==char];byclass[char]={engine:{subset:headline(rr,path.name,engine,subset) for subset in ['all','substituted']} for engine in ['analytic','direct','pdfium','poppler']}
        byclass[char]['population']=dict(total_visible=sum(r['character']==char for r in rows),with_owned_source=sum(r['character']==char and r['source'] is not None for r in rows),substituted=sum(rows[i]['character']==char for i in acc))
        byclass[char]['renderer_floors']={}
        for engine in ['pdfium','poppler','analytic']:
            values={}
            for ref in ['analytic','direct']:
                vv=[measure(crops[f"{r['member']}-{ref}-default"],crops[f"{r['member']}-{engine}-default"])['error'] for r in rr if r['metric']=='direct']
                values[ref]=dict(mean=float(np.mean(vv)),p95=float(np.quantile(vv,.95))) if vv else None
            byclass[char]['renderer_floors'][engine]=values
    floors={}
    for engine in ['pdfium','poppler','analytic']:
        vals=[measure(crops[f"{r['member']}-analytic-default"],crops[f"{r['member']}-{engine}-default"])['error'] for r in records if r['metric']=='direct'];floors[engine]=dict(mean=float(np.mean(vals)),p95=float(np.quantile(vals,.95)))
    result=dict(pdf=str(path),sha256=sha(path),default_sha256=sha(ROOT/'financial-default.pdf'),all_candidate_draws_measured=True,reference_reuse=dict(pdf=reference,source_snapshot_exact=True,default_sha256_exact=True) if reference else None,bytes=path.stat().st_size,substituted=len(acc),classes=byclass,renderer_vs_analytic_floors=floors,records=records)
    (art/'class-metrics.json').write_text(json.dumps(result,indent=2)+'\n');np.savez_compressed(art/'class-crops.npz',**crops)
    Path('qualification/font04/r1-native-'+path.stem+'-class-scorecard.json').write_text(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2)+'\n')

if __name__=='__main__':main(Path(sys.argv[1]))
