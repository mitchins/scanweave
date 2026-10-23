"""Distinguish witness availability from failure of source-pair calibration."""
from pathlib import Path
import collections,json,sys
from qualification.font04.metrics import sha

def analyze(artifact):
    rows=json.loads((artifact/'source.json').read_text())['rows'];plan=json.loads((artifact/'plan.json').read_text());pairs=json.loads((artifact/'pair-ledger.json').read_text());meta=json.loads((artifact/'frames.json').read_text());successful={int(o['key'].rsplit('-',1)[1]) for o in json.loads((artifact/'outlines.json').read_text())['records'] if 'gid' in o};by_member=collections.defaultdict(list)
    for p in pairs:by_member[p['member']].append(p)
    old={r['member']:r for r in plan.get('noise_support',[])};records=[]
    for i,row in enumerate(rows):
        attempted=by_member[i];eligible=[p for p in attempted if not p['reasons'] and rows[p['canonical']]['shape_key']!=row['shape_key']];survivors=old[i]['witnesses'] if i in old else None
        if survivors is None:raise ValueError('Use the recomputed P arm with recorded surviving witnesses')
        status='calibrated' if plan['noise_floor'][i] is not None else ('fewer_than_k_eligible_witnesses' if len(eligible)<2 else 'source_pair_calibration_failure')
        records.append(dict(member=i,page=row['page'],id=row['id'],character=row.get('character','e'),frame_available=meta['frames'][i] is not None,traced_self_available=i in successful,witnesses=survivors,eligible_witnesses=len(eligible),required_k=2,shortlisted_independent_impressions=sum(rows[p['canonical']]['shape_key']!=row['shape_key'] for p in attempted),same_target_program_excluded=sum(rows[p['canonical']]['shape_key']==row['shape_key'] for p in attempted),source_pair_rejections=len(eligible)-survivors if plan['noise_floor'][i] is None else None,status=status,calibration_failure=status=='source_pair_calibration_failure',numerical_calibration_error=False))
    summary=dict(collections.Counter(r['status'] for r in records));classes={}
    for char in sorted({r['character'] for r in records}):classes[char]=dict(collections.Counter(r['status'] for r in records if r['character']==char))
    return dict(definition='Eligible witnesses are shortlisted, candidate-hard-compatible independent impressions whose current program differs from the target. Calibration failure means >=k such witnesses exist but source-to-source hard checks leave <k; it is not an optimizer exception. Surviving witness count is capped at five by the unchanged method.',summary=summary,classes=classes,records=records,source=str(artifact),source_sha256=sha(artifact/'source.json'))

def main():
    artifact=Path(sys.argv[1]);out=Path(sys.argv[2]);result=analyze(artifact);out.write_text(json.dumps(result,indent=2)+'\n')
    if '--update-plan' in sys.argv:
        path=artifact/'plan.json';p=json.loads(path.read_text());p['noise_support']=result['records'];p['noise_support_definition']=result['definition'];path.write_text(json.dumps(p,indent=2)+'\n')
    print(result['summary'])

if __name__=='__main__':main()
