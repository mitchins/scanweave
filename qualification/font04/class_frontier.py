"""Class-level fixed-coordinate direct-outline frontier for bounded P controls.

The chosen PV complete PDF is scored independently. This sweep isolates P (the
original hard vetoes) and does not extrapolate the ownership veto to unrendered
proposals. All pair direct coverages are measured at the actual fitted bbox.
"""
from pathlib import Path
import json,sys
import numpy as np
from fontTools.ttLib import TTFont
from qualification.font04.planner import choose,frame_bbox
from qualification.font04.geometry import register
from qualification.font04.causal import glyph_matrix
from qualification.font04.metrics import operands,measure,sha
from qualification.font04.prime_metrics import direct


def main(path):
    art=Path(str(path)+'.font04');snap=json.loads((art/'source.json').read_text());rows=snap['rows'];plan=json.loads((art/'plan.json').read_text());pairs=json.loads((art/'pair-ledger.json').read_text());meta=json.loads((art/'frames.json').read_text());outlines=json.loads((art/'outlines.json').read_text())['records'];lookup={int(o['key'].rsplit('-',1)[1]):o for o in outlines if 'gid' in o};font=TTFont(art/'canonical.ttf');fields=np.load(art/'fields.npy');metrics=json.loads((art/'class-metrics.json').read_text());current={r['member']:r['default']['error'] for r in metrics['records'] if r['metric']=='direct'};geometry=json.loads(Path('qualification/font04/local/financial-default.pdf.json').read_text())['pages'];n=len(rows)
    allowed=np.zeros((n,n),bool);ratios=np.full((n,n),np.inf);fidelity={};parameters={}
    for p in pairs:
        i,j=p['member'],p['canonical'];allowed[i,j]=not p['reasons'];parameters[i,j]=p['parameters'];level=plan['noise_floor'][i]
        if level is not None:ratios[i,j]=p['error']/max(level,1e-6)
    for c in plan['self_checks']:
        i=c['member'];allowed[i,i]=not c['reasons'];level=plan['noise_floor'][i]
        if level is not None:ratios[i,i]=c['error']/max(level,1e-6)
        o=lookup[i];x,y=meta['origins'][i];canvas=np.zeros((64,64));canvas[y:y+o['height'],x:x+o['width']]=np.array(o['coverage']).reshape(o['height'],o['width']);parameters[i,i]=register(fields[i],canvas)[0]
    with np.load(art/'class-crops.npz') as crops:
        for count,((i,j),p) in enumerate(parameters.items()):
            if not allowed[i,j] or not np.isfinite(ratios[i,j]) or ratios[i,j]>3:continue
            r=rows[i];o=lookup[j];bbox=frame_bbox(meta['frames'][i],meta['origins'][j],(o['width'],o['height']),p);g=geometry[r['page']];rr=dict(r,pixel_x_pt=g['width_pt']/g['raster_width'],pixel_y_pt=g['height_pt']/g['raster_height']);m=glyph_matrix(rr,o,bbox);x,y,xx,yy=map(int,r['source']['bbox']);draw=dict(gid=o['gid'],matrix=operands(m));candidate=direct(font,draw,[x-4,y-4,xx+4,yy+4],r['page_height']);fidelity[i,j]=measure(crops[f'{i}-analytic-source'],candidate)['error']
            if count%250==0:print('frontier pairs',count,len(parameters),flush=True)
    (art/'frontier-pair-coverage.json').write_text(json.dumps([dict(member=i,canonical=j,error=e) for (i,j),e in fidelity.items()]))
    points=[]
    for point in plan['frontier']:
        groups=choose(allowed,ratios,point['error_scale'],point['grouping'],rows);assigned={i:g['canonical'] for g in groups for i in g['members']};classes={}
        for char in sorted({r['character'] for r in rows}):
            indices=[i for i,r in enumerate(rows) if r['character']==char and i in current];vals=[(i,fidelity[i,assigned[i]] if i in assigned else current[i]) for i in indices];old={rows[i]['shape_key'] for i in indices};retained={rows[i]['shape_key'] for i in indices if i not in assigned};added=len({assigned[i] for i in indices if i in assigned})
            classes[char]=dict(n=len(vals),substituted=sum(i in assigned for i in indices),mean=float(np.mean([e for i,e in vals])) if vals else None,p95=float(np.quantile([e for i,e in vals],.95)) if vals else None,added=added,retired_visible_candidates=len(old-retained),net_retired_visible_candidates=len(old-retained)-added,worst_10_regressions=[dict(member=i,error=e,delta=e-current[i]) for i,e in sorted(vals,key=lambda v:v[1]-current[v[0]],reverse=True)[:10]])
        points.append(dict(grouping=point['grouping'],error_scale=point['error_scale'],classes=classes));print('frontier point',point['grouping'],point['error_scale'],flush=True)
    result=dict(reference='direct 16x winding coverage at fitted physical coordinates against isolated analytic source',scope='P controls; ownership-aware PV selected complete output is measured separately',input_pdf=str(path),input_sha256=sha(path),points=points)
    Path('qualification/font04/b2-frontier.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main(Path(sys.argv[1]))
