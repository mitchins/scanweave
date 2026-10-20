"""Bind the completed corpus to its matched product baseline; no inferred byte savings."""
from pathlib import Path
import json,hashlib,collections,csv,pikepdf
B=Path(__file__).resolve().parent;R=B.parents[1];groups=json.load(open(R/'qualification/pdf_packaging/groups.json'));measure=json.load(open(B/'measurements.json'));outline=json.load(open(B/'outline-inventory.json'));rows=[];changes=[];totals=collections.Counter();beforetotals=collections.Counter();checks=[]
sha=lambda data:hashlib.sha256(data).hexdigest()
def streams(q):return sorted(sha(o.read_bytes()) for o in q.objects if isinstance(o,pikepdf.Stream) and str(o.get('/Subtype'))!='/Image' and str(o.get('/Type')) not in ['/ObjStm','/XRef'])
def resources(path):
 q=pikepdf.open(path);images=sum(len(o.read_raw_bytes()) for o in q.objects if isinstance(o,pikepdf.Stream) and o.get('/Subtype')==pikepdf.Name.Image);fonts=sum(len(o.FontFile2.read_raw_bytes()) for o in q.objects if isinstance(o,pikepdf.Dictionary) and '/FontFile2' in o);content=sum(len(pg.Contents.read_raw_bytes()) for pg in q.pages);return {'pdf_bytes':path.stat().st_size,'raster_bytes':images,'font_bytes':fonts,'content_bytes':content,'overhead_bytes':path.stat().st_size-images-fonts-content}
for name,g in groups.items():
 old=B/'baseline-collections'/f'{name}.pdf';new=B/'collections'/f'{name}.pdf';a=pikepdf.open(old);z=pikepdf.open(new);assert streams(a)==streams(z),name
 report=json.load(open(str(new)+'.json'))['conversion'];baseline=json.load(open(str(old)+'.json'))['conversion'];assert len(a.pages)==len(z.pages)==len(g['members']);check={'document':name,'non_image_streams_identical':True,'pages':[]}
 for i,(pg,bpg,pr,bpr) in enumerate(zip(z.pages,a.pages,report['page_reports'],baseline['page_reports'])):
  assert pr['occurrences']==bpr['occurrences'];assert pr['patches']==bpr['patches'];assert list(pg.MediaBox)==list(bpg.MediaBox);assert pg.Contents.read_bytes()==bpg.Contents.read_bytes();seen=set()
  for j,p in enumerate(pr['patches']):
   x=pg.Resources.XObject.get('/Im'+str(j));y=bpg.Resources.XObject.get('/Im'+str(j));assert int(x.Width)==int(y.Width) and int(x.Height)==int(y.Height)
   changed=x.read_raw_bytes()!=y.read_raw_bytes();kind='paper' if p['compact_background'] else ('whole_page' if len(pr['patches'])==1 else 'native_exception')
   if changed:
    assert not any(o['owner'].startswith('visible') for o in pr['occurrences']);assert len(pr['patches'])==1 and not p['compact_background'];assert str(x.Filter)=='/DCTDecode';changes.append({'document':name,'page':i,'id':g['members'][i],'before_image_bytes':len(y.read_raw_bytes()),'after_image_bytes':len(x.read_raw_bytes()),'width':int(x.Width),'height':int(x.Height),'class':kind})
   if x.objgen not in seen:seen.add(x.objgen)
  check['pages'].append({'id':g['members'][i],'media_box_identical':True,'content_identical':True,'ownership_decisions_identical':True,'patches_identical':True})
 checks.append(check);before=resources(old);after=resources(new);beforetotals.update(before);totals.update(after);rows.append({'document':name,'pages':len(g['members']),'before':before,'after':after,'saved_bytes':before['pdf_bytes']-after['pdf_bytes'],'saved_percent':100*(1-after['pdf_bytes']/before['pdf_bytes'])})
 assert after['pdf_bytes']<=before['pdf_bytes']
 for directory in ['collections','baseline-collections']:
  inv=next(r for r in outline if r['pdf'].endswith('/'+directory+'/'+name+'.pdf'));check[directory+'_glyph_draws']=inv['visible_glyph_draws'];check[directory+'_unique_outlines']=inv['unique_painted_gids']
 assert check['collections_glyph_draws']==check['baseline-collections_glyph_draws'];assert check['collections_unique_outlines']==check['baseline-collections_unique_outlines']
(B/'paired-checks.json').write_text(json.dumps(checks,indent=2));(B/'changed-images.json').write_text(json.dumps(changes,indent=2));(B/'byte-accounting.json').write_text(json.dumps({'before':dict(beforetotals),'after':dict(totals),'saved':{k:beforetotals[k]-totals[k] for k in totals},'documents':rows},indent=2))
with (B/'scorecard.csv').open('w') as f:
 w=csv.DictWriter(f,['document','pages','before_pdf_bytes','after_pdf_bytes','saved_bytes','saved_percent']);w.writeheader()
 for r in rows:w.writerow({'document':r['document'],'pages':r['pages'],'before_pdf_bytes':r['before']['pdf_bytes'],'after_pdf_bytes':r['after']['pdf_bytes'],'saved_bytes':r['saved_bytes'],'saved_percent':r['saved_percent']})
manifest={'base':'99ec072','implementation':'5e6f4d9','files':[]}
for path in list((B/'collections').glob('*.pdf'))+list((B/'baseline-collections').glob('*.pdf'))+list((B/'final').glob('*.pdf'))+list((B/'q98').glob('*.pdf'))+list((B/'300').glob('*.pdf'))+list((B/'600').glob('*.pdf')):
 manifest['files'].append({'path':str(path.relative_to(R)),'bytes':path.stat().st_size,'sha256':sha(path.read_bytes()),'storage':'local; reproducible using recorded commands'})
(B/'run-manifest.json').write_text(json.dumps(manifest,indent=2));print('before',dict(beforetotals),'after',dict(totals));print('changed images',len(changes));print('docs',[(r['document'],r['saved_bytes']) for r in rows])
