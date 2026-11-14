#!/usr/bin/env python3
"""Line-aligned pilot OCR metrics. Reads only the six pilot PDFs and local GT."""
import ctypes,hashlib,json,math,pathlib,random,re,unicodedata
import numpy as np,pypdfium2 as pdfium
from lxml import html
from scipy.optimize import linear_sum_assignment
from scipy.stats import kendalltau
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[2];Q=P/'pilot'; c=json.loads((P/'corpus.frozen.json').read_text());ids=c['pilot_6'];works={p['id']:p['work'] for p in c['pages']};locks=json.loads((P/'sources.lock.json').read_text())['pages'];runs=json.loads((Q/'results/runs.json').read_text());document_scores=json.loads((Q/'results/text-and-size.json').read_text());geo=json.loads((Q/'results/phase1b/geometry.json').read_text())['pages'];lib=ctypes.CDLL(str(B/'pilot/edit.so'));lib.books01_edit.argtypes=[ctypes.POINTER(ctypes.c_uint32),ctypes.c_size_t,ctypes.POINTER(ctypes.c_uint32),ctypes.c_size_t];lib.books01_edit.restype=ctypes.c_int
ADOBE='Acrobat default OCR language (not matched); no Fraktur support; page straightened (deskew)'
def norm(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',re.sub(r'-\s*\n\s*','',s.replace('ſ','s'))).casefold()).strip()
def edit(a,b):
 x=(ctypes.c_uint32*len(a))(*map(ord,a));y=(ctypes.c_uint32*len(b))(*map(ord,b));return lib.books01_edit(x,len(a),y,len(b))
def word_edit(a,b):
 a=a.split();b=b.split();old=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  cur=[i];pat=re.compile('^'+'.'.join(re.escape(v) for v in x.split('\ufffd'))+'$') if '\ufffd' in x else None
  for j,y in enumerate(b,1):cur.append(min(old[j]+1,cur[-1]+1,old[j-1]+(not (bool(pat.fullmatch(y)) if pat else x==y))))
  old=cur
 return old[-1]
def bbox(poly):return [min(x for x,y in poly),min(y for x,y in poly),max(x for x,y in poly),max(y for x,y in poly)]
def gt(id):
 key=id.split('/')[-1];g=json.loads((B/'gt'/works[id]/(key+'.json')).read_text());lines=g['lines'] or [r for r in g['regions'] if r['kind']=='TextRegion' and r.get('text') and len(r['text'].strip().splitlines())==1];ranks={x['attributes'].get('regionRef'):i for i,x in enumerate(g['reading_order']) if x['attributes'].get('regionRef')}
 if ranks:lines=[x[1] for x in sorted(enumerate(lines),key=lambda z:(ranks.get(z[1].get('region_id',z[1].get('id')),len(ranks)),z[0]))]
 return [{'box':bbox(x['polygon']),'text':x.get('text') or ''} for x in lines if len(x['polygon'])>=3],g
def hocr(id,psm):
 key=id.split('/')[-1];root=html.parse(str(B/'ocr-frozen'/key/f'psm{psm}-1.hocr'));lines=[];words=[]
 for line in root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocr_line ")]'):
  m=re.search(r'\bbbox (\d+) (\d+) (\d+) (\d+)',line.get('title',''))
  if not m:continue
  ws=[]
  for w in line.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]'):
   text=''.join(t.strip() for t in w.itertext() if t.strip());ws.append(text);words.append(text)
  lines.append({'box':list(map(int,m.groups())),'text':' '.join(ws)})
 return lines,words
def transform_box(rect,g):
 angle=math.radians(g['rotation_degrees']);s=g['scale_x'];tx,ty=g['translation_px'];cc=math.cos(angle)*s;ss=math.sin(angle)*s
 pts=[(cc*x-ss*y+tx,ss*x+cc*y+ty) for x,y in [(rect[0],rect[1]),(rect[2],rect[1]),(rect[0],rect[3]),(rect[2],rect[3])]];return [min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)]
def pdf_lines(page,dpi,geom):
 tp=page.get_textpage();left,bottom,right,top=page.get_bbox();lines=[];chars=[];line_box=None;first=None
 def flush():
  nonlocal chars,line_box,first
  if line_box is not None and any(not ch.isspace() for ch in chars):lines.append({'box':line_box,'text':''.join(chars).strip(),'first':first})
  chars=[];line_box=None;first=None
 for i in range(tp.count_chars()):
  try:
   char=tp.get_text_range(i,1)
   if not char:continue
   if any(c in char for c in '\r\n'):flush();continue
   if char.isspace():
    if chars and not chars[-1].isspace():chars.append(' ')
    continue
   l,b,r,t=tp.get_charbox(i)
   if r<=l or t<=b:continue
   box=transform_box([(l-left)*dpi/72,(top-t)*dpi/72,(r-left)*dpi/72,(top-b)*dpi/72],geom);h=max(1,box[3]-box[1]);cy=(box[1]+box[3])/2
   if line_box is not None:
    lh=max(1,line_box[3]-line_box[1]);vertical=max(0,min(box[3],line_box[3])-max(box[1],line_box[1]));gap=box[0]-line_box[2]
    if (vertical<.12*min(h,lh) and abs(cy-(line_box[1]+line_box[3])/2)>.6*max(h,lh)) or gap>max(4*lh,40):flush()
   if line_box is None:line_box=box[:];first=i
   else:line_box=[min(line_box[0],box[0]),min(line_box[1],box[1]),max(line_box[2],box[2]),max(line_box[3],box[3])]
   chars.append(char)
  except Exception:continue
 flush();return lines,tp
def pair(reference,hyp):
 if not reference or not hyp:return []
 matrix=np.zeros((len(reference),len(hyp)),dtype=np.float32)
 for i,a in enumerate(reference):
  x0,y0,x1,y1=a['box'];a_area=max(1,(x1-x0)*(y1-y0))
  for j,b in enumerate(hyp):
   u0,v0,u1,v1=b['box'];inter=max(0,min(x1,u1)-max(x0,u0))*max(0,min(y1,v1)-max(y0,v0));union=a_area+max(1,(u1-u0)*(v1-v0))-inter;matrix[i,j]=inter/union
 i,j=linear_sum_assignment(-matrix);return [(int(a),int(b),float(matrix[a,b])) for a,b in zip(i,j) if matrix[a,b]>=.2]
def score(ref,hyp):
 matches=pair(ref,hyp);ce=we=known=knownwords=0
 for i,j,_ in matches:
  a=norm(ref[i]['text']);b=norm(hyp[j]['text']);ce+=edit(a,b);we+=word_edit(a,b);known+=len(a)-a.count('\ufffd');knownwords+=sum('\ufffd' not in x for x in a.split())
 missing=set(range(len(ref)))-{i for i,j,v in matches};allchars=sum(len(norm(x['text']).replace('\ufffd','')) for x in ref);misschars=sum(len(norm(ref[i]['text']).replace('\ufffd','')) for i in missing);ordered=sorted(matches);tau=float(kendalltau([x[0] for x in ordered],[x[1] for x in ordered]).statistic) if len(ordered)>=2 else None
 if tau is not None and not math.isfinite(tau):tau=None
 return {'gt_count':len(ref),'output_count':len(hyp),'matched_lines':len(matches),'missing_lines':len(missing),'missing_known_characters':misschars,'total_known_characters':allchars,'missing_character_share':misschars/allchars if allchars else None,'extra_lines':len(hyp)-len(matches),'matched_known_characters':known,'matched_character_edits':ce,'line_aligned_cer':ce/known if known else None,'matched_known_words':knownwords,'line_aligned_wer':we/knownwords if knownwords else None,'kendall_tau':tau,'kendall_pair_count':len(matches),'matching':'axis-aligned source-frame bounding-box IoU >= 0.2, one-to-one maximum weight'}
def same_gt_comparison(ref,frozen,pdf):
 a={i:j for i,j,_ in pair(ref,frozen)};b={i:j for i,j,_ in pair(ref,pdf)};common=sorted(set(a)&set(b));known=knownwords=ce_a=ce_b=we_a=we_b=0
 for i in common:
  truth=norm(ref[i]['text']);h=norm(frozen[a[i]]['text']);out=norm(pdf[b[i]]['text']);known+=len(truth)-truth.count('\ufffd');knownwords+=sum('\ufffd' not in w for w in truth.split());ce_a+=edit(truth,h);ce_b+=edit(truth,out);we_a+=word_edit(truth,h);we_b+=word_edit(truth,out)
 return {'shared_gt_lines':len(common),'known_characters':known,'known_words':knownwords,'frozen_cer':ce_a/known if known else None,'pdf_cer':ce_b/known if known else None,'frozen_wer':we_a/knownwords if knownwords else None,'pdf_wer':we_b/knownwords if knownwords else None,'method':'compare both OCR texts against exactly the same GT lines, matched independently by geometry'}
out={}
for id in ids:
 ref,g=gt(id);psm=runs[id]['selected_psm'];frozen,ocrwords=hocr(id,psm);allgt=' '.join(x['text'] for x in (g['lines'] or g['regions']) if x.get('text'));allwords=sorted(set(re.findall(r'\w{4,}',norm(allgt))));rnd=random.Random(int.from_bytes(hashlib.sha256(('books01-search-v1/'+id).encode()).digest()[:8],'big'));positive=rnd.sample(allwords,min(20,len(allwords)));recognized=set(re.findall(r'\w{4,}',norm(' '.join(ocrwords))));subset=[w for w in positive if w in recognized];result={'gt_type':'TextLine' if g['lines'] else 'single-line TextRegion proxy','gt_lines':len(ref),'known_gt_characters':sum(len(norm(v['text']).replace('\ufffd','')) for v in ref),'frozen_hocr':score(ref,frozen),'rows':{}}
 for row in ['src','sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E']:
  key=id.split('/')[-1];r=runs[id]['rows'][row];path=pathlib.Path(r.get('path',B/'pilot/runs'/key/(row+'.pdf')));geom=geo[id][row]['pdfium'][str(int(locks[id]['resolved_dpi']))]; entry={'dpi_confidence':locks[id]['dpi_evidence']['confidence'],'source_type':locks[id]['source_type'],'adobe_label':ADOBE if row=='adobe-E' else None,'document_level_scores':document_scores[id]['rows'][row].get('extraction',{}).get('pdfium',{}).get('scores')}
  if geom['status']!='accepted':entry.update(status='unavailable',reason='global registration unaccepted');result['rows'][row]=entry;continue
  try:
   doc=pdfium.PdfDocument(str(path));page=doc[0];lines,tp=pdf_lines(page,int(locks[id]['resolved_dpi']),geom);scores=score(ref,lines);hits=0
   for w in subset:
    search=tp.search(w,match_case=False);hits+=search.get_next() is not None;search.close()
   entry.update(status='ok',line_metrics=scores,matched_ocr_same_gt_lines=same_gt_comparison(ref,frozen,lines),recognized_word_search={'recognized_frozen_ocr_words_in_sample':len(subset),'pdf_search_hits':int(hits),'hit_rate':hits/len(subset) if subset else None,'semantics':'exact reading-normalized GT token present in selected frozen hOCR; case-insensitive literal PDFium search'})
  except Exception as e:entry.update(status='error',reason=str(e))
  result['rows'][row]=entry
 out[id]=result;print(id,flush=True)
(Q/'results/phase1b/line-ocr.json').write_text(json.dumps({'pages':out},indent=2,allow_nan=False)+'\n')
