#!/usr/bin/env python3
"""Audit original conditional literal-search misses. Text-bearing evidence stays local."""
import collections,difflib,hashlib,json,pathlib,random,re
from lxml import html
B=pathlib.Path('/data/coding/scanweave/work/books01'); Q=pathlib.Path(__file__).resolve().parents[1]; p=Q/'phase1b/line_ocr.py'; n={'__file__':str(p)};exec(compile(p.read_text().split('out={}\nfor id in ids:')[0],str(p),'exec'),n)
norm=n['norm']; pdfium=n['pdfium']; edit=n['edit']; results={};private=[]
def search(tp,query):
 try:
  s=tp.search(query,match_case=False);ok=s.get_next() is not None;s.close();return ok
 except Exception:return False
for id in n['ids']:
 gt,g=n['gt'](id); allgt=' '.join(x['text'] for x in (g['lines'] or g['regions']) if x.get('text')); allwords=sorted(set(re.findall(r'\w{4,}',norm(allgt))));rnd=random.Random(int.from_bytes(hashlib.sha256(('books01-search-v1/'+id).encode()).digest()[:8],'big'));positive=rnd.sample(allwords,min(20,len(allwords))); frozen,words=n['hocr'](id,n['runs'][id]['selected_psm']);recognized=set(re.findall(r'\w{4,}',norm(' '.join(words))));subset=[w for w in positive if w in recognized];results[id]={}
 for row in ['src','sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E']:
  r=n['runs'][id]['rows'][row];path=pathlib.Path(r.get('path',B/'pilot/runs'/id.split('/')[-1]/(row+'.pdf')));doc=pdfium.PdfDocument(str(path));page=doc[0];tp=page.get_textpage();text=tp.get_text_range();tokens=list(re.finditer(r'[^\W_]+(?:[\u0300-\u036f]+)?',text,re.UNICODE));counts=collections.Counter();matches=[]
  for ix,q in enumerate(subset):
   if search(tp,q):continue
   mid=f'{id.split("/")[-1]}:{row}:{ix:02d}'; candidates=[]
   for t in tokens:
    raw=t.group();normalized=norm(raw)
    if normalized==q:candidates.append((0,raw,t.start(),'exact_normalised_token'))
    elif abs(len(normalized)-len(q))<=max(2,len(q)//3):candidates.append((edit(q,normalized),raw,t.start(),'token'))
   for t,u in zip(tokens,tokens[1:]):
    between=text[t.end():u.start()];raw=t.group()+between+u.group();joined=re.sub(r'[\s\-\u00ad]+','',norm(raw))
    if joined==q:candidates.append((0,raw,t.start(),'line_hyphen' if '\n' in between or '\r' in between or '-' in between or '\u00ad' in between else 'split'))
   candidates.sort(key=lambda x:(x[0],x[3]!='exact_normalised_token',len(x[1])));nearest=candidates[0] if candidates else (len(q),'',-1,'none');distance,raw,pos,kind=nearest;nearest_hit=bool(raw and search(tp,raw));diplomatic=nearest_hit if kind=='exact_normalised_token' else None;
   if kind=='exact_normalised_token' and raw.casefold()!=q.casefold() and diplomatic:cause='query-normalisation'
   elif kind=='line_hyphen':cause='hyphenation/line-break'
   elif kind=='split':cause='word-split/merge'
   elif kind=='exact_normalised_token' and diplomatic:cause='query-normalisation'
   elif kind=='exact_normalised_token':cause='other'
   elif not text.strip():cause='other'
   elif row in ('ocrmypdf-E','adobe-E'):cause='other'
   else:cause='text-layer-loss'
   note={'other':('empty text layer' if not text.strip() else 'independent OCR output differs; recognition versus PDF text-layer loss cannot be distinguished from this evidence' if row in ('ocrmypdf-E','adobe-E') and kind!='exact_normalised_token' else 'normalised token exists but PDFium literal diplomatic search also failed')}.get(cause)
   counts[cause]+=1;rec={'id':mid,'page':id,'row':row,'sample_index':ix,'cause':cause,'nearest_normalised_character_edits':distance,'nearest_kind':kind,'diplomatic_search_hit':diplomatic,'nearest_literal_search_hit':nearest_hit,'pdfium_match_options':'case insensitive, literal','gt_occurrences':len(re.findall(r'(?<!\w)'+re.escape(q)+r'(?!\w)',norm(allgt))),'frozen_occurrences':len(re.findall(r'(?<!\w)'+re.escape(q)+r'(?!\w)',norm(' '.join(words)))),'note':note};matches.append(rec);private.append(dict(rec,query=q,nearest_text_layer_string=raw,nearest_offset=pos))
  old=n['json'].loads((Q/'results/phase1b/line-ocr.json').read_text())['pages'][id]['rows'][row]['recognized_word_search'];assert len(subset)==old['recognized_frozen_ocr_words_in_sample'] and len(subset)-len(matches)==old['pdf_search_hits'],(id,row,len(subset),len(matches),old)
  results[id][row]={'sample_size':len(subset),'hits':len(subset)-len(matches),'misses':len(matches),'causes':dict(counts),'details':matches,'diplomatic_variant_hits':len(subset)-len(matches)+sum(m['diplomatic_search_hit'] is True for m in matches)}
(B/'pilot/phase1c/search-evidence.json').write_text(json.dumps({'warning':'GT and OCR text: local only','misses':private},ensure_ascii=False,indent=2)+'\n');(Q/'results/phase1c/search-audit.json').write_text(json.dumps({'definition':'Original frozen-recognised sampled GT tokens; case-insensitive literal PDFium search, unchanged','caveat':'Closest normalized text is evidence, not proof of occurrence identity; a repeated query can refer to different GT occurrences. Counts use exhaustive actual misses.','pages':results},indent=2)+'\n');print('audited',len(private),'misses');print(collections.Counter(x['cause'] for x in private))
