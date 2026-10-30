"""FONT-04 S1c offline analysis. Run from repository root with qualification/.venv/bin/python.

Uses the S1b local pair ledger and frozen exports. Oracle data are used only to
calibrate on train and score/purity; inference sees OCR geometry and masks.
"""
import json, math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from s1b_features import features, differences, CONFUSABLE, ROUND
from s1b_veto import BASE, OUT, FONT, read, lines, make_join

STYLE=('slant','weight'); KS=(2,3,4,6); MODES=('word','line')
pairs=read(BASE/'S1b/pairs.json'); baseline=read(OUT/'s1b-frontier.json'); glyph_noise=read(OUT/'s1b-noise.json')['scales']

def inputs(name):
    if name in ('train','validation','test'):
        return [(BASE/f'S1/font01/{name}-{i}-cover-2.0/source.json',d) for i,d in enumerate((200,300,600))]
    if name=='P2': return [(BASE/f'S1/instrumented-{i}/source.json',(200,300,600)[i//3]) for i in range(9)]
    return [(BASE/'R2a/export/financial-observations/source.json',300)]

def line_groups(words):
    # Greedy, deterministic span clustering: vertical intersection at least half
    # the smaller span height, with closest baseline resolving multiple matches.
    groups=[]
    for sid, rr in sorted(words.items(), key=lambda x:(x[1][0]['page'],min(r['bbox'][1] for r in x[1]),x[0])):
        box=[min(r['bbox'][1] for r in rr),max(r['bbox'][3] for r in rr)]
        candidates=[]
        for j,g in enumerate(groups):
            if g['page'] != rr[0]['page']: continue
            overlap=max(0,min(box[1],g['bottom'])-max(box[0],g['top']))
            if overlap >= .5*min(box[1]-box[0],g['bottom']-g['top']): candidates.append((abs(box[1]-g['bottom']),j))
        if candidates:
            g=groups[min(candidates)[1]]; g['ids'].append(sid)
            g['top']=float(np.median([min(r['bbox'][1] for r in words[s]) for s in g['ids']]))
            g['bottom']=float(np.median([max(r['bbox'][3] for r in words[s]) for s in g['ids']]))
        else: groups.append(dict(ids=[sid],top=box[0],bottom=box[1],page=rr[0]['page']))
    return [g['ids'] for g in groups]

pages={}; train_values=defaultdict(list)
for name in pairs:
    pages[name]=[]
    for page,(path,dpi) in enumerate(inputs(name)):
        rows=read(path)['rows']
        if name=='financial':
            for r in rows: r['id']=f"{r['page']}:{r['id']}"
        fs={r['id']:features(r) for r in rows}; words=defaultdict(list)
        for r in rows:
            words[(r['page'],r['span_id'])].append(r)
            if name=='train' and len(r['character'])==1 and fs[r['id']]:
                for f in STYLE: train_values[(dpi,r['character'],f)].append(fs[r['id']][f])
        if name in ('train','validation','test'):
            obs=lines(FONT/name/'observations.jsonl'); labels={x['id']:x for x in lines(FONT/name/'oracle/labels.jsonl')}
            join,_=make_join(rows,[o for o in obs if o['page']==page])
        elif name=='P2':
            labels={x['id']:x for x in lines(BASE/'P2/p2/oracle/labels.jsonl')}
            rec=read(OUT/'s1a-join.json')['sheets'][page]['records']; join={r['source_id']:r['candidates'][0]['id'] for r in rec if r['status']=='single_best'}
        else: labels={}; join={}
        pages[name].append(dict(rows=rows,fs=fs,words=words,dpi=dpi,faces={r['id']:labels[join[r['id']]]['face'] for r in rows if r['id'] in join and join[r['id']] in labels}))
# S1b's financial id-only dictionary collapses page-local IDs. Repair its
# member/canonical source lookup using the same frozen observation indices.
financial_obs=read(BASE/'R2a/export/financial-observations/observations.json')
financial_rows={r['id']:r for r in pages['financial'][0]['rows']}
for r in pairs['financial']:
    a,b=(financial_obs[r[x]] for x in ('member','canonical'))
    r['member_id']=f"{a['page']}:{a['id']}"; r['canonical_id']=f"{b['page']}:{b['id']}"
    aa=financial_rows[r['member_id']]; bb=financial_rows[r['canonical_id']]
    r['label']=aa['character']; r['delta']=differences(pages['financial'][0]['fs'][aa['id']],pages['financial'][0]['fs'][bb['id']],aa['character'])
normal={k:float(np.median(v)) for k,v in train_values.items()}
# Unseen labels abstain from pooling; no held-out or financial statistics used.
for name, pp in pages.items():
    for p in pp:
        p['runs']={}; p['lookup']={}
        for mode in MODES:
            groups=[[sid] for sid in sorted(p['words'])] if mode=='word' else line_groups(p['words'])
            runs=[]; lookup={}
            for ids in groups:
                rr=[r for sid in ids for r in p['words'][sid]]; vectors=[]
                for r in rr:
                    f=p['fs'][r['id']]; char=r['character']; dpi=p['dpi']
                    if f and all((dpi,char,x) in normal for x in STYLE): vectors.append([f[x]-normal[(dpi,char,x)] for x in STYLE])
                facecounts=Counter(p['faces'].get(r['id']) for r in rr); facecounts.pop(None,None)
                # Purity only describes resolved glyphs; unresolved counts are retained.
                run=dict(ids=[r['id'] for r in rr], n=len(vectors), total=len(rr), vector=np.median(vectors,axis=0).tolist() if vectors else None, faces=dict(facecounts), resolved=sum(facecounts.values()))
                for r in rr: lookup[r['id']]=len(runs)
                runs.append(run)
            p['runs'][mode]=runs; p['lookup'][mode]=lookup

noise={}; report={}
for mode in MODES:
    noise[mode]={}; report[mode]={}
    for dpi in (200,300,600):
        runs=[r for p in pages['train'] if p['dpi']==dpi for r in p['runs'][mode] if r['vector'] is not None and r['resolved']>=2 and len(r['faces'])==1]
        diffs=[]; bins=defaultdict(list)
        for a,b in combinations(runs,2):
            if next(iter(a['faces']))!=next(iter(b['faces'])): continue
            factor=math.sqrt(1/a['n']+1/b['n']); delta=np.abs(np.array(a['vector'])-b['vector']); diffs.append(delta/factor)
            n=2/(1/a['n']+1/b['n']); key='1-2' if n<3 else '3-5' if n<6 else '6-11' if n<12 else '12+'
            bins[key].append(delta)
        scales=np.sqrt(np.mean(np.square(diffs),axis=0)).tolist() if diffs else [None]*len(STYLE)
        noise[mode][str(dpi)]=scales
        report[mode][str(dpi)]=dict(scales=dict(zip(STYLE,scales)),same_face_run_pairs=len(diffs),pure_resolved_runs=len(runs),length_bins={k:dict(pairs=len(v),rms_difference=dict(zip(STYLE,np.sqrt(np.mean(np.square(v),axis=0)).tolist()))) for k,v in sorted(bins.items())})
(OUT/'s1c-noise.json').write_text(json.dumps(dict(schema='font04-s1c-noise-v1',method='Train-only per-DPI character median centering; median run residual; RMS same-face run pair differences multiplied by 1/sqrt(1/n1+1/n2). Oracle-pure among resolved glyphs, at least two resolved. All distinct within-page run pairs; pair dependence and unresolved labels limit precision.',features=STYLE,character_normalization_counts={str(d):sum(1 for x in normal if x[0]==d)//len(STYLE) for d in (200,300,600)},calibration=report),indent=2)+'\n')

def incompatible(a,b,mode,dpi,k):
    if a['vector'] is None or b['vector'] is None: return False
    s=noise[mode][str(dpi)]; factor=math.sqrt(1/a['n']+1/b['n'])
    return any(scale is not None and abs(x-y)>k*scale*factor for x,y,scale in zip(a['vector'],b['vector'],s))

def cluster(p,mode,k):
    runs=p['runs'][mode]; parent=list(range(len(runs)))
    def find(i):
        while parent[i]!=i: parent[i]=parent[parent[i]]; i=parent[i]
        return i
    for i,a in enumerate(runs):
        if a['vector'] is None: continue
        for j in range(i):
            b=runs[j]
            if b['vector'] is not None and not incompatible(a,b,mode,p['dpi'],k):
                x,y=find(i),find(j)
                if x!=y: parent[x]=y
    return [find(i) for i in range(len(runs))]

clusters={}; cluster_report={}
for name,pp in pages.items():
    cluster_report[name]={}
    for mode in MODES:
        cluster_report[name][mode]={}
        for k in KS:
            info=[]
            for i,p in enumerate(pp):
                c=cluster(p,mode,k); clusters[(name,i,mode,k)]=c; faces=defaultdict(Counter)
                for r,cid in zip(p['runs'][mode],c): faces[cid].update(r['faces'])
                resolved=sum(sum(v.values()) for v in faces.values()); correct=sum(max(v.values()) for v in faces.values() if v)
                info.append(dict(page=i,clusters=len(set(c)),runs=len(c),unavailable_runs=sum(r['vector'] is None for r in p['runs'][mode]),oracle_resolved_glyphs=resolved,purity=correct/resolved if resolved else None))
            cluster_report[name][mode][str(k)]=info

def structural(r,p):
    a=next(x for x in p['rows'] if x['id']==r['member_id']); b=next(x for x in p['rows'] if x['id']==r['canonical_id'])
    if a['character'] not in CONFUSABLE|ROUND and b['character'] not in CONFUSABLE|ROUND: return False
    if a['character']!=b['character']: return True
    x,y=p['fs'][a['id']],p['fs'][b['id']]
    if not x or not y: return False
    # Features are already dimensionless glyph-normalised, as in S1b.
    if a['character'] in CONFUSABLE:
        return x['dot']!=y['dot'] or abs(x['flag']-y['flag'])>.20 or abs(x['foot']-y['foot'])>.25
    return (x['hole']>.015)!=(y['hole']>.015)

def fallback(r,k):
    return bool(r['delta'] and any(glyph_noise[str(r['dpi'])].get(f) is not None and v>k*glyph_noise[str(r['dpi'])][f] for f,v in r['delta'].items()))

def veto(r,variant,mode,k):
    p=pages[r['dataset']][r['page']]; lookup=p['lookup'][mode]; ia=lookup[r['member_id']]; ib=lookup[r['canonical_id']]; a=p['runs'][mode][ia]; b=p['runs'][mode][ib]
    style=False
    if variant.startswith('A'): style=incompatible(a,b,mode,p['dpi'],k)
    if variant.startswith('B'): style=clusters[(r['dataset'],r['page'],mode,k)][ia]!=clusters[(r['dataset'],r['page'],mode,k)][ib] if a['vector'] is not None and b['vector'] is not None else False
    guard=False
    if 'C1' in variant: guard=structural(r,p)
    if 'C2' in variant: guard=r['label'] in CONFUSABLE|ROUND or next(x['character'] for x in p['rows'] if x['id']==r['canonical_id']) in CONFUSABLE|ROUND
    return style or guard or ('fallback' in variant and min(a['n'],b['n'])<3 and fallback(r,k))

variants=['A','B','C1','C2']+[x+'+'+y+z for x in ('A','B') for y in ('C1','C2') for z in ('','+fallback')]
frontier={}; decisions={}
for name,rows in pairs.items():
    frontier[name]={}
    for variant in variants:
        frontier[name][variant]={}
        for mode in MODES:
            frontier[name][variant][mode]={}
            for k in KS:
                flags=[veto(r,variant,mode,k) for r in rows]; decisions[(name,variant,mode,k)]=flags
                missing_runs=sum(any(pages[name][r['page']]['runs'][mode][pages[name][r['page']]['lookup'][mode][r[x]]] ['vector'] is None for x in ('member_id','canonical_id')) for r in rows)
                result={}
                for threshold in (.2,.3):
                    by=defaultdict(Counter)
                    for r,caught in zip(rows,flags):
                        visible=r['cls']=='different-character' or (r['shape_xor'] is not None and r['shape_xor']>threshold)
                        if visible: by[r['cls']]['caught' if caught else 'remaining']+=1
                        elif r['cls']=='same-face' and caught: by[r['cls']]['false_veto']+=1
                        elif r['cls'] in ('different-family','same-family-different-style') and r['shape_xor'] is not None and caught: by[r['cls']]['interchangeable_veto']+=1
                    kept=len(rows)-sum(flags); self_count=baseline['meta'][name]['stats'].get('accepted_self',0)
                    result[str(threshold)]=dict(accepted_substitutions=len(rows),kept=kept,retained_fraction=kept/len(rows) if rows else None,by_class=dict(by),unresolved=sum(r['cls']=='unresolved' for r in rows),missing_features=sum(r['delta'] is None for r in rows),missing_run_features=missing_runs,accepted_members=len(rows)+self_count,accepted_members_kept=kept+self_count,accepted_members_retained_fraction=(kept+self_count)/(len(rows)+self_count) if rows or self_count else None,estimated_net_outlines_retired=None)
                frontier[name][variant][mode][str(k)]=result
out=dict(schema='font04-s1c-v1',description='Offline vetoes of frozen accepted non-self substitutions; FONT-01 train is calibration, validation/test held-out development, P2 spent development. Net retirement cannot be inferred from occurrence vetoes.',method=dict(runs='word=(page,span_id); lines=greedy page-local y-overlap/baseline; financial occurrence IDs resolved with (page,id)',normalization='train-only per-character per-DPI medians, residual median per run',noise='train-only oracle-pure same-face run pairs; length scale sqrt(1/n1+1/n2)',cluster='per-page deterministic single-linkage under same feature thresholds; missing runs abstain',C1='same OCR label plus dimensionless structural check: dot equality, flag difference <=0.20, foot <=0.25; round hole presence threshold 0.015; missing masks abstain',C2='exclude sharing when either OCR label is confusable',fallback='S1b k veto only if either run has fewer than 3 normalizable glyphs',net_retirement='unavailable: occurrence decisions do not identify which original outlines remain live or added canonicals disappear'),meta=baseline['meta'],clusters=cluster_report,frontier=frontier)
(OUT/'s1c-frontier.json').write_text(json.dumps(out,indent=2)+'\n')
# Review P2 best operating point selected by highest caught with financial >=90%,
# then fewest same-face vetoes; all classes represented in the review manifest.
def score(v,mode,k):
    fin=frontier['financial'][v][mode][str(k)]['0.2']['retained_fraction']; d=frontier['P2'][v][mode][str(k)]['0.2']['by_class']; caught=sum(x.get('caught',0) for x in d.values()); false=d.get('same-face',{}).get('false_veto',0)
    return (fin>=.9,caught,-false)
variant,mode,k=max(((v,m,k) for v in variants for m in MODES for k in KS),key=lambda x:score(*x))
rows=pairs['P2']; flags=decisions[('P2',variant,mode,k)]; buckets=defaultdict(list)
for r,f in zip(rows,flags):
    visible=r['cls']=='different-character' or (r['shape_xor'] is not None and r['shape_xor']>.2)
    if visible: buckets['caught' if f else 'missed'].append(r)
    elif f and r['cls']!='unresolved': buckets['false-veto'].append(r)
local=BASE/'S1c'; local.mkdir(parents=True,exist_ok=True); examples=OUT/'s1c-examples'; examples.mkdir(exist_ok=True)
for category in ('caught','missed','false-veto'):
    selected=buckets[category][:40]; canvas=Image.new('RGB',(720,35+76*max(1,len(selected))),'white'); draw=ImageDraw.Draw(canvas)
    draw.text((4,4),f'P2 {variant} {mode} k={k}: {category}; member | canonical source masks',fill='black')
    for i,r in enumerate(selected):
        y=35+i*76; draw.text((3,y),f"{i+1:02} p{r['page']} {r['member']} <- {r['canonical']}\n{r['label']} {r['cls']} xor {r['shape_xor']}",fill='black')
        p=pages['P2'][r['page']]
        for j,rid in enumerate((r['member_id'],r['canonical_id'])):
            row=next(x for x in p['rows'] if x['id']==rid); s=row['source']
            if s and s.get('mask'):
                im=Image.fromarray((255-255*np.asarray(s['mask'],dtype=np.uint8).reshape(s['height'],s['width']))).convert('RGB'); im.thumbnail((160,68),Image.Resampling.NEAREST); canvas.paste(im,(390+j*160,y))
    canvas.save(local/f'{category}.png',optimize=True)
    canvas.crop((0,0,720,35+76*min(3,max(1,len(selected))))).save(examples/f'{category}.png',optimize=True)
(local/'review-manifest.json').write_text(json.dumps(dict(selection=dict(variant=variant,mode=mode,k=k,rule='maximize P2 visible caught subject to financial retention >=90%, then minimize same-face vetoes'),available={k:len(v) for k,v in buckets.items()},rows={k:v[:40] for k,v in buckets.items()}),indent=2)+'\n')
print('selected',variant,mode,k,score(variant,mode,k))
