"""Ownership-aware unexplained-ink hard veto; exceptions retain default programs."""
import json
from pathlib import Path
import numpy as np
from scipy import ndimage

HALO=1.0
MIN_AREA=1
MIN_MASS=.75

def components(source,current,candidate,member):
    # Source components first: default agreement establishes ownership. Scanner
    # dirt absent from the current output cannot trigger retention.
    labels,n=ndimage.label(source>.25)
    footprint=candidate>.10
    distance=ndimage.distance_transform_edt(~footprint)
    ledger=[]
    for label in range(1,n+1):
        component=labels==label
        owned=component & (current>.15)
        unexplained=owned & (distance>HALO)
        area=int(unexplained.sum());mass=float(source[unexplained].sum())
        firing=area>=MIN_AREA and mass>=MIN_MASS
        ledger.append(dict(member=member,component=label,source_area=int(component.sum()),owned_area=int(owned.sum()),area=area,contrast=float(source[unexplained].mean()) if area else 0.,mass=mass,distance=float(distance[owned].max()) if owned.any() else None,halo=HALO,decision='keep_default_exception' if firing else ('unowned_dirt_ignored' if not owned.any() else 'covered_or_below_significance'),fires=bool(firing)))
    return ledger

def main(path):
    artifact=Path(str(path)+'.font04');plan=json.loads((artifact/'plan.json').read_text());ledger=[]
    is_b2=plan.get('scope')=='all 55 frequent classes'
    with np.load(artifact/('class-crops.npz' if is_b2 else 'prime-crops.npz')) as crops:
        for a in plan['assignments']:
            i=a['member'];ledger.extend(components(crops[f'{i}-analytic-source'],crops[f'{i}-analytic-default'],crops[f'{i}-analytic-candidate'],i))
    fired=sorted({r['member'] for r in ledger if r['fires']})
    if not is_b2:assert 277 in fired, 'glyph-277 owned mark must veto the substitution'
    result=dict(schema='font04-owned-components-v1',source_pdf=str(path),source_pdf_sha256=__import__('hashlib').sha256(path.read_bytes()).hexdigest(),exceptions=fired,components=ledger,policy=dict(halo_pixels=HALO,min_area=MIN_AREA,min_mass=MIN_MASS,source_threshold=.25,default_ownership_threshold=.15,candidate_footprint_threshold=.10),regression_glyph_277='PV complete-output regression pending class_verify' if is_b2 else 'PASS: default retained; owned mark survives')
    Path('qualification/font04/'+('b2-owned-component-ledger.json' if is_b2 else 'owned-component-ledger.json')).write_text(json.dumps(result,indent=2)+'\n')
    print('ownership veto:',fired)

def test():
    source=np.zeros((24,24));source[10:20,8:16]=1;source[3:5,12:14]=1
    candidate=source.copy();candidate[3:5,12:14]=0
    assert any(r['fires'] for r in components(source,source,candidate,277))
    assert not any(r['fires'] for r in components(source,candidate,candidate,0))
    assert not any(r['fires'] for r in components(source,source,source,0))

if __name__=='__main__':
    import sys
    test();main(Path(sys.argv[1]))
