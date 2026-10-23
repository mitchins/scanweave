"""Summarize frozen native ladder measurements, including class tails."""
from pathlib import Path
import collections
import json
import os
import numpy as np
from qualification.font04.metrics import summary,sha
from qualification.font04.causal import ROOT,ARMS as BASE_ARMS,CLASSES
ARMS=BASE_ARMS+['A-floor-self']
ENGINES=['analytic','pdfium','poppler'] if 'prime-causal' in str(ROOT) else ['pdfium','poppler']


def compare(records):
    means={a:float(np.mean([r.get('pristine',r['source'])['error']for r in records if r['arm']==a]))for a in ARMS}
    gain=means['A0']-means['F-self']
    effects={
        'forward_placement_A0_to_A1':means['A0']-means['A1'],
        'forward_floor_fresh_self':means['A-floor-self']-means['A2'],
        'legacy_witness_vs_fresh_floor_on_self':means['A0']-means['A-floor-self'],
        'forward_normalization_A2_to_A3':means['A2']-means['A3'],
        'forward_frame_A3_to_A4':means['A3']-means['A4'],
        'forward_placement_A4_to_Fself':means['A4']-means['F-self'],
        'reverse_floor':means['R-floor']-means['F-self'],
        'reverse_normalization':means['R-normalization']-means['F-self'],
        'reverse_frame':means['R-frame']-means['F-self'],
        'reverse_placement':means['A4']-means['F-self'],
        'cap_raised_vs_current':means['cap-current']-means['cap-raised'],
    }
    return dict(mean_error=means,A0_to_Fself_gain=gain,effects={k:dict(error_reduction=v,share_of_A0_Fself_gain=v/gain if abs(gain)>1e-10 else None)for k,v in effects.items()},Fself_vs_Fmedoid=means['F-medoid']-means['F-self'],note='Effects are matched interventions, not an additive decomposition. A-floor-self separates the native floor effect from legacy witness choice; reverse controls isolate each F-self toggle.')


def main():
    populations={}
    for population in ['train','validation','test','financial']:
        root=ROOT/population
        if not (root/'evaluated.json').exists():continue
        source=json.loads((root/'source.json').read_text());records=json.loads((root/'evaluated.json').read_text())['records']+json.loads((root/'floor-control-evaluated.json').read_text())['records'];by_class={};strata={}
        extension=Path(os.environ.get('FONT04_CAUSAL_EXTENSION_ROOT','qualification/font04/local/causal-extension'))/population
        extension_artifacts={}
        if population!='financial':
            if not (extension/'evaluated.json').exists():raise RuntimeError('Required eight-class extension incomplete: '+population)
            additional=json.loads((extension/'source.json').read_text());additional_records=json.loads((extension/'evaluated.json').read_text())['records']+json.loads((extension/'floor-control-evaluated.json').read_text())['records'];existing={r['id']for r in source['rows']};added={r['id']for r in additional['rows']}
            if existing&added:raise ValueError('Duplicate target in class extension')
            source['rows']+=additional['rows'];records+=additional_records
            exceptions={r['id']:r for r in source['abstentions']if r['id']not in added}
            exceptions.update({r['id']:r for r in additional['abstentions']})
            source['abstentions']=list(exceptions.values())
            extension_artifacts={p:dict(path=str(extension/p),sha256=sha(extension/p))for p in ['source.json','decisions.json','evaluated.json']}
            if {r['character']for r in source['rows']}!=set(CLASSES):raise ValueError('Required sixteen-class coverage absent')
        for engine in ENGINES:
            subset=[r for r in records if r['renderer']==engine]
            for char in sorted({r['character']for r in subset}):
                key=engine+':'+char;selected=[r for r in subset if r['character']==char];arms={}
                for arm in ARMS:
                    rows=[r for r in selected if r['arm']==arm];values=[r.get('pristine',r['source'])for r in rows]
                    arms[arm]=dict(n=len(rows),metrics=summary(values),worst_10=[dict(id=r['id'],dpi=r['dpi'],damage=r['damage'],**r.get('pristine',r['source']))for r in sorted(rows,key=lambda r:r.get('pristine',r['source'])['error'],reverse=True)[:10]])
                by_class[key]=dict(arms=arms,causal=compare(selected))
            for dpi,damage in sorted({(r['dpi'],r['damage'])for r in subset}):
                strata[f'{engine}:{dpi}:{damage}']=compare([r for r in subset if r['dpi']==dpi and r['damage']==damage])
        populations[population]=dict(selected=source['selected'],evaluated_targets=len(source['rows']),abstentions=source['abstentions'],extension_artifacts=extension_artifacts,class_tail=by_class,strata=strata,headline={e:compare([r for r in records if r['renderer']==e])for e in ENGINES},artifacts={p:dict(path=str(root/p),sha256=sha(root/p))for p in ['source.json','decisions.json','evaluated.json']})
    result=dict(schema='font04-checkpoint-a-v1',classes=list(CLASSES),populations=populations,method='Actual production A0; independently switchable fresh self tracing; forward/reverse controls; source-only bounded placement; both native engines and translation-independent contour metric.',P2='not accessed',qualification=dict(product_change_prepared=False,reason='No mechanism is production-qualified: independent blinded financial review is pending and renderer directions differ. No product branch or merge is justified by a ≥50% explanatory share alone.'),failure_classifications=[dict(classification='algorithm',finding='The initial A0→A2 comparison changed legacy witness and floor together. A-floor-self now separately isolates the floor in native fresh self tracing.',next='Assess native and reverse floor controls separately; the resolved confound does not qualify a product change without review.'),dict(classification='measurement',finding='Source placement fit may improve one renderer while worsening the other; means and tails must be assessed separately.',next='Independent review and renderer-phase diagnosis before product qualification.'),dict(classification='measurement',finding='Inherited ownership caches covered only eight classes; the eight-class extension repairs the requested population coverage.',next='Use full production ownership export in future experiments; retain both cohorts and denominators.'),dict(classification='data',finding='Financial population has no pristine reference and blinded judgments are pending.',next='Review the financial sheets. Do not infer pristine improvement from source fit.')])
    if 'prime-causal' in str(ROOT):
        result['schema']='font04-checkpoint-a-prime-v1'
        result['method']+=' Corrected centre-to-edge inverse in every line-frame arm; frozen cohorts and traced programs reused.'
        result['supersedes']='Pre-fix line-frame measurements and conclusions in the original Checkpoint A.'
        result['qualification']['reason']='Corrected independent blinded financial review is pending. No product promotion is qualified by these causal measurements alone.'
        result['failure_classifications']=[dict(classification='measurement',finding='Half-canvas-pixel line-frame inverse mismatch corrected and affected arms remeasured.',next='Review corrected causal shares and F-self versus F-medoid alongside renderer floors; supersede pre-fix claims.'),dict(classification='data',finding='Corrected sealed financial review is reviewer-pending.',next='Independent judgments required before any product qualification.')]
    Path('qualification/font04/checkpoint-A.json').write_text(json.dumps(result,separators=(',',':')))
    lines=['# Checkpoint A — causal ladder','',f'Classes: `{CLASSES}`. Analytic primary reference plus both native renderer screens; all three P1 splits remain development data.','', '| Population | Renderer | Targets | A0 | A1 | A4 | F-self | F-medoid |','|---|---|---:|---:|---:|---:|---:|---:|']
    for name,p in populations.items():
        for engine,h in p['headline'].items():
            m=h['mean_error'];lines.append(f"| {name} | {engine} | {p['evaluated_targets']} | "+' | '.join(f'{m[a]:.5f}'for a in ['A0','A1','A4','F-self','F-medoid'])+' |')
    lines+=['','Error is coverage squared error normalized by union ink, measured against pristine in P1 and source-owned coverage in P3. Each arm uses the same targets. The JSON includes per-class mean/p95/worst-ten, DPI/damage strata, reverse effects and explanatory shares. Shares are not additive.','',result['qualification']['reason'],'','The independent reviewer must assess renderer disagreement, the shape metric, rejected candidates, and source-frame accuracy. This checkpoint does not authorize a product promotion or B2.']
    Path('qualification/font04/checkpoint-A.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__=='__main__':main()
