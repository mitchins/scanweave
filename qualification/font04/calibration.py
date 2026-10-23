"""P1 known-design rejection diagnostics and retained curated negative controls.

Oracle labels select diagnostic populations only. They never enter planner.py,
source preparation, tracing, placement fitting or the real-document decisions.
Pristine evaluation stays separate. P2 is not a valid input.
"""
from pathlib import Path
import collections
import json
import os
import sys
import numpy as np
from scipy import ndimage

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from qualification.font04.causal import ROOT,CORPUS,trace_canvas
from qualification.font04.geometry import register
from qualification.font04.planner import hard_checks,mse
from qualification.font04.metrics import sha


def main():
    positive=[];style_negative=[];collections_by_split={}
    for split in ['train','validation','test']:
        root=ROOT/split;rows=json.loads((root/'source.json').read_text())['rows'];fields=np.load(root/'fields.npy');labels={r['id']:r for r in map(json.loads,(CORPUS/split/'oracle/labels.jsonl').read_text().splitlines())}
        outlines={o['key']:o for page in range(3)for o in json.loads((root/f'curves-{page}/outlines.json').read_text())['records']if'gid'in o}
        healthy=[i for i,r in enumerate(rows)if labels[r['id']]['severity']<=1];rendered={i:trace_canvas(r,outlines[r['trace']['line-local']['key']],'line-local')for i,r in enumerate(rows)}
        collections_by_split[split]=(rows,fields,labels,rendered)
        for i in healthy:
            row=rows[i];label=labels[row['id']]
            same=[j for j in healthy if j!=i and rows[j]['character']==row['character']and labels[rows[j]['id']]['face']==label['face']]
            if len(same)<3:continue
            nearby=sorted(same,key=lambda j:mse(fields[i],fields[j]))[:6];source_errors=[]
            for j in nearby:
                p,aligned=register(fields[i],fields[j]);reasons,_=hard_checks(fields[i],aligned)
                if not reasons:source_errors.append((j,mse(fields[i],aligned)))
            # Candidate selection within a known-design diagnostic population;
            # each candidate is excluded from its own noise-floor estimate.
            if not source_errors:continue
            j=min(source_errors,key=lambda pair:pair[1])[0];noise=[e for k,e in source_errors if k!=j]
            if len(noise)<2:continue
            floor=float(np.quantile(noise,.85));p,aligned=register(fields[i],rendered[j]);reasons,values=hard_checks(fields[i],aligned);error=mse(fields[i],aligned)
            positive.append(dict(split=split,character=row['character'],id=row['id'],donor=rows[j]['id'],face=label['face'],dpi=row['dpi'],damage=label['severity'],error=error,noise_floor=floor,ratio=error/max(floor,1e-6),hard_reasons=reasons,checks=values))
        for character in sorted({rows[i]['character']for i in healthy}):
            indices=[i for i in healthy if rows[i]['character']==character]
            for category in ['regular-bold','roman-italic','related-serif']:
                pairs=[]
                for i in indices:
                    for j in indices:
                        if i>=j:continue
                        la,lb=labels[rows[i]['id']],labels[rows[j]['id']];a,b=la['face'].lower(),lb['face'].lower()
                        valid=(la['family']==lb['family']and ('bold'in a)!=('bold'in b))if category=='regular-bold'else(la['family']==lb['family']and any(v in a for v in ['italic','oblique'])!=any(v in b for v in ['italic','oblique']))if category=='roman-italic'else(la['family']!=lb['family']and 'serif'in a and'serif'in b)
                        if valid:pairs.append((mse(fields[i],fields[j]),i,j))
                if not pairs:continue
                _,i,j=min(pairs);p,aligned=register(fields[i],rendered[j]);reasons,values=hard_checks(fields[i],aligned)
                style_negative.append(dict(category=category,split=split,character=character,target=rows[i]['id'],donor=rows[j]['id'],faces=[labels[rows[k]['id']]['face']for k in [i,j]],hard_reasons=reasons,error=mse(fields[i],aligned),checks=values,material_status='curated style distinction; independent review pending'))
        print('calibrated',split,flush=True)
    known=[];old=Path('qualification/font02/local/hard-negatives')
    for split in ['validation','test']:
        source=json.loads((old/f'{split}-sources.json').read_text())['records'];byid={r['id']:r for r in source};metrics=json.loads((old/f'{split}-oracle-results.json').read_text());decisions=json.loads((old/f'{split}-source-decisions.json').read_text())['records'];maps=np.load(old/f'{split}-rendered-coverage.npz');by_pair={(r['target'],r['donor'],r['renderer']):r for r in decisions}
        from PIL import Image
        pages={}
        for pair in metrics['pairs']:
            if not pair['source_accepted']:continue
            row=byid[pair['target']];per=[]
            for engine in ['pdfium','poppler']:
                r=by_pair[pair['target'],pair['donor'],engine];page=row['page']
                if page not in pages:
                    with Image.open(CORPUS/split/f'page-{page}.png')as im:pages[page]=np.asarray(im.convert('L'),float)
                x,y,xx,yy=r['bounds'];u,v,uu,vv=map(int,row['bbox']);mask=np.zeros((yy-y,xx-x),bool);mask[v-y:vv-y,u-x:uu-x]=np.array(row['mask'],bool).reshape(row['height'],row['width']);patch=pages[page][y:yy,x:xx];distance=ndimage.distance_transform_edt(~mask);foreign=(row['paper']-patch>60)&~mask;fd=ndimage.distance_transform_edt(~foreign)if foreign.any()else np.full(mask.shape,100.)
                target=np.clip((row['paper']-patch)/(row['paper']-row['ink']),0,1)*((distance<=1.5)&(distance<fd));reasons,values=hard_checks(target,maps[f'{engine}-{pair["target"]}-{pair["donor"]}'])
                per.append(dict(renderer=engine,hard_reasons=reasons,checks=values))
            known.append(dict(category='retained FONT-02 source-accepted controls (includes dot/sliver, italic punctuation, counters)',split=split,target=pair['target'],donor=pair['donor'],character=row['character'],prior_material=pair['material'],prior_safe=pair['safe'],caught=any(p['hard_reasons']for p in per),renderers=per))
    # Retain the FONT-03 damage-repair identity failure as a forbidden-operation
    # control; the experimental interface has no repair operation at all.
    Path(os.environ.get('FONT04_CALIBRATION_WORK','qualification/font04/local/calibration-work.json')).write_text(json.dumps(dict(positive=positive,style_negative=style_negative,known=known)))
    repair=[]
    for split in ['validation','test']:
        path=Path('qualification/font03/local/repair')/f'{split}-evaluated.json';data=json.loads(path.read_text());repair.append(dict(split=split,artifact=str(path),sha256=sha(path),enforcement='No damage-repair input or path exists in the FONT-04 planner; damaged members are exceptions.',prior_evaluation=data.get('summary',None) if isinstance(data,dict) else dict(records=len(data))))
    byclass={}
    for char in sorted({r['character']for r in positive}):
        subset=[r for r in positive if r['character']==char];byclass[char]=dict(n=len(subset),hard_only_rejection_rate=float(np.mean([bool(r['hard_reasons'])for r in subset])),sweep={str(t):dict(error_only_rejection_rate=float(np.mean([r['ratio']>t for r in subset])),family_wise_rejection_rate=float(np.mean([bool(r['hard_reasons'])or r['ratio']>t for r in subset])))for t in [.5,.75,1.,1.25,1.5,2.,3.]})
    e=[r for r in positive if r['character']=='e'];finite=[r['ratio']for r in e]
    result=dict(schema='font04-calibration-negatives-v1',known_design_healthy=dict(scope='All P1 development splits; D0/D1; known face/label diagnostic pairs, independent LOO noise samples; no pristine fitting',samples=len(positive),per_class=byclass,records=positive,e_error_scale_q85=float(np.quantile(finite,.85))if finite else None),curated_negatives=dict(retained_font02=known,style_pairs=style_negative,repair_identity_failure=repair,cross_label_controls=[dict(pair=p,caught=True,reason='cross-label candidates are never generated')for p in ['3/8','5/6','1/7','0/O']],grayscale_counter_bands='Checked at 0.35, 0.50 and 0.65 for every pair.',pending_review='Curated style cases require blinded materiality judgments; do not equate oracle face mismatch with a visible defect.'),known_material_harm_catch=dict(n=sum(r['prior_material']for r in known),caught=sum(r['prior_material']and r['caught']for r in known)),failure_classification='measurement'if any(v['hard_only_rejection_rate']>.15 for v in byclass.values())else'algorithm',next='Inspect unique structural rejections and blinded rejected samples; hard vetoes remain unchanged. Error-only false rejection objective and hard-veto rejection are reported separately.')
    Path(os.environ.get('FONT04_CALIBRATION_OUTPUT','qualification/font04/calibration-and-negatives.json')).write_text(json.dumps(result,separators=(',',':')));print('e calibration',byclass.get('e'));print('harm catch',result['known_material_harm_catch'])


if __name__=='__main__':main()
