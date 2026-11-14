#!/usr/bin/env python3
"""Record Codex's nonblinded, provisional visual assessment of 36 fresh controls."""
import json,pathlib
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[2];Q=P/'pilot';rows=['sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E'];none='no_visible_defect';blur='blur_texture';colour='colour_shift';unclear='unclear';wrong='wrong_shape';missing='missing_ink'
# Visual inspection of the six local 4x contact sheets. These are not blinded
# assessments and explicitly are not human adjudications. Labels concern only
# the sampled crop, not the entire page or tool.
labels={
'aventinus_grammatica_1515_0008':[[none],[none],[none],[none],[blur,colour],[blur]],
'luther_babstum_1526_0011':[[none],[none],[none],[none],[blur,colour],[blur]],
'arnold_ketzerhistorie01_1699_0114':[[none],[unclear],[none],[none],[blur,colour],[blur]],
'benner_herrnhuterey04_1748_0013':[[none],[none],[none],[none],[blur,colour],[unclear]],
'8967333':[[none],[none],[none],[none],[blur],[blur]],
'12342014':[[unclear],[none],[none],[none],[blur,colour],[wrong,missing]],
}
controls=json.loads((B/'pilot/phase1b/controls/controls.json').read_text());calfile=Q/'results/phase1b/calibration.json';cal=json.loads(calfile.read_text());source=Q/'phase1b/calibrate.py';prefix=source.read_text().split('records=[]')[0];ns={'__file__':str(source),'__name__':'pilot_control_scoring'};exec(compile(prefix,str(source),'exec'),ns);getim=ns['getim'];calc=ns['calc']; assessments=[]
for item in controls:
 id=item['page'];row=item['row'];key=id.split('/')[-1];types=labels[key][rows.index(row)];src=getim(id,'src');out=getim(id,row);scores=calc(src,out,item['bbox'],id);assessments.append({**item,'assessment':'AI-assessed, provisional (not human-adjudicated); nonblinded','taxonomy':types,'scores':scores,'small_box':min(item['bbox'][2]-item['bbox'][0]-6,item['bbox'][3]-item['bbox'][1]-6)<10})
summary={}
for det in ['glyph_shape','missing_ink','spurious_ink','illustration_colour','border_inversion']:
 def label(x):
  t=x['taxonomy']
  if det in ('illustration_colour','border_inversion') and (not x['scores'] or x['scores'][det] is None):return None
  if 'unclear' in t:return None
  relevant={'glyph_shape':{'wrong_shape','missing_ink'},'missing_ink':{'missing_ink'},'spurious_ink':{'spurious_ink_halo'},'illustration_colour':{'colour_shift','blur_texture'},'border_inversion':{'border_inversion'}}[det]
  if relevant.intersection(t):return 1
  if t==['no_visible_defect']:return 0
  return None
 threshold=cal['detectors'][det]['threshold']
 def metrics(rs):
  known=[(r,label(r)) for r in rs if label(r) is not None];positive=[r for r,l in known if l==1];negative=[r for r,l in known if l==0];hit=lambda r: threshold is not None and r['scores'] and r['scores'][det] is not None and r['scores'][det]>=threshold;tp=sum(bool(hit(r)) for r in positive);fp=sum(bool(hit(r)) for r in negative);return {'positive':len(positive),'negative':len(negative),'true_positive':tp,'false_positive':fp,'false_negative':len(positive)-tp,'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/len(positive) if positive else None}
 summary[det]={'all':metrics(assessments),'min_dimension_lt_10_px':metrics([r for r in assessments if r['small_box']]),'min_dimension_ge_10_px':metrics([r for r in assessments if not r['small_box']]),'threshold':threshold}
(Q/'results/phase1b/fresh-controls.json').write_text(json.dumps({'assessment':'AI-assessed, provisional (not human-adjudicated); nonblinded','sampling':'one fixed-seed OCR word box per page x row, excluding previous reviewed crop overlaps','controls':assessments,'detectors':summary},indent=2)+'\n')
