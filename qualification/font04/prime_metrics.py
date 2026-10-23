"""B1-prime independent per-member coverage and renderer-floor scorecards.

Analytic definition reused from review_b1/rescore.py (4x PDFium box average).
Direct coverage independently flattens embedded TrueType contours and integrates
nonzero winding coverage at 16x, without a PDF text renderer.
"""
from pathlib import Path
import io,json,sys
import numpy as np
import pikepdf
import pypdfium2 as pdfium
from PIL import Image,ImageDraw
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from qualification.font04.metrics import inspect,render,measure,sha,matrix
from qualification.font04.b1_audit import bindings
from qualification.font04.native_financial import emitted_layer

ROOT=Path('qualification/font04/local')

class Flatten(BasePen):
    def __init__(self,glyphset):super().__init__(glyphset);self.contours=[];self.points=[]
    def _moveTo(self,p):self.points=[p]
    def _lineTo(self,p):self.points.append(p)
    def _qCurveToOne(self,p1,p2):
        p0=np.array(self._getCurrentPoint());p1=np.array(p1);p2=np.array(p2)
        for t in np.linspace(0,1,65)[1:]:self.points.append(tuple((1-t)**2*p0+2*(1-t)*t*p1+t*t*p2))
    def _curveToOne(self,p1,p2,p3):
        p0=np.array(self._getCurrentPoint());p1=np.array(p1);p2=np.array(p2);p3=np.array(p3)
        for t in np.linspace(0,1,65)[1:]:self.points.append(tuple((1-t)**3*p0+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*p3))
    def _closePath(self):self.contours.append(self.points);self.points=[]
    def _endPath(self):self._closePath()

def analytic(path,page):
    # Exact independent-review definition, including grayscale render mode.
    d=pdfium.PdfDocument(str(path));p=d[page];b=p.render(scale=1200/72,grayscale=True)
    a=np.asarray(b.to_pil().convert('L'),dtype=np.float32);h,w=a.shape
    result=a[:h//4*4,:w//4*4].reshape(h//4,4,w//4,4).mean((1,3))
    b.close();p.close();d.close();return result

def direct(font,draw,bounds,page_height,k=16):
    x,y,xx,yy=bounds;h,w=yy-y,xx-x
    pen=Flatten(font.getGlyphSet());font.getGlyphSet()[font.getGlyphOrder()[draw['gid']]].draw(pen)
    accum=np.zeros((h*k,w*k),np.int16);upem=font['head'].unitsPerEm;m=matrix(draw['matrix'])
    for contour in pen.contours:
        if len(contour)<3:continue
        q=np.array(contour);pt=(m@np.column_stack([q/upem,np.ones(len(q))]).T).T
        xy=np.column_stack([pt[:,0]*300/72-x,(page_height-pt[:,1])*300/72-y])
        area=np.sum(xy[:,0]*np.roll(xy[:,1],-1)-np.roll(xy[:,0],-1)*xy[:,1])
        im=Image.new('1',(w*k,h*k));ImageDraw.Draw(im).polygon([tuple(p) for p in (xy*k-.5)],fill=1)
        accum+=np.asarray(im,dtype=np.int16)*(1 if area>0 else -1)
    return (accum!=0).reshape(h,k,w,k).mean((1,3))

def headline(records,arm,metric,subset):
    values=[r for r in records if r['metric']==metric and (subset=='all' or r['accepted'])]
    return dict(default_mean=float(np.mean([r['default']['error'] for r in values])) if values else None,default_p95=float(np.quantile([r['default']['error'] for r in values],.95)) if values else None,n=len(values),mean=float(np.mean([r['candidate']['error'] for r in values])) if values else None,
                p95=float(np.quantile([r['candidate']['error'] for r in values],.95)) if values else None,
                worst_10_regressions=[dict(member=r['member'],delta=r['candidate']['error']-r['default']['error'],error=r['candidate']['error']) for r in sorted(values,key=lambda r:r['candidate']['error']-r['default']['error'],reverse=True)[:10]])

def main(path):
    artifact=Path(str(path)+'.font04');snap=json.loads((artifact/'source.json').read_text());plan=json.loads((artifact/'plan.json').read_text());acc={a['member'] for a in plan['assignments']}
    inv=inspect(path);bound=bindings(snap,inv);baseinv=inspect(ROOT/'financial-default.pdf');basebound=bindings(snap,baseinv)
    (artifact/'emitted-bindings.json').write_text(json.dumps(basebound))
    isolated=artifact/'isolated-e.pdf';emitted_layer(snap,inv,bound,path,isolated)
    records=[];crops={};fonts={}
    for name,p in [('default',ROOT/'financial-default.pdf'),('candidate',path)]:
        with pikepdf.open(p) as pdf:
            fonts[name]=TTFont(io.BytesIO(pdf.pages[0].Resources.Font.F1.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()))
    for page in range(13):
        rows=[r for r in snap['rows'] if r['page']==page and r['source'] is not None]
        engines={}
        for metric in ['pdfium','poppler','analytic']:
            get=analytic if metric=='analytic' else lambda p,i:render(p,i,300,metric)
            engines[metric]={name:1-get(p,page).astype(float)/255 for name,p in [('source',ROOT/'financial-source-owned.pdf'),('default',ROOT/'financial-default-isolated-e.pdf'),('candidate',isolated)]}
            for row in rows:
                i=row['index'];x,y,xx,yy=map(int,row['source']['bbox']);bounds=[x-4,y-4,xx+4,yy+4];x,y,xx,yy=bounds
                a={name:img[y:yy,x:xx] for name,img in engines[metric].items()}
                crops[f'{i}-{metric}-source']=a['source'];crops[f'{i}-{metric}-default']=a['default'];crops[f'{i}-{metric}-candidate']=a['candidate']
                records.append(dict(member=i,page=page,metric=metric,accepted=i in acc,default=measure(a['source'],a['default']),candidate=measure(a['source'],a['candidate'])))
        for row in rows:
            i=row['index'];x,y,xx,yy=map(int,row['source']['bbox']);bounds=[x-4,y-4,xx+4,yy+4]
            a=direct(fonts['default'],basebound[i],bounds,row['page_height']);b=direct(fonts['candidate'],bound[i],bounds,row['page_height'])
            src=crops[f'{i}-analytic-source']
            crops[f'{i}-direct-default']=a;crops[f'{i}-direct-candidate']=b
            records.append(dict(member=i,page=page,metric='direct',accepted=i in acc,default=measure(src,a),candidate=measure(src,b)))
        print(path.name,page,flush=True)
    floors={}
    for engine in ['pdfium','poppler','analytic']:
        vals=[measure(crops[f"{r['member']}-direct-default"],crops[f"{r['member']}-{engine}-default"])['error'] for r in records if r['metric']=='direct']
        analytic_vals=[measure(crops[f"{r['member']}-analytic-default"],crops[f"{r['member']}-{engine}-default"])['error'] for r in records if r['metric']=='direct']
        floors[engine]=dict(direct_reference=dict(mean=float(np.mean(vals)),p95=float(np.quantile(vals,.95))),analytic_reference=dict(mean=float(np.mean(analytic_vals)),p95=float(np.quantile(analytic_vals,.95))),population='291 identical default outlines at their real emitted placements')
    result=dict(pdf=str(path),sha256=sha(path),bytes=path.stat().st_size,substituted=len(acc),review_status='pending independent blinded review',metrics={metric:{subset:headline(records,path.name,metric,subset) for subset in ['all','substituted']} for metric in ['pdfium','poppler','analytic','direct']},renderer_floors=floors,records=records)
    (artifact/'prime-metrics.json').write_text(json.dumps(result,indent=2)+'\n');np.savez_compressed(artifact/'prime-crops.npz',**crops)
    compact={k:v for k,v in result.items() if k!='records'}
    Path(f'qualification/font04/{path.stem}-scorecard.json').write_text(json.dumps(compact,indent=2)+'\n')
    print(json.dumps(compact,indent=2))

if __name__=='__main__':main(Path(sys.argv[1]))
