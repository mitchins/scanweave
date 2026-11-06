#!/usr/bin/env python3
"""Collect decision counts, byte identity and basic PDF/text checks."""
import collections, difflib, hashlib, json, shutil, subprocess
from pathlib import Path
import pikepdf, pypdfium2 as pdfium
root=Path('/data/coding/scanweave/qualification'); local=root/'acr06/local/donorfix'; output=root/'acr06/donorfix'; panels=json.loads((local/'panels/index.json').read_text()); words=collections.defaultdict(set)
for r in panels: words[(r['document'],r['page_index'])].add(r['word'])
sus=json.loads((root/'acr06/cp2/donor-mismatch.json').read_text()); counts={}; docs=[]
def embedded_fonts(path):
 seen={}
 with pikepdf.open(path) as pdf:
  for page in pdf.pages:
   for _,f in page.get('/Resources',{}).get('/Font',{}).items():
    try:
     face=f.DescendantFonts[0] if '/DescendantFonts' in f else f; desc=face.FontDescriptor
     for key in ('/FontFile','/FontFile2','/FontFile3'):
      if key in desc:
       stream=desc[key]; ident=tuple(stream.objgen); seen[ident]={'stored':int(stream.get('/Length',0)),'decoded':len(stream.read_bytes())}
    except (AttributeError,KeyError,ValueError,pikepdf.PdfError):continue
 return {'count':len(seen),'stored_bytes':sum(x['stored'] for x in seen.values()),'decoded_bytes':sum(x['decoded'] for x in seen.values())}
for cp in sorted((local/'candidate').glob('*.pdf')):
 name=cp.stem; mp=local/'main'/f'{name}.pdf'
 if not mp.exists(): mp=local/'baseline'/('single.pdf' if name=='single' else f'{name}-off.pdf')
 if not mp.exists(): continue
 ar=json.loads(Path(str(mp)+'.json').read_text()); br=json.loads(Path(str(cp)+'.json').read_text()); changed=[]; changed_substitutions=[]; tally=collections.Counter(); font=[]
 for pi,(a,b) in enumerate(zip(ar['conversion']['page_reports'],br['conversion']['page_reports'])):
  aa={o['symbol_id']:o for o in a['reconstruction']['occurrences']}; bb={o['symbol_id']:o for o in b['reconstruction']['occurrences']}; ao={o['symbol_id']:o['owner'] for o in a['occurrences']}; bo={o['symbol_id']:o['owner'] for o in b['occurrences']}
  for sid in aa.keys() & bb.keys():
   x,y=aa[sid],bb[sid]; tally['main:'+x['decision']]+=1; tally['candidate:'+y['decision']]+=1
   if (x['decision'],x.get('replacement_bbox_px'),x.get('prototype_id'))!=(y['decision'],y.get('replacement_bbox_px'),y.get('prototype_id')): changed_substitutions.append((pi,sid))
   if (x['decision'],x.get('replacement_bbox_px'),x.get('prototype_id'),ao.get(sid))!=(y['decision'],y.get('replacement_bbox_px'),y.get('prototype_id'),bo.get(sid)): changed.append((pi,sid))
  font.append([a.get('font_bytes'),b.get('font_bytes')])
 ident=hashlib.sha256(mp.read_bytes()).digest()==hashlib.sha256(cp.read_bytes()).digest(); checks={}
 if changed:
  try:
   with pikepdf.open(cp) as pdf: checks['pikepdf_check_pdf_syntax']=pdf.check_pdf_syntax()
  except Exception as e: checks['pikepdf_error']=str(e)
  texts=[]; text_cache={}
  for label,p in [('main',mp),('candidate',cp)]:
   text_cache[label]=[]; text_dir=local/'text'/name; text_dir.mkdir(parents=True,exist_ok=True)
   pdf=pdfium.PdfDocument(str(p)); extracted=[]
   for pi in range(len(pdf)):
    tp=pdf[pi].get_textpage(); text=tp.get_text_range(); pop=subprocess.run(['pdftotext','-f',str(pi+1),'-l',str(pi+1),str(p),'-'],capture_output=True,text=True)
    text_cache[label].append((text,pop.stdout)); (text_dir/f'{label}-p{pi}-pdfium.txt').write_text(text); (text_dir/f'{label}-p{pi}-poppler.txt').write_text(pop.stdout)
    extracted.append({'page_index':pi,'pdfium_sha256':hashlib.sha256(text.encode()).hexdigest(),'poppler_sha256':hashlib.sha256(pop.stdout.encode()).hexdigest(),'poppler_exit':pop.returncode,'word_search':{w:{'pdfium_native_search':tp.search(w,match_case=True).get_next() is not None,'pdfium_text_contains':w in text,'poppler_text_contains':w in pop.stdout} for w in words[(name,pi)]}})
   texts.append({'variant':label,'pages':extracted})
  checks['text']=texts
  checks['text_differences']=[]
  for pi,(a,b) in enumerate(zip(text_cache['main'],text_cache['candidate'])):
   for renderer,idx in [('pdfium',0),('poppler',1)]:
    if a[idx]!=b[idx]:
     changes=[{'operation':tag,'main':a[idx][i:j],'candidate':b[idx][k:l]} for tag,i,j,k,l in difflib.SequenceMatcher(None,a[idx],b[idx],autojunk=False).get_opcodes() if tag!='equal']
     checks['text_differences'].append({'page_index':pi,'renderer':renderer,'changes':changes})
 main_run=local/'main'/f'{name}.run.json'; baseline_run=local/'baseline'/'identity.json'; candidate_run=local/'candidate'/f'{name}.run.json'
 docs.append({'name':name,'main_bytes':mp.stat().st_size,'candidate_bytes':cp.stat().st_size,'main_runtime':json.loads(main_run.read_text())['seconds'] if main_run.exists() else next((r['seconds'] for r in json.loads(baseline_run.read_text()) if r['group']==name),None),'candidate_runtime':json.loads(candidate_run.read_text())['seconds'] if candidate_run.exists() else None,'font_bytes_per_page':font,'main_embedded_fonts':embedded_fonts(mp),'candidate_embedded_fonts':embedded_fonts(cp),'byte_identical':ident,'changed_occurrences':len(changed),'changed_substitutions':len(changed_substitutions),'pdf_change_without_occurrence_change':not ident and not changed,'pdf_change_without_substitution_change':not ident and not changed_substitutions,'counts':dict(tally),'checks':checks})
 if name in sus:
  aa={(pi,o['symbol_id']):o for pi,p in enumerate(ar['conversion']['page_reports']) for o in p['reconstruction']['occurrences']}; bb={(pi,o['symbol_id']):o for pi,p in enumerate(br['conversion']['page_reports']) for o in p['reconstruction']['occurrences']}
  rows=sus[name]['rows']; counts[name]={'suspects':len(rows),'rejected':sum(bb.get((r['page'],r['id']),{}).get('decision','').startswith('rejected_') for r in rows)}
(output/'metrics.json').write_text(json.dumps({'validator':'pikepdf.check_pdf_syntax','qpdf_available':Path('/tmp/scanweave-qpdf-deb/root/usr/bin/qpdf').exists(),'ots_available':Path('/tmp/scanweave-donorfix-ots/build/ots-sanitize').exists(),'suspects':counts,'documents':docs},indent=2)+'\n')
print('docs',len(docs),'changed',sum(d['changed_occurrences'] for d in docs),'suspects',counts)
