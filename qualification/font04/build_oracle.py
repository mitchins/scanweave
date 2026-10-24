"""Materialize the frozen research decision oracle and executable regressions."""
import json
from pathlib import Path
import numpy as np
from qualification.font04.freeze_method import BASE, ART, digest, write
from qualification.font04.geometry import warp
from qualification.font04.planner import hard_checks


def build():
    plan = json.loads((ART/'plan.json').read_text())
    rows = json.loads((ART/'source.json').read_text())['rows']
    accepted = {r['member']:r for r in plan['assignments']}
    rejected = {r['member']:r for r in plan['rejection_ledger']}
    owned = json.loads((BASE/'local/B2prime-cover-2.0-owned.json').read_text())
    hygiene = {r['canonical']:r for r in json.loads((BASE/'b2prime-canonical-hygiene.json').read_text())['records']}
    support = {r['member']:r for r in json.loads((BASE/'b2prime-soft-support.json').read_text())['members']}
    ledger=[]
    for i,row in enumerate(rows):
        a=accepted.get(i,rejected.get(i)); assert a is not None
        j=a.get('canonical'); reasons=a.get('reasons',[])
        first=reasons[0] if reasons else None
        checks=a.get('checks',{})
        value=checks.get(first,{}).get('value'); limit=checks.get(first,{}).get('limit')
        if first=='canonical_hygiene':value=hygiene[j];limit='offered=true'
        if first=='stroke_weight_band':value=plan['weight_band'][i];limit=plan['weight_band'][j]
        if first=='unexplained_owned_ink':value=[c for c in owned['components'] if c['member']==i and c['fires']];limit=owned['policy']
        if first=='ranking_or_economy_exception':value='not selected by frozen greedy cover/group survival';limit='selected in surviving group of >=2'
        ledger.append(dict(member=i,page=row['page'],id=row['id'],character=row['character'],canonical=j,
            decision='accept' if i in accepted else 'reject',first_failing_check=first,value=value,limit=limit,
            fitted_transform=a.get('parameters'),all_reasons=reasons,checks=checks,
            weight_band=plan['weight_band'][i],noise_floor=support[i]['floor']))
    write(BASE/'reference-oracle.json',dict(schema='font04-reference-oracle-v1',method_freeze_sha256=digest(BASE/'method-freeze.json'),
        source_sha256=digest(ART/'source.json'),plan_sha256=digest(ART/'plan.json'),
        rejected_attempt_semantics='Frozen research rejection ledger selects fewest-hard-failures then lowest-error attempted canonical; this is a diagnostic attempt, not a counterfactual next-best group. Reasons preserve research order; ranking exceptions have no scalar threshold.',
        summary=dict(members=len(rows),accepted=len(accepted),rejected=len(rejected)),members=ledger))
    registry=json.loads((BASE/'b2prime-material-regressions.json').read_text())['regressions']
    cases=[]
    for r in registry:
        stem='financial-B1prime-PV' if 'b1prime' in r['review'] else 'financial-B2-PV'
        cases.append((stem,r['member'],r['canonical'],r['judgment']))
    for i in [3013,2466,63,1450,3422,1233]:
        r=rejected[i];cases.append(('financial-B2prime-cover-2.0',i,r['canonical'],f'owner mandatory member {i}'))
    b1plan=json.loads((BASE/'local/financial-B1prime-PV.pdf.font04/plan.json').read_text())
    r=next(r for r in b1plan['rejection_ledger'] if r['member']==277)
    cases.append(('financial-B1prime-PV',277,r['canonical'],'glyph-277; same physical draw as B2 member 3422'))
    fixtures=[]
    for stem,i,j,description in cases:
        art=BASE/'local'/f'{stem}.pdf.font04'
        fields=np.load(art/'fields.npy');p=json.loads((art/'plan.json').read_text());rr=next(r for r in p['rejection_ledger'] if r['member']==i)
        meta=json.loads((art/'frames.json').read_text());out=json.loads((art/'outlines.json').read_text())['records']
        o=next(o for o in out if o['key']==f'font04-e-{j}');a=np.zeros((64,64));x,y=meta['origins'][j];a[y:y+o['height'],x:x+o['width']]=np.array(o['coverage']).reshape(o['height'],o['width'])
        aligned=warp(a,rr['parameters']);reasons,checks=hard_checks(fields[i],aligned)
        entry=dict(source=stem,member=i,canonical=j,description=description,parameters=rr['parameters'],
            reference=fields[i].ravel().tolist(),candidate=a.ravel().tolist(),expected_hard_reasons=reasons,expected_checks=checks,
            expected_final_decision='reject')
        if i in [277,3422,1233]:
            entry['owned_components']=[c for c in owned['components'] if c['member']==(3422 if i==277 else i)]
            assert any(c['fires'] for c in entry['owned_components'])
        else: assert reasons
        fixtures.append(entry)
    write(BASE/'regression-fixtures.json',dict(schema='font04-regressions-v1',width=64,height=64,cases=fixtures))
    assert len(fixtures)==23
    print('oracle',len(ledger),'accepted',len(accepted),'regressions',len(fixtures))


if __name__=='__main__': build()
