"""LOO source-variation estimates without a witness-count admission gate."""
from pathlib import Path
import collections,json
import numpy as np
from qualification.font04.geometry import register,geometry
from qualification.font04.planner import mse
from qualification.font04.metrics import sha
BASE=Path('qualification/font04');ART=BASE/'local/financial-B2-P-initial.pdf.font04'

def build():
    rows=json.loads((ART/'source.json').read_text())['rows'];plan=json.loads((ART/'plan.json').read_text());fields=np.load(ART/'fields.npy');bands=[]
    from scipy import ndimage
    for f in fields:
        g=geometry(f);weight=float(f.sum())/max(1.,float(((f>.5)^ndimage.binary_erosion(f>.5)).sum())) if g else 0.;bands.append(int(np.floor(np.log(max(weight,.1))/np.log(1.3))))
    records=[];counts=collections.Counter()
    for i,row in enumerate(rows):
        level=plan['noise_floor'][i];peers=[k for k,x in enumerate(plan['noise_floor']) if x is not None and rows[k]['character']==row['character'] and bands[k]==bands[i] and rows[k]['shape_key']!=row['shape_key']];kind='individual_LOO';witnesses=[]
        if level is None:
            if peers:level=float(np.median([plan['noise_floor'][k] for k in peers]));kind='independent_class_weight_band_median'
            else:
                candidates=[j for j,r in enumerate(rows) if j!=i and r['character']==row['character'] and fields[j].sum()>0];independent=[j for j in candidates if rows[j]['shape_key']!=row['shape_key']];pool=independent or candidates;sameband=[j for j in pool if bands[j]==bands[i]];pool=sameband or pool
                # Eligibility is an uncertainty/ranking signal. It cannot turn
                # the numeric criterion into an implicit witness-count gate.
                nearest=sorted(pool,key=lambda j:(mse(fields[i],fields[j]),j))[:5]
                values=[]
                for j in nearest:
                    p,aligned=register(fields[i],fields[j]);error=mse(fields[i],aligned);values.append(error);witnesses.append(dict(member=j,error=error,parameters=p.tolist(),different_current_program=rows[j]['shape_key']!=row['shape_key']))
                assert values,'Every frequent class must have another source impression'
                level=float(np.quantile(values,.85));kind='source_LOO_no_support_gate' if independent else 'shared_current_program_source_LOO_diagnostic'
        assert level is not None and np.isfinite(level)
        counts[kind]+=1;records.append(dict(member=i,character=row['character'],band=bands[i],floor=float(level),source=kind,independent_calibrated_peers=len(peers),source_witnesses=witnesses,original_noise_support=plan['noise_support'][i]['status']))
    result=dict(summary=dict(counts),members=records,source_snapshot_sha256=sha(ART/'source.json'),definition='Original LOO estimate; then independent calibrated class/weight-band median; otherwise bounded registration of nearest source impressions, without requiring the source-pair hard checks to calibrate a floor. Current-program independence is preferred and logged; absence is diagnostic, never admission gating. Candidate hygiene, member hard vetoes, and weight separation remain mandatory. All numeric error criteria still swept at 1.0/1.5/2.0.',no_missing_floors=True)
    (BASE/'b2prime-soft-support.json').write_text(json.dumps(result,indent=2)+'\n');print('Soft diagnostic estimates',dict(counts),flush=True);return result

if __name__=='__main__':build()
