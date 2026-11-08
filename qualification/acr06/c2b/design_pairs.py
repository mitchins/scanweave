#!/usr/bin/env python3
"""Link OCR to pristine ink by overlap; measure per-member best tested fits by truth design."""
from pathlib import Path
from collections import defaultdict,Counter
import re,json,statistics
import numpy as np
from PIL import Image
from lxml import etree
R=Path('/data/coding/scanweave/qualification'); T=R/'acr06/local/c2b/trace'; O=R/'acr06/local/c2b'; sources={'p2':('P2','p2'),'p2prime':('P2prime','p2prime'),'p2pp':('P2pp','p2pp'), **{f'font01-{split}':('FONT',split) for split in ('train','validation','test')}}
all_records={}; summary={}
for name,(folder,sub) in sources.items():
 root=(R/'font01/local/corpus-font01-v1'/sub if folder=='FONT' else R/'font04/local'/folder/sub)
 obs=[json.loads(s) for s in (root/'observations.jsonl').open()]
 truth={r['id']:r for r in (json.loads(s) for s in (root/'oracle/labels.jsonl').open())}
 for sheet in (range(1,3) if folder=='FONT' else range(3,9)):
  doc=f'{name}-{sheet}'; path=T/f'{doc}.pdf.funnel.json'
  if not path.exists() or not (T/f'{doc}.pdf.json').exists():continue
  d=json.load(path.open()); side=json.load((T/f'{doc}.pdf.json').open()); xml=etree.fromstring(side['pages'][0]['hocr'].encode(),etree.XMLParser(recover=True,resolve_entities=False,no_network=True)); words=xml.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]');
  refs=[]
  for ob in obs:
   if (ob['page'] != sheet if folder=='FONT' else ob['page'] != sheet // 3 or ob['sheet'] != sheet % 3):continue
   label=truth[ob['id']]; a=np.array(Image.open(root/'oracle'/f"{ob['id']}-pristine.png").convert('L')); ink=(255-a).astype(np.float32); mass=float(ink.sum())
   if mass: refs.append((ob,label,ink,mass))
  matches={}; reasons=Counter()
  for row in d['rows']:
   m=re.fullmatch(r'w(\d+)s(\d+)',row['id'])
   if not m:reasons['non_symbol']+=1;continue
   wi,ci=map(int,m.groups())
   try:
    chars=words[wi].xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_cinfo ")]'); t=chars[ci].get('title'); box=list(map(int,re.search(r'x_bboxes (\d+) (\d+) (\d+) (\d+)',t).groups()))
   except (IndexError,AttributeError):reasons['missing_box']+=1;continue
   hits=[]
   for ob,label,ink,mass in refs:
    x,y,x2,y2=ob['bbox']; bx,by,bx2,by2=box; ix=max(x,bx); iy=max(y,by); ex=min(x2,bx2); ey=min(y2,by2)
    if ix>=ex or iy>=ey:continue
    captured=float(ink[iy-y:ey-y,ix-x:ex-x].sum())/mass
    if captured>0:hits.append((captured,ob,label))
   hits.sort(key=lambda h:h[0],reverse=True)
   if not hits or hits[0][0]<.5:reasons['low_overlap']+=1;continue
   if len(hits)>1 and hits[1][0]>.5*hits[0][0]:reasons['ambiguous_overlap']+=1;continue
   score,ob,label=hits[0]
   if label['character'] != row['label']:reasons['ocr_truth_mismatch']+=1;continue
   matches[row['member']]={'truth_id':ob['id'],'character':label['character'],'face':label['face'],'font_sha256':label['font_sha256'],'point_size':label['point_size'],'bbox':ob['bbox'],'ocr_box':box,'ink_capture':score,'ocr_character':row['label']}; reasons['matched']+=1
  same=defaultdict(list); diff=defaultdict(list); pair_counts=Counter()
  for f in d['fits']:
   i,j=f['member'],f['canonical']
   if i==j or i not in matches or j not in matches:continue
   a,b=matches[i],matches[j]; eq=all(a[k]==b[k] for k in ('character','font_sha256'));kind='same' if eq else 'different';pair_counts[kind]+=1; pair_counts[kind+'_above_008']+=f['error']>.08
   (same if eq else diff)[i].append((f['error'],j))
  data={'matches':matches,'match_counts':dict(reasons),'best':{},'pair_counts':dict(pair_counts)}
  for kind,group in [('same',same),('different',diff)]:
   best={i:min(vals) for i,vals in group.items()}; errors=sorted(e for e,j in best.values());data['best'][kind]={'count':len(errors),'above_008':sum(e>.08 for e in errors),'median':statistics.median(errors) if errors else None,'p90':float(np.quantile(errors,.9)) if errors else None,'members':{str(i):{'error':v[0],'canonical':v[1]} for i,v in best.items()}}
  all_records[doc]=data;summary[doc]={'eligible':len(d['rows']),'match_counts':dict(reasons),'pair_counts':dict(pair_counts),'best':{k:{x:y for x,y in val.items() if x!='members'} for k,val in data['best'].items()}}
  print(doc,len(matches),'/',len(d['rows']),flush=True)
(O/'truth-pair-details.json').write_text(json.dumps(all_records,indent=1)+'\n');(R/'acr06/c2b/design-pairs-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
