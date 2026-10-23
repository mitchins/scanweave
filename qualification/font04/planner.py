"""FONT-04 source-only discovery planner, called only by explicit CLI mode.

Geometry implementation copied from FONT-03 7ebc09e (geometry.py). Hard vetoes
are unchanged. Added effective-stroke, counter-band and baseline checks remain
orthogonal to the single swept noise-floor error criterion. No oracle IO here.
"""
from pathlib import Path
import collections
import json
import os
import sys
import time
import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from qualification.font04.geometry import geometry, geometry_rejections, register, warp, structural_distances

SWEEP = [0.5, 0.75, 1., 1.25, 1.5, 2., 3.]


def local_source(source, paper_rgb=(255,255,255)):
    h,w=source['height'],source['width']
    mask=np.array(source['mask'],bool).reshape(h,w)
    halo=np.array(source['halo'],float).reshape(h+4,w+4)
    owned=np.pad(mask,2)
    paper=float(np.quantile(halo[~owned],.8))
    ink=float(np.quantile(halo[owned],.15))
    if paper-ink<30: raise ValueError('insufficient_contrast')
    distance=ndimage.distance_transform_edt(~owned)
    foreign=(np.abs(halo-np.dot(paper_rgb,[.2126,.7152,.0722]))>60)&~owned
    fd=ndimage.distance_transform_edt(~foreign) if foreign.any() else np.full(halo.shape,100.)
    support=(distance<=1.5)&(distance<fd)
    return np.clip((paper-halo)/(paper-ink),0,1)*support


def source_frame(row):
    s=row['source']; evidence=local_source(s,row['paper'])
    # Source line geometry only; fall back explicitly to the owned impression.
    own_center=(s['bbox'][1]+s['bbox'][3])/2
    own_height=s['bbox'][3]-s['bbox'][1]
    line=[u['bbox'] for u in row.get('line_units',[]) if u['text'] in 'ace' and u['bbox'][3]-u['bbox'][1]>=4
          and (not row.get('geometric_line_filter',True) or abs((u['bbox'][1]+u['bbox'][3])/2-own_center)<=.65*max(own_height,u['bbox'][3]-u['bbox'][1]))]
    if not line: line=[s['bbox']]
    xh=float(np.median([b[3]-b[1] for b in line]));base=float(np.median([b[3] for b in line]))
    cx=(s['ocr_bbox'][0]+s['ocr_bbox'][2])/2
    scale=32/xh; yy,xx=np.mgrid[:64,:64]
    canvas=ndimage.map_coordinates(evidence,[base+(yy-48)/scale-s['bbox'][1]+1.5,cx+(xx-32)/scale-s['bbox'][0]+1.5],order=1,mode='constant',prefilter=False)
    return canvas,dict(xheight=xh,baseline=base,cx=cx,scale=scale)


def frame_bbox(frame, origin, size, parameters=(0., 0., 1.)):
    """Convert canvas centre indices to physical pixel edges, then fit."""
    x,y=origin;w,h=size;dx,dy,s=parameters
    left=32+s*(x-.5-32)+dx;top=48+s*(y-.5-48)+dy
    return [frame['cx']+(left-32)/frame['scale'],
            frame['baseline']+(top-48)/frame['scale'],
            frame['cx']+(left+s*w-32)/frame['scale'],
            frame['baseline']+(top+s*h-48)/frame['scale']]


def crop_request(key,character,image,**options):
    yy,xx=np.nonzero(image>.5)
    if not len(xx):raise ValueError('empty_coverage')
    x0,x1=int(xx.min()),int(xx.max()+1);y0,y1=int(yy.min()),int(yy.max()+1)
    crop=image[y0:y1,x0:x1]
    return dict(key=key,character=character,width=x1-x0,height=y1-y0,coverage=crop.ravel().tolist(),local=True,preserve_frame=True,**options),[x0,y0]


def prepare(snapshot,directory):
    if os.environ.get('FONT04_SCOPE','B1')=='B2':
        gate=json.loads(Path('qualification/font04/checkpoint-B1prime.json').read_text())
        if not all(gate['B2_conditions'].get(k) is True for k in ('a','b','c')):
            raise ValueError('B2 is not authorized by the completed B1-prime checkpoint')
        if len({r['character'] for r in snapshot['rows']})!=55:raise ValueError('B2 requires exactly 55 frequent classes')
    items=[];frames=[];fields=[];origins=[];errors=[]
    for row in snapshot['rows']:
        try:
            if row['source'] is None:raise ValueError('no_safe_owned_witness')
            field,frame=source_frame(row)
            item,origin=crop_request('font04-e-'+str(row['index']),row.get('character','e'),field)
            frames.append(frame);fields.append(field);origins.append(origin);items.append(item)
        except ValueError as error:
            frames.append(None);fields.append(np.zeros((64,64)));origins.append(None);errors.append(dict(index=row['index'],reason=str(error)))
    np.save(directory/'fields.npy',fields)
    (directory/'source.json').write_text(json.dumps(snapshot))
    (directory/'frames.json').write_text(json.dumps(dict(frames=frames,origins=origins,errors=errors)))
    return dict(items=items)


def mse(a,b):
    return float(np.square(a-b).sum()/max(1.,np.maximum(a,b).sum()))


def hard_checks(a,b):
    reasons=geometry_rejections(a,b)
    ga,gb=geometry(a),geometry(b)
    distances=structural_distances(a,b)
    values={}
    if ga is None or gb is None:return ['empty_ink'],dict(empty_ink=dict(value=1,limit=0))
    for key,limit in [('area',1.25),('width',1.18),('height',1.18),('elongation',1.5),('stroke',1.3)]:
        ratio=max(ga[key]/max(gb[key],1e-8),gb[key]/max(ga[key],1e-8))
        values[key]=dict(value=float(ratio),limit=limit)
    values['topology']=dict(value=list(gb['topology']),limit=list(ga['topology']))
    values['centroid']=dict(value=float(np.linalg.norm(np.array(ga['centroid'])-gb['centroid'])),limit=2.)
    values['orientation']=dict(value=float(abs(np.dot(ga['axis'],gb['axis']))),limit=float(np.cos(np.deg2rad(15))))
    if distances:
        for key,limit in [('stroke_log',float(np.log(1.3))),('counter_difference',.35),('cross_moment',.08)]:
            values[key]=dict(value=distances[key],limit=limit)
            if distances[key]>limit:reasons.append(key)
    # Multi-threshold topology catches grayscale counter closures/openings.
    for threshold in [.35,.65]:
        from qualification.font04.geometry import topology
        ta,tb=topology(a>threshold),topology(b>threshold)
        key='counter_band_'+str(threshold)
        values[key]=dict(value=list(tb),limit=list(ta))
        if ta!=tb:reasons.append(key)
    return sorted(set(reasons)),values


def choose(matrix,errors,scale,method,rows=None):
    if rows is not None and len({r.get('character','e') for r in rows})>1:
        groups=[]
        for char in sorted({r.get('character','e') for r in rows}):
            indices=[i for i,r in enumerate(rows) if r.get('character','e')==char]
            sub=choose(matrix[np.ix_(indices,indices)],errors[np.ix_(indices,indices)],scale,method,[rows[i] for i in indices])
            groups.extend(dict(canonical=indices[g['canonical']],members=[indices[i] for i in g['members']]) for g in sub)
        return groups
    valid=matrix & (errors<=scale)
    admissible_self=np.diag(valid).copy()
    valid[:,~admissible_self]=False
    np.fill_diagonal(valid,False)
    n=len(matrix);remaining=set(range(n));groups=[]
    remapped=set()
    while remaining:
        if not any(admissible_self[j] for j in remaining):break
        if method=='complete':
            seed=min(j for j in remaining if admissible_self[j]);members=[seed]
            for i in sorted(remaining-{seed}):
                if all(valid[i,j] and valid[j,i] for j in members):members.append(i)
            canonical=min((j for j in members if admissible_self[j]),key=lambda j:sum(errors[i,j] for i in members if i!=j))
        else:
            # Greedy set cover: candidate chosen for maximum uncovered support.
            # Star control uses aggregate pair distance to choose the next center.
            candidates=[]
            for j in sorted(remaining):
                if not admissible_self[j]:continue
                members=[i for i in sorted(remaining) if valid[i,j]]
                members=sorted(set(members+[j]))
                priority=(-len(members),float(sum(errors[i,j] for i in members if i!=j)),j)
                if method=='star':priority=(float(np.median(errors[j,[i for i in remaining if i!=j]])) if len(remaining)>1 else 0.,-len(members),j)
                if method=='cover' and rows is not None:
                    users={}
                    for i,row in enumerate(rows):users.setdefault(row['shape_key'],set()).add(i)
                    before=sum(u<=remapped for u in users.values())
                    retired=sum(u<=(remapped|set(members)) for u in users.values())-before
                    # Cost-aware set cover is the justified third alternative:
                    # retire whole old programs, rather than maximizing draws.
                    priority=(-(retired-1),-len(members),priority[1],j)
                candidates.append((priority,j,members))
            _,canonical,members=min(candidates)
        # A singleton remains on its old outline; two is sufficient for economy.
        if len(members)>=2:groups.append(dict(canonical=canonical,members=members))
        remaining-=set(members)
        if len(members)>=2:remapped.update(members)
    return groups


_FIT_CONTEXT=None

def _fit_pair(pair):
    i,j=pair;fields,candidate=_FIT_CONTEXT
    p,aligned=register(fields[i],candidate[j]);err=mse(fields[i],aligned)
    reasons,values=hard_checks(fields[i],aligned)
    return dict(member=i,canonical=j,error=err,reasons=reasons,checks=values,parameters=p.tolist())


def plan(data,directory):
    started=time.monotonic();rows=data['snapshot']['rows'];n=len(rows)
    fields=np.load(directory/'fields.npy');meta=json.loads((directory/'frames.json').read_text());frames=meta['frames'];origins=meta['origins']
    outlines=data['outlines']['records'];lookup={o['key']:o for o in outlines if 'gid' in o}
    candidate=np.zeros_like(fields);shape_indices={};successful=[o for o in outlines if 'gid'in o]
    for si,o in enumerate(successful):
        j=int(o['key'].rsplit('-',1)[1]);x,y=origins[j];h,w=o['height'],o['width']
        candidate[j,y:y+h,x:x+w]=np.array(o['coverage']).reshape(h,w);shape_indices[j]=si
    arm=os.environ.get('FONT04_ARM','P')
    if arm not in ('P0','P','PV'):raise ValueError('unknown FONT04_ARM')
    if arm=='P0':
        frozen=Path('qualification/font04/local/financial-experimental-v2.pdf.font04')
        old_snapshot=json.loads((frozen/'source.json').read_text())
        if data['snapshot']!=old_snapshot:raise ValueError('frozen B1 source changed')
        if data['outlines']!=json.loads((frozen/'outlines.json').read_text()):raise ValueError('frozen B1 outlines changed')
        result=json.loads((frozen/'plan.json').read_text())
        for a in result['assignments']:
            j=a['canonical'];o=lookup['font04-e-'+str(j)]
            a['bbox']=frame_bbox(frames[a['member']],origins[j],(o['width'],o['height']),a['parameters'])
        result['arm']='B1-prime-P0';result['membership']='frozen B1 accepted set and canonical mapping'
        (directory/'outlines.json').write_text(json.dumps(data['outlines']))
        (directory/'pair-ledger.json').write_bytes((frozen/'pair-ledger.json').read_bytes())
        (directory/'plan.json').write_text(json.dumps(result,indent=2))
        return result
    if arm=='PV' and os.environ.get('FONT04_REUSE_FITS')=='1':
        import hashlib
        ledger_path=Path(os.environ.get('FONT04_OWNERSHIP_LEDGER','qualification/font04/owned-component-ledger.json'))
        ownership=json.loads(ledger_path.read_text());control=Path(ownership['source_pdf']);reference=Path(str(control)+'.font04')
        if hashlib.sha256(control.read_bytes()).hexdigest()!=ownership['source_pdf_sha256']:raise ValueError('changed ownership control PDF')
        if data['snapshot']!=json.loads((reference/'source.json').read_text()):raise ValueError('cached fits source mismatch')
        if data['outlines']!=json.loads((reference/'outlines.json').read_text()):raise ValueError('cached fits outlines mismatch')
        result=json.loads((reference/'plan.json').read_text())
        if result['selected']['grouping']!='star' or result['selected']['error_scale']!=1.:raise ValueError('cached operating point mismatch')
        exceptions=set(ownership['exceptions']);groups=collections.defaultdict(list)
        for a in result['assignments']:groups[a['canonical']].append(a)
        accepted=[];removed=[]
        for j,members in groups.items():
            survivors=[a for a in members if a['member'] not in exceptions] if j not in exceptions else []
            if len(survivors)<2:survivors=[]
            kept={a['member'] for a in survivors};accepted.extend(survivors)
            removed.extend(a for a in members if a['member'] not in kept)
        for a in accepted:a['character']=rows[a['member']].get('character','e')
        for a in removed:
            i=a['member'];result['rejection_ledger'].append(dict(member=i,canonical=a['canonical'],reasons=['unexplained_owned_ink' if i in exceptions else 'ownership_group_exception'],checks=dict(unexplained_owned_ink=dict(value=[r for r in ownership['components'] if r['member']==i and r['fires']],limit=ownership['policy'])) if i in exceptions else dict(ownership_group=dict(value=dict(canonical=a['canonical'],canonical_veto=a['canonical'] in exceptions,remaining_members=sum(x['member'] not in exceptions for x in groups[a['canonical']])),limit=dict(canonical_veto=False,minimum_members=2))),parameters=a['parameters']))
        result.update(assignments=accepted,arm='PV',ownership_veto=ownership,runtime_seconds=time.monotonic()-started,fit_reuse=dict(control_pdf=str(control),sha256=ownership['source_pdf_sha256'],verification='Exact source snapshot and traced outline equality; identical post-group ownership veto; no refitting or acceptance change.'))
        (directory/'outlines.json').write_text(json.dumps(data['outlines']))
        (directory/'pair-ledger.json').write_bytes((reference/'pair-ledger.json').read_bytes())
        (directory/'plan.json').write_text(json.dumps(result,indent=2));return result
    errors=np.full((n,n),np.inf);veto=np.zeros((n,n),bool);pairs=[];parameters={}
    # Fits are independent. Optional process parallelism preserves job/result order
    # and is checked against the serial B1 ledger; no decision rule changes.
    global _FIT_CONTEXT
    _FIT_CONTEXT=(fields,candidate)
    jobs=[];label_indices={}
    for i,row in enumerate(rows):label_indices.setdefault(row.get('character','e'),[]).append(i)
    for i in range(n):
        if frames[i] is None:continue
        indices=label_indices[rows[i].get('character','e')]
        distances=np.array([mse(fields[i],candidate[j]) if j in shape_indices and j!=i else np.inf for j in indices])
        jobs.extend((i,indices[j]) for j in np.argsort(distances)[:min(24,len(indices)-1)] if np.isfinite(distances[j]))
    workers=max(1,min(16,int(os.environ.get('FONT04_FIT_WORKERS','1'))))
    executor=None
    if workers>1:
        import concurrent.futures,multiprocessing
        executor=concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('fork'))
        fitted=executor.map(_fit_pair,jobs,chunksize=32)
    else:fitted=map(_fit_pair,jobs)
    try:
        previous=None
        for pair in fitted:
            i,j=pair['member'],pair['canonical'];errors[i,j]=pair['error'];veto[i,j]=not pair['reasons'];parameters[i,j]=pair['parameters'];pairs.append(pair)
            if i!=previous and i%25==0:print(f'FONT04 fitted {i}/{n}',file=sys.stderr,flush=True)
            previous=i
    finally:
        if executor is not None:executor.shutdown()
    # Noise floor uses non-target source impressions, not current self outlines.
    # Nearest structurally compatible independent impressions; LOO per member.
    noise=[];noise_support=[]
    for i in range(n):
        peers=[]
        indices=label_indices[rows[i].get('character','e')]
        for local_j in np.argsort(errors[i,indices]):
            j=indices[int(local_j)]
            if not veto[i,j] or rows[i]['shape_key']==rows[j]['shape_key']:continue
            p,aligned=register(fields[i],fields[j]);reasons,_=hard_checks(fields[i],aligned)
            if not reasons:peers.append(mse(fields[i],aligned))
            if len(peers)>=5:break
        noise.append(float(np.quantile(peers,.85)) if len(peers)>=2 else None)
        noise_support.append(dict(member=i,witnesses=len(peers),required_k=2,status='fewer_than_k_witnesses' if len(peers)<2 else 'calibrated',calibration_failure=False))
    normalized=np.full_like(errors,np.inf)
    for i,level in enumerate(noise):
        if level is not None:normalized[i]=errors[i]/max(level,1e-6)
    self_checks=[]
    for i in shape_indices:
        p,aligned=register(fields[i],candidate[i]);reasons,values=hard_checks(fields[i],aligned)
        err=mse(fields[i],aligned);errors[i,i]=err;veto[i,i]=not reasons
        normalized[i,i]=err/max(noise[i],1e-6) if noise[i] is not None else np.inf
        parameters[(i,i)]=p.tolist()
        self_checks.append(dict(member=i,error=err,reasons=reasons,checks=values))
    frontier=[]
    original={r['shape_key'] for r in rows}
    choices=[]
    for method in ['star','complete','cover']:
        for scale in SWEEP:
            groups=choose(veto,normalized,scale,method,rows)
            remapped={i for g in groups for i in g['members']}
            retired=original-{rows[i]['shape_key'] for i in range(n) if i not in remapped}
            added=len(groups);retained=len(original)-len(retired)
            item=dict(grouping=method,error_scale=scale,remapped=len(remapped),added=added,retired_visible_candidates=len(retired),net_visible_candidates=added-len(retired),designs=retained+added,
                mean_source_error=float(np.mean([errors[i,g['canonical']] for g in groups for i in g['members'] if i!=g['canonical']])) if groups else None,
                material_defects=None,pristine_error=None)
            frontier.append(item);choices.append((item,groups))
    # Conservative discovery point 1.0: within the independently measured floor.
    eligible=[(v,g) for v,g in choices if v['error_scale']==1.]
    chosen,groups=next((v,g) for v,g in eligible if v['grouping']=='star')
    ownership=None
    if arm=='PV':
        ledger_path=Path(os.environ.get('FONT04_OWNERSHIP_LEDGER','qualification/font04/owned-component-ledger.json'))
        ownership=json.loads(ledger_path.read_text())
        reference=Path(str(ownership['source_pdf'])+'.font04')
        if json.loads((reference/'source.json').read_text())!=data['snapshot']:
            raise ValueError('ownership veto evidence has different source snapshot')
        prior=json.loads((reference/'plan.json').read_text())
        if prior['selected']!=chosen:raise ValueError('ownership evidence has different operating point')
        proposed={(i,g['canonical']) for g in groups for i in g['members']}
        if proposed!={(a['member'],a['canonical']) for a in prior['assignments']}:
            raise ValueError('ownership evidence has different candidate assignments')
        exceptions=set(ownership['exceptions'])
        groups=[dict(g,members=[i for i in g['members'] if i not in exceptions])
                for g in groups if g['canonical'] not in exceptions]
        groups=[g for g in groups if len(g['members'])>=2]
    assignments=[];accepted=set();canonical_for={}
    for g in groups:
        j=g['canonical'];o=lookup['font04-e-'+str(j)];x,y=origins[j]
        for i in g['members']:
            if rows[i].get('character','e')!=rows[j].get('character','e'):raise ValueError('cross-label canonical forbidden')
            # Even the canonical member must pass its actual traced self gates.
            if i==j:
                p,aligned=register(fields[i],candidate[j]);reasons,values=hard_checks(fields[i],aligned)
                if reasons or noise[i] is None or mse(fields[i],aligned)>noise[i]*chosen['error_scale']:raise ValueError('inconsistent canonical self-admission')
            else:p=np.array(parameters[(i,j)])
            frame=frames[i];dx,dy,s=p
            # warp() applies a forward uniform scale about (32,48), then translation.
            bb=frame_bbox(frame,(x,y),(o['width'],o['height']),p)
            assignments.append(dict(character=rows[i].get('character','e'),page=rows[i]['page'],occurrence=rows[i]['occurrence'],id=rows[i]['id'],member=i,canonical=j,shape=shape_indices[j],bbox=bb,parameters=list(map(float,p))))
            accepted.add(i);canonical_for[i]=j
    # Reject records include an attempted candidate even if no admissible match.
    rejection=[]
    for i in range(n):
        attempted=sorted([p for p in pairs if p['member']==i],key=lambda p:p['error'])
        if i in accepted:continue
        if not attempted:rejection.append(dict(member=i,reasons=['no_safe_owned_witness'],checks={}));continue
        best=min(attempted,key=lambda p:(len(p['reasons']),p['error']))
        best=dict(best);best['reasons']=list(best['reasons'])
        if noise[i] is None:
            best['reasons'].append('insufficient_noise_witnesses');best['checks']=dict(best['checks'],noise_witnesses=dict(value=noise_support[i]['witnesses'],limit=2))
        elif best['error']>noise[i]:
            best['reasons'].append('noise_floor');best['checks']=dict(best['checks'],noise_floor=dict(value=best['error'],limit=noise[i]))
        if ownership is not None and i in ownership['exceptions']:
            best['reasons'].append('unexplained_owned_ink');best['checks']=dict(best['checks'],unexplained_owned_ink=dict(value=[r for r in ownership['components'] if r['member']==i and r['fires']],limit=ownership['policy']))
        if not best['reasons']:best['reasons']=['grouping_exception']
        rejection.append(best)
    unique=collections.Counter(p['reasons'][0] for p in pairs if len(p['reasons'])==1)
    result=dict(schema='font04-b1-plan-v1',scope='all 55 frequent classes' if os.environ.get('FONT04_SCOPE')=='B2' else 'all visible e only',selected=chosen,assignments=assignments,
        rejection_ledger=rejection,noise_floor=noise,noise_support=noise_support,frontier=frontier,unique_pair_rejections=dict(unique),
        arm=arm,fit_workers=workers,ownership_veto=ownership,self_checks=self_checks,total_pair_attempts=len(pairs),shortlist=24,shortlist_exclusions=sum(v*(v-1) for v in collections.Counter(r.get('character','e') for r in rows).values())-len(pairs),cross_label_forbidden=n*(n-1)-sum(v*(v-1) for v in collections.Counter(r.get('character','e') for r in rows).values()),runtime_seconds=time.monotonic()-started,
        defects_status='pending blinded independent review',inference_inputs='source only; no pristine or face labels')
    (directory/'outlines.json').write_text(json.dumps(data['outlines']))
    (directory/'plan.json').write_text(json.dumps(result,indent=2));(directory/'pair-ledger.json').write_text(json.dumps(pairs))
    return result


if __name__=='__main__':
    stage,destination=sys.argv[1:];directory=Path(destination);directory.mkdir(parents=True,exist_ok=True)
    data=json.load(sys.stdin)
    result={'prepare':prepare,'plan':plan}[stage](data,directory)
    json.dump(result,sys.stdout,allow_nan=False)
