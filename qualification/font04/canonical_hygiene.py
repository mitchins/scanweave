"""Source-only, pre-offer canonical contamination screen and material regressions."""
from pathlib import Path
import collections,json
import numpy as np
from scipy import ndimage
from qualification.font04.geometry import topology
from qualification.font04.metrics import sha
BASE=Path('qualification/font04');ROOT=BASE/'local'
POLICY=dict(source_threshold=.25,class_support_fraction=.20,footprint_halo=2,unsupported_fraction=.05,unsupported_mass=4.,unsupported_component_mass=3.,rare_topology_fraction=.10)

def screen(art):
    rows=json.loads((art/'source.json').read_text())['rows'];fields=np.load(art/'fields.npy');meta=json.loads((art/'frames.json').read_text());out=json.loads((art/'outlines.json').read_text())['records'];records=[]
    for o in out:
        if 'gid' not in o:continue
        j=int(o['key'].rsplit('-',1)[1]);row=rows[j];indices=[i for i,r in enumerate(rows) if r['character']==row['character'] and r['shape_key']!=row['shape_key'] and fields[i].sum()>0]
        reasons=[]
        if not indices:
            records.append(dict(canonical=j,reasons=['no_independent_class_footprint'],offered=False));continue
        a=np.zeros((64,64));x,y=meta['origins'][j];a[y:y+o['height'],x:x+o['width']]=np.array(o['coverage']).reshape(o['height'],o['width'])
        support=(fields[indices]>.25).mean(0);footprint=ndimage.binary_dilation(support>=.2,iterations=2);mass=float((a*~footprint).sum());fraction=mass/max(1.,float(a.sum()));labels,n=ndimage.label(a>.25);component=[]
        for k in range(1,n+1):
            mask=labels==k;unsupported=float(a[mask&~footprint].sum());total=float(a[mask].sum());bad=unsupported>=3 and unsupported/max(1,total)>.5
            component.append(dict(component=k,mass=total,unsupported=unsupported,fires=bad))
        if mass>4 and fraction>.05:reasons.append('outside_independent_class_footprint')
        if any(c['fires'] for c in component):reasons.append('unsupported_component')
        tops=collections.Counter(topology(fields[i]>.5) for i in indices);t=topology(a>.5);frequency=tops[t]/len(indices)
        if frequency<.1:reasons.append('class_unsupported_topology')
        records.append(dict(canonical=j,character=row['character'],independent_members=len(indices),unsupported_mass=mass,unsupported_fraction=fraction,topology=list(t),topology_support=frequency,components=component,reasons=reasons,offered=not reasons))
    return dict(policy=POLICY,source_snapshot_sha256=sha(art/'source.json'),records=records,excluded=[r['canonical'] for r in records if not r['offered']])

def regressions():
    results=[]
    for name,review in [('financial-B1prime-PV','review_b1prime/key-decoded-rejected.json'),('financial-B2-PV','review_b2/key-decoded.json')]:
        art=ROOT/(name+'.pdf.font04');h=screen(art);hr={r['canonical']:r for r in h['records']};plan=json.loads((art/'plan.json').read_text());rejected={r['member']:r for r in plan['rejection_ledger']};review_path=BASE/review;decoded=json.loads(review_path.read_text());decoded=decoded['decoded'] if isinstance(decoded,dict) else decoded
        for r in decoded:
            if not (r.get('classification','').startswith('material') or (r.get('cls')=='material' and r['flag_on']=='candidate')):continue
            i=r['member'] if 'member'in r else int(r['id'].split('-')[1]);p=rejected[i];hard=[x for x in p['reasons'] if x not in ['insufficient_noise_witnesses','noise_floor','grouping_exception','functional_text_identity']];hygiene=hr[p['canonical']]['reasons'];assert hard or hygiene
            results.append(dict(review=str(review_path),review_sha256=sha(review_path),member=i,canonical=p['canonical'],judgment=r.get('classification',r.get('note')),hygiene=hygiene,retained_hard_vetoes=hard,pass_regression=True))
    assert len(results)==16
    result=dict(material_cases_only=True,n=16,regressions=results,note='A valid canonical paired with a wrong-label/contaminated target may pass hygiene; the unchanged member hard veto remains mandatory. No minor/repair/current-side judgments used as material cases.')
    (BASE/'b2prime-material-regressions.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    h=screen(ROOT/'financial-B2-P-initial.pdf.font04');(BASE/'b2prime-canonical-hygiene.json').write_text(json.dumps(h,indent=2)+'\n');print('hygiene',len(h['excluded']),'of',len(h['records']),'excluded; material regressions',regressions()['n'])
