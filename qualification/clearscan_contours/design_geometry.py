#!/usr/bin/env python3
"""Design-space outline comparison for matched M1-G glyph placements.

Evaluator-only: reads the synthetic oracle, its licensed source TTFs, and
embedded ScanWeave PDFs. It does not render bitmaps or alter product artifacts.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, math, sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pikepdf
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COMP = ROOT / 'qualification/clearscan_competitive'
FIX = ROOT / 'qualification/experiments/m1g/fixture/dpi300'
OUT = HERE / 'design-geometry-300.json'

spec = importlib.util.spec_from_file_location('source_font_control', COMP/'source_font_control.py')
source_control = importlib.util.module_from_spec(spec); spec.loader.exec_module(source_control)
spec = importlib.util.spec_from_file_location('audit_module', HERE/'audit.py')
audit_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit_module)

STEP = 0.18  # maximum target-space sampling interval, in physical pixels

class SamplePen(BasePen):
    """Flatten TrueType line/quadratic/cubic paths after an affine transform."""
    def __init__(self, glyph_set, transform, step=STEP):
        super().__init__(glyph_set)
        self.transform = transform; self.step = step
        self.contours=[]; self.cur=[]; self.start=None

    def _pt(self, p): return np.asarray(self.transform(float(p[0]),float(p[1])),dtype=np.float64)
    def _append_line(self, p0, p1):
        dist=float(np.linalg.norm(p1-p0)); n=max(1,int(math.ceil(dist/self.step)))
        for i in range(1,n+1): self.cur.append(p0+(p1-p0)*(i/n))
    def _moveTo(self,p):
        if self.cur: self._finish()
        q=self._pt(p);self.start=q;self.cur=[q]
    def _lineTo(self,p):
        q=self._pt(p);self._append_line(self.cur[-1],q)
    def _curveToOne(self,p1,p2,p3):
        ps=[self._pt(p) for p in (self._getCurrentPoint(),p1,p2,p3)]
        length=sum(float(np.linalg.norm(ps[i+1]-ps[i])) for i in range(3))
        n=max(1,int(math.ceil(length/self.step)))
        p0,a,b,c=ps
        for j in range(1,n+1):
            t=j/n;u=1-t
            self.cur.append(u**3*p0+3*u*u*t*a+3*u*t*t*b+t**3*c)
    def _qCurveToOne(self,p1,p2):
        ps=[self._pt(p) for p in (self._getCurrentPoint(),p1,p2)]
        length=float(np.linalg.norm(ps[1]-ps[0])+np.linalg.norm(ps[2]-ps[1]))
        n=max(1,int(math.ceil(length/self.step)))
        p0,a,b=ps
        for j in range(1,n+1):
            t=j/n;u=1-t
            self.cur.append(u*u*p0+2*u*t*a+t*t*b)
    def _closePath(self):
        if self.cur and self.start is not None and np.linalg.norm(self.cur[-1]-self.start)>1e-9:
            self._append_line(self.cur[-1],self.start)
        self._finish()
    def _endPath(self): self._finish()
    def _finish(self):
        if len(self.cur)>1:self.contours.append(np.asarray(self.cur,dtype=np.float64))
        self.cur=[];self.start=None

def extract(font: TTFont, glyph_name: str, transform):
    pen=SamplePen(font.getGlyphSet(),transform)
    font.getGlyphSet()[glyph_name].draw(pen)
    if pen.cur: pen._finish()
    return pen.contours

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def signed_area(contours):
    total=0.0
    for p in contours:
        q=np.roll(p,-1,axis=0)
        total+=0.5*float(np.sum(p[:,0]*q[:,1]-q[:,0]*p[:,1]))
    return total

def nearest(A,B):
    # Exact nearest-neighbour distances in bounded 2D blocks. Keeping the
    # working set small avoids a scipy dependency and large all-pairs arrays.
    if not len(A) or not len(B): return np.full(len(A),np.inf)
    out=[]; b2=np.einsum('ij,ij->i',B,B)
    for i in range(0,len(A),256):
        a=A[i:i+256]
        d2=np.einsum('ij,ij->i',a,a)[:,None]+b2[None,:]-2.0*(a@B.T)
        np.maximum(d2,0.0,out=d2)
        out.extend(np.sqrt(np.min(d2,axis=1)))
    return np.asarray(out)

def flatten(contours):
    return np.concatenate(contours,axis=0) if contours else np.zeros((0,2),dtype=np.float64)

def scan_intervals(contours,y):
    xs=[]
    for p in contours:
        q=np.roll(p,-1,axis=0)
        for (x0,y0),(x1,y1) in zip(p,q):
            if (y0<=y<y1) or (y1<=y<y0):
                xs.append(float(x0+(y-y0)*(x1-x0)/(y1-y0)))
    xs.sort()
    return [(xs[i],xs[i+1]) for i in range(0,len(xs)-1,2) if xs[i+1]>xs[i]]

def stem_widths(source,embedded):
    """Compare stable near-vertical source intervals to actual same-y intervals."""
    if not source or not embedded:return {'samples':0,'missing':0,'errors_px':[]}
    src=flatten(source);ys=np.concatenate([c[:,1] for c in source]);lo=float(ys.min());hi=float(ys.max())
    errors=[];missing=0
    y=lo+0.11
    while y<hi:
        mid=scan_intervals(source,y)
        low=scan_intervals(source,y-0.25);high=scan_intervals(source,y+0.25)
        for l,r in mid:
            w=r-l
            if not 0.7<=w<=6.0:continue
            def nearest_center(rows,c): return min(rows,key=lambda z:abs((z[0]+z[1])/2-c),default=None)
            c=(l+r)/2;lm=nearest_center(low,c);hm=nearest_center(high,c)
            if lm is None or hm is None:continue
            if max(abs(l-lm[0]),abs(r-lm[1]),abs(l-hm[0]),abs(r-hm[1]))>=0.25:continue
            candidates=scan_intervals(embedded,y)
            if not candidates:
                missing+=1;continue
            match=min(candidates,key=lambda z:(0 if min(r,z[1])>max(l,z[0]) else 1,abs((z[0]+z[1])/2-c)))
            if abs((match[0]+match[1])/2-c)>1.0:
                missing+=1;continue
            errors.append({'y_px':round(y,3),'source_interval_px':[l,r],'source_width_px':w,
                           'embedded_interval_px':list(match),'embedded_width_px':match[1]-match[0],
                           'signed_width_error_px':match[1]-match[0]-w})
        y+=0.2
    return {'samples':len(errors),'missing':missing,'errors_px':errors}

def chamfer(A,B):
    da=nearest(A,B);db=nearest(B,A);all_d=np.concatenate([da,db])
    return {'mean':float((da.mean()+db.mean())/2), 'p95':float(np.percentile(all_d,95)),
            'source_to_sw_mean':float(da.mean()),'sw_to_source_mean':float(db.mean()),
            'source_to_sw_p95':float(np.percentile(da,95)), 'sw_to_source_p95':float(np.percentile(db,95)),
            'source_boundary_fraction_gt_0_5px':float(np.mean(da>0.5))}

def missing_run(contours_a, contours_b, threshold=0.5):
    """Longest consecutive source-boundary segment farther than threshold."""
    if not contours_a or not contours_b: return None
    B=flatten(contours_b);longest=0.0;runs=0
    for contour in contours_a:
        d=nearest(contour,B);mask=d>threshold
        if not mask.any(): continue
        # Sample spacing is <= STEP. Join wrap-around runs on closed contours.
        starts=np.flatnonzero(mask & ~np.roll(mask,1));ends=np.flatnonzero(mask & ~np.roll(mask,-1))
        if len(starts)==0: longest=max(longest,len(mask)*STEP);runs+=1;continue
        runs+=len(starts)
        for s in starts:
            n=0;i=int(s)
            while mask[i]:
                n+=1;i=(i+1)%len(mask)
                if i==s:break
            longest=max(longest,n*STEP)
    return {'threshold_px':threshold,'count_runs':runs,'longest_run_px':float(longest)}

def shifted_best(src,sw,step=0.5):
    # Diagnostic only: translation is varied on a fixed grid within ±1 px.
    base=chamfer(src,sw);best=(base['mean'],0.0,0.0)
    for dy in (-1.0,-0.5,0.0,0.5,1.0):
        for dx in (-1.0,-0.5,0.0,0.5,1.0):
            if dx==0 and dy==0:continue
            c=chamfer(src,sw+np.array([dx,dy]))
            if c['mean']<best[0]:best=(c['mean'],dx,dy)
    return {'mean_px':float(best[0]),'shift_px':[best[1],best[2]],'grid_px':step,'limit_px':1.0,
            'raw_mean_px':base['mean'],'gain_px':float(base['mean']-best[0])}

def source_positions(dpi):
    result=[]
    for pi in range(8):
        truth=json.loads((FIX/'oracle'/f'page{pi:02}.truth.json').read_text())
        fpath=truth['font']
        positions=source_control.positions_for_page(dpi,pi,fpath)
        records={r['id']:r for r in truth['records']}
        for sid,rec in records.items():
            if not rec['text'].strip() or sid not in positions:continue
            ch,x,baseline,size,font_path=positions[sid]
            if ch!=rec['text']:
                raise ValueError(f'nominal source text mismatch at {sid}: {ch!r} != {rec["text"]!r}')
            result.append({'page':pi,'symbol':sid,'text':ch,'font_path':font_path,
                           'x_px':float(x),'baseline_px':float(baseline),'font_size_px':float(size)})
    return result

def font_pageheight_px(page,dpi):
    return float(page.MediaBox[3]-page.MediaBox[1])*dpi/72.0

def load_pdf_font(pdf, objgen, cache):
    key=tuple(objgen)
    if key in cache:return cache[key]
    obj=next(o for o in pdf.objects if getattr(o,'objgen',None)==key)
    desc=obj.get('/DescendantFonts',[obj])[0];fd=desc.get('/FontDescriptor',{})
    stream=fd.get('/FontFile2') or fd.get('/FontFile')
    if stream is None: raise ValueError(f'font {key} has no TrueType program')
    raw=stream.read_bytes();ft=TTFont(io.BytesIO(raw),recalcBBoxes=False,recalcTimestamp=False)
    cache[key]={'font':ft,'sha256':hashlib.sha256(raw).hexdigest(),'upem':ft['head'].unitsPerEm,
                'glyph_order':ft.getGlyphOrder()}
    return cache[key]

def design_outline(font_path,ch,size,x,baseline):
    ft=source_fonts.setdefault(font_path,TTFont(font_path,recalcBBoxes=False,recalcTimestamp=False))
    cmap=ft.getBestCmap();name=cmap.get(ord(ch))
    if name is None: raise ValueError(f'{font_path} has no cmap glyph for {ch!r}')
    scale=size/ft['head'].unitsPerEm
    contours=extract(ft,name,lambda gx,gy:(x+gx*scale,baseline-gy*scale))
    return contours,ft,name

source_fonts={}

def evaluate_arm(dpi,arm,pdf_path,positions,representative=False):
    report_path=HERE/str(dpi)/f'{arm}.json'
    if arm=='source-font-control': report_path=COMP/str(dpi)/'clearscan.json'
    report=json.loads(report_path.read_text())
    audit=audit_module.audit(dpi,arm,pdf_path,report_path)
    placements=audit['placements'];doc=pikepdf.open(pdf_path);font_cache={}
    truth_by_page=[{r['id']:r for r in json.loads((FIX/'oracle'/f'page{i:02}.truth.json').read_text())['records']} for i in range(8)]
    pos_map={(r['page'],r['symbol']):r for r in positions}
    vectors=[];missing=[];sample_counts=defaultdict(int)
    for row in placements:
        pi=row['page'];sid=row.get('symbol')
        if sid is None or (pi,sid) not in pos_map or sid not in truth_by_page[pi]:continue
        oracle=pos_map[(pi,sid)];truth=truth_by_page[pi][sid];ch=truth['text']
        if representative:
            allowed={'e','6','8','g','a','!',',','か','な','カ','ナ'}
            if ch not in allowed or (ch=='a' and pi not in (6,7)) or sample_counts[ch]>=5:continue
            sample_counts[ch]+=1
        try: pf=load_pdf_font(doc,row['font'],font_cache)
        except Exception as e:
            missing.append({'page':pi,'symbol':sid,'reason':str(e)});continue
        gid=int(row['gid']);order=pf['glyph_order']
        if gid<0 or gid>=len(order):
            missing.append({'page':pi,'symbol':sid,'reason':f'GID {gid} outside glyph order'});continue
        a,b,c,d,e,f=map(float,row['matrix']);upem=pf['upem'];hpx=font_pageheight_px(doc.pages[pi],dpi)
        def pdf_transform(gx,gy):
            px=(a*gx/upem+c*gy/upem+e)*dpi/72.0
            py=(hpx-(b*gx/upem+d*gy/upem+f)*dpi/72.0)
            return px,py
        source_contours,source_ft,source_name=design_outline(oracle['font_path'],ch,oracle['font_size_px'],oracle['x_px'],oracle['baseline_px'])
        # The source-font control keeps the pre-existing OCR CID/ToUnicode
        # map. An OCR substitution can therefore select a different original
        # source-font GID at one occurrence; it is not a valid geometry
        # control for the pristine character. Record and exclude only that
        # control mismatch. Product arms are always scored as emitted.
        if arm=='source-font-control' and order[gid] != source_name:
            missing.append({'page':pi,'symbol':sid,'reason':'source-control CID maps to a different source glyph','expected_glyph':source_name,'actual_glyph':order[gid]})
            continue
        sw_contours=extract(pf['font'],order[gid],pdf_transform)
        src=flatten(source_contours);sw=flatten(sw_contours)
        if not len(src) or not len(sw):
            missing.append({'page':pi,'symbol':sid,'reason':'empty source or embedded outline'});continue
        dist=chamfer(src,sw);delta=shifted_best(src,sw)
        sa=signed_area(source_contours);wa=signed_area(sw_contours)
        area_bias=(wa-sa)/abs(sa) if abs(sa)>1e-9 else None
        miss=missing_run(source_contours,sw_contours)
        vectors.append({'page':pi,'symbol':sid,'text':ch,'family':'kana' if ord(ch)>127 else ('italic' if pi in (6,7) else 'serif'),
            'font_path':oracle['font_path'],'source_glyph_name':source_name,'source_upem':source_ft['head'].unitsPerEm,
            'embedded_font_sha256':pf['sha256'],'embedded_gid':gid,'embedded_glyph_name':order[gid],
            'tm':[a,b,c,d,e,f],'source_nominal':[oracle['x_px'],oracle['baseline_px'],oracle['font_size_px']],
            'source_samples':len(src),'embedded_samples':len(sw),'signed_area_source_px2':sa,'signed_area_embedded_px2':wa,
            'signed_area_bias':area_bias,'symmetric_chamfer':dist,'translation_only':delta,'missing_boundary_run':miss})
        vectors[-1]['stem_widths']=stem_widths(source_contours,sw_contours)
    groups=defaultdict(list)
    for r in vectors:groups[r['text']].append(r)
    def stats(rs):
        stem=[e['signed_width_error_px'] for r in rs for e in r.get('stem_widths',{}).get('errors_px',[])]
        return {'n':len(rs),'mean_chamfer_px':float(np.mean([r['symmetric_chamfer']['mean'] for r in rs])),
            'median_chamfer_px':float(np.median([r['symmetric_chamfer']['mean'] for r in rs])),
            'p95_boundary_px':float(np.mean([r['symmetric_chamfer']['p95'] for r in rs])),
            'mean_abs_area_bias':float(np.mean([abs(r['signed_area_bias']) for r in rs if r['signed_area_bias'] is not None])),
            'mean_translation_gain_px':float(np.mean([r['translation_only']['gain_px'] for r in rs])),
            'stem_width_sample_count':len(stem),'stem_width_missing_count':sum(r.get('stem_widths',{}).get('missing',0) for r in rs),
            'stem_width_mean_signed_error_px':float(np.mean(stem)) if stem else None,
            'stem_width_mean_abs_error_px':float(np.mean(np.abs(stem))) if stem else None}
    return {'arm':arm,'pdf':str(pdf_path.relative_to(ROOT)),'pdf_sha256':sha(pdf_path),'occurrence_count':len(vectors),
            'missing':missing,'overall':stats(vectors),'by_char':{k:stats(v) for k,v in sorted(groups.items())},'occurrences':vectors}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arms',nargs='*',default=['source-font-control','previous','fit','fair','strong','edgefit','blur']);ap.add_argument('--dpi',type=int,choices=(300,600),default=300);ap.add_argument('--representative',action='store_true',help='bound output to up to five selected glyphs per diagnostic character');args=ap.parse_args()
    dpi=args.dpi;positions=source_positions(dpi)
    key_sets=[]
    for arm in args.arms:
        audit_path=HERE/str(dpi)/arm/'audit.json'
        if audit_path.exists():key_sets.append({(r['page'],r['symbol']) for r in json.loads(audit_path.read_text())['placements']})
    if key_sets:
        common=set.intersection(*key_sets);positions=[r for r in positions if (r['page'],r['symbol']) in common]
    arms=[]
    for arm in args.arms:
        path=(COMP/'300/source-font-control/oracle-source-font.pdf' if arm=='source-font-control' else HERE/str(dpi)/f'{arm}.pdf')
        if not path.exists():continue
        arms.append(evaluate_arm(dpi,arm,path,positions,args.representative))
    expected_count=515
    summary={a['arm']:{'occurrences':a['occurrence_count'],'missing':len(a['missing']),'overall':a['overall'],'by_char':a['by_char']} for a in arms}
    result={'method':{'dpi':dpi,'accepted_population':expected_count,'sampling_step_px':STEP,'distance':'symmetric Chamfer: mean of both directed means; p95 of concatenated boundary distances','translation_diagnostic':'diagnostic grid dx,dy in {-1,-0.5,0,0.5,1} px; no scale/rotation/box fit','area':'signed shoelace area in physical pixel coordinates; relative signed-area bias; no bitmap threshold','source_placement':'exact generator nominal positions from source_font_control.positions_for_page (Pillow font metrics only for generator-compatible baseline/size), source TTF outlines from oracle font path','embedded_placement':'actual PDF CID→GID and Tm from audit.py placements; actual embedded TTFont glyph outlines; actual MediaBox','limitations':'TTFont design outlines and PDF GID/Tm mapping are exact vector geometry, but flattening and nearest-point metrics are sampled approximations; raster hinting is intentionally excluded. Adobe Type 3 geometry is not included.'},
        'tools':{'python':sys.version,'numpy':np.__version__,'pikepdf':pikepdf.__version__},
        'source_fonts':{p:{'sha256':sha(Path(p)),'upem':TTFont(p,recalcBBoxes=False,recalcTimestamp=False)['head'].unitsPerEm} for p in sorted(set(r['font_path'] for r in positions))},
        'arms':summary,'details':arms}
    output_path=HERE/f'design-geometry-{dpi}{"-representative" if args.representative else ""}.json'
    output_path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(summary,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
