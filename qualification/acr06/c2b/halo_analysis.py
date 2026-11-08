#!/usr/bin/env python3
"""Compare counterfactual planned members, pair admission, and overlap with other OCR boxes."""
from pathlib import Path
import json,re,collections,hashlib
import numpy as np,pikepdf
from scipy.ndimage import distance_transform_edt
from lxml import etree
R=Path('/data/coding/scanweave/qualification'); L=R/'acr06/local/c2b';T=L/'trace';H=L/'halo';D=L/'detail';truth=json.load((L/'truth-pair-details.json').open());out={};pairsout=[]
for hp in sorted(H.glob('*.pdf.funnel.json')):
 name=hp.name.removesuffix('.pdf.funnel.json')
 if name.startswith('identity-'):continue
 bp=T/f'{name}.pdf.funnel.json';detail=D/f'{name}.pdf.detail.json';sp=T/f'{name}.pdf.json'
 if not bp.exists() or not detail.exists() or not sp.exists():raise RuntimeError(f'missing baseline for {name}')
 a=json.load(bp.open());b=json.load(hp.open());rows=a['rows'];new=b['rows']; old_by_id={r['id']:r['member'] for r in rows};new_by_id={r['id']:r['member'] for r in new}; assert set(old_by_id)==set(new_by_id)
 old_group={rows[i]['id'] for g in a['groups'] for i in g['members']};new_group={new[i]['id'] for g in b['groups'] for i in g['members']};newly=sorted(new_group-old_group);lost=sorted(old_group-new_group)
 def isvalid(f,rs):
  i,j=f['member'],f['canonical'];return not f['reasons'] and not rs[j]['hygiene'] and rs[i]['band']==rs[j]['band'] and f['error']/max(rs[i]['floor'],1e-6)<=2 and f['error']<=.08
 oldtested={(rows[f['member']]['id'],rows[f['canonical']]['id']) for f in a['fits'] if f['member']!=f['canonical']};oldvalid={(rows[f['member']]['id'],rows[f['canonical']]['id']) for f in a['fits'] if f['member']!=f['canonical'] and isvalid(f,rows)}; bytruth=truth[name]['matches'];counts=collections.Counter()
 for f in b['fits']:
  if f['member']==f['canonical'] or not isvalid(f,new):continue
  mid=new[f['member']]['id'];cid=new[f['canonical']]['id']
  if (mid,cid) in oldvalid:continue
  i=old_by_id[mid];j=old_by_id[cid];mi=bytruth.get(str(i));mj=bytruth.get(str(j));category='unmatched' if mi is None or mj is None else ('same' if all(mi[k]==mj[k] for k in ('character','font_sha256')) else 'different');counts[category]+=1;pairsout.append({'document':name,'id':mid,'canonical_id':cid,'category':category,'baseline_tested':(mid,cid) in oldtested,'error':f['error']})
 # OCR-box proxy: newly admitted source support touching nonwhite source in another OCR symbol's box.
 side=json.load(sp.open());xml=etree.fromstring(side['pages'][0]['hocr'].encode(),etree.XMLParser(recover=True,resolve_entities=False,no_network=True));words=xml.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]');boxes=[]
 for wi,word in enumerate(words):
  for ci,ch in enumerate(word.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_cinfo ")]')):
   m=re.search(r'x_bboxes (\d+) (\d+) (\d+) (\d+)',ch.get('title',''))
   if m:boxes.append((f'w{wi:06}s{ci:04}',tuple(map(int,m.groups()))))
 if name.startswith('font01-'):
  split=name.split('-')[1];pdf=R/'font04/local/S1/font01'/f'{split}-2.pdf'
 else:
  kind,num=name.rsplit('-',1);folder={'p2':'P2','p2prime':'P2prime','p2pp':'P2pp'}[kind];pdf=R/'font04/local'/folder/f'sheet-{num}.pdf'
 with pikepdf.open(pdf) as d:page=np.asarray(pikepdf.PdfImage(d.pages[0].images['/Im0']).as_pil_image().convert('L'))
 captured=json.load(detail.open());over=[]
 for r in captured:
  s=r['source'];
  if s is None or not s['gray_halo']:continue
  w=s['width'];h=s['height'];x,y=map(int,s['bbox'][:2]);x0=x-4;y0=y-4;Hh=h+8;Ww=w+8;gray=np.full((Hh,Ww),255.,dtype=float);ix=max(0,x0);iy=max(0,y0);ex=min(page.shape[1],x0+Ww);ey=min(page.shape[0],y0+Hh);gray[iy-y0:ey-y0,ix-x0:ex-x0]=page[iy:ey,ix:ex];owned=np.pad(np.array(s['mask'],bool).reshape(h,w),4);dist=distance_transform_edt(~owned);color=np.dot(r['paper'],[.2126,.7152,.0722]);foreign=(abs(gray-color)>60)&~owned;fd=distance_transform_edt(~foreign) if foreign.any() else np.full(gray.shape,100.);newallow=(dist<=3)&(dist<fd); oldmask=owned[2:-2,2:-2];oldgray=gray[2:-2,2:-2];oldforeign=(abs(oldgray-color)>60)&~oldmask;oldfd=distance_transform_edt(~oldforeign) if oldforeign.any() else np.full(oldgray.shape,100.);olddist=distance_transform_edt(~oldmask);newallow[2:-2,2:-2]&=~((olddist<=1.5)&(olddist<oldfd));ys,xs=np.nonzero(newallow & (gray<245));hit=[]
  for oid,(bx,by,bx2,by2) in boxes:
   if oid==r['id'] or bx2<=x0 or bx>=x0+Ww or by2<=y0 or by>=y0+Hh:continue
   if np.any((xs+x0>=bx)&(xs+x0<bx2)&(ys+y0>=by)&(ys+y0<by2)):hit.append(oid)
  if hit:over.append({'id':r['id'],'other_ids':hit})
 out[name]={'baseline_planned':len(old_group),'halo_planned':len(new_group),'new_planned_ids':newly,'lost_planned_ids':lost,'new_valid_pairs':dict(counts),'new_support_overlaps_other_ocr_boxes':over,'baseline_pdf_sha256':hashlib.sha256((T/f'{name}.pdf').read_bytes()).hexdigest(),'capture_pdf_sha256':hashlib.sha256((D/f'{name}.pdf').read_bytes()).hexdigest()}
 print(name,len(newly),len(lost),dict(counts),'overlaps',len(over),flush=True)
(L/'halo-pairs.json').write_text(json.dumps(pairsout,indent=1)+'\n');(R/'acr06/c2b/halo-results.json').write_text(json.dumps(out,indent=2)+'\n')
