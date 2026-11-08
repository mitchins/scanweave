#!/usr/bin/env python3
"""Summarize member-existence and selected-group stages; overlapping filters are not causal attribution."""
from pathlib import Path
from collections import Counter, defaultdict
import json, hashlib
R=Path('/data/coding/scanweave/qualification/acr06')
T=R/'local/c2b/trace'; out={}
for path in sorted(T.glob('*.pdf.funnel.json')):
    d=json.loads(path.read_text()); rows=d['rows']; by=defaultdict(list)
    for fit in d['fits']:
        if fit['member'] != fit['canonical']: by[fit['member']].append(fit)
    stages=Counter(); stages['occurrences']=len(d['occurrences']); stages['eligible_label_at_least_10']=len(rows)
    for row in rows:
        i=row['member']; stages['frame']+=row['has_frame']; stages['canonical_trace']+=row['has_canonical']
        pairs=by[i]; stages['any_nonself_fit']+=bool(pairs)
        structural=[f for f in pairs if not f['reasons']]
        stages['any_structural_pass']+=bool(structural)
        safe=[f for f in structural if not rows[f['canonical']]['hygiene'] and row['band']==rows[f['canonical']]['band']]
        stages['any_hygiene_band_pass']+=bool(safe)
        rel=[f for f in safe if f['error']/max(row['floor'],1e-6)<=2]
        stages['any_relative_pass']+=bool(rel)
        stages['any_absolute_pass']+=any(f['error']<=0.08 for f in rel)
    # Replay deterministic cover to expose groups removed before ownership by quorum.
    partitions=defaultdict(list)
    for row in rows: partitions[f"{row['label']}:weight{row['band']}"].append(row['member'])
    valid={(f['member'],f['canonical']):f['error']/max(rows[f['member']]['floor'],1e-6) for f in d['fits'] if not f['reasons'] and not rows[f['canonical']]['hygiene'] and rows[f['member']]['band']==rows[f['canonical']]['band'] and f['error']/max(rows[f['member']]['floor'],1e-6)<=2 and f['error']<=.08}
    stages['self_admissible_canonical']=sum((i,i) in valid for i in range(len(rows)))
    replay=[]
    for key in sorted(partitions):
        indices=partitions[key]
        users=defaultdict(set)
        for i in indices: users[rows[i]['shape_key']].add(i)
        remaining=set(indices); remapped=set()
        while remaining:
            best=None
            for j in sorted(remaining):
                if (j,j) not in valid: continue
                members=sorted(i for i in remaining if i==j or (i,j) in valid)
                union=remapped | set(members)
                retired=sum(u<=union and not u<=remapped for u in users.values())
                value=(1-retired,-len(members),sum(valid[(i,j)] for i in members if i!=j),j,members)
                if best is None or value<best: best=value
            if best is None:
                stages['cover_no_self_admissible_remaining']+=len(remaining); break
            _,_,_,j,members=best; remaining.difference_update(members)
            witnesses=len({rows[i]['shape_key'] for i in members})
            if len(members)>=2 and witnesses>=3:
                remapped.update(members); replay.append((j,members))
            else:
                stages['cover_below_quorum_members']+=len(members)
                stages['cover_below_quorum_groups']+=1
    assert replay==[(g['canonical'],g['members']) for g in d['groups']], path
    stages['planned_members']=sum(len(g['members']) for g in d['groups'])
    ownedpath=Path(str(path)+'.ownership.json')
    owned=json.loads(ownedpath.read_text()) if ownedpath.exists() else []
    for x in owned:
        for k in ('legacy','corrected'):
            stages[k+'_'+('invalid' if x[k] is None else 'reject' if x[k] else 'pass')]+=1
        stages['combined_reject']+=x['combined']
    stages['final_accepted_before_economy']=sum(r['decision']['accepted'] for r in rows)
    for r in rows:
        for reason in r['decision']['reasons']: stages['decision_'+reason]+=1
    side=json.loads(Path(str(path).removesuffix('.funnel.json')+'.json').read_text())
    # Search the sidecar rather than assuming where its sharing report lives.
    def find(obj):
        if isinstance(obj,dict):
            if 'encoded_font_bytes_before' in obj and 'decisions' in obj: return obj
            for v in obj.values():
                x=find(v)
                if x is not None:return x
        if isinstance(obj,list):
            for v in obj:
                x=find(v)
                if x is not None:return x
    sharing=find(side)
    out[path.name.removesuffix('.pdf.funnel.json')]={'counts':dict(stages),'economy':{k:sharing.get(k) for k in ('fallback','proposed_members','substituted','retired_outlines','net_outlines_retired','encoded_font_bytes_before','encoded_font_bytes_after')} if sharing else None,'trace_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(R/'c2b/measurements.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
