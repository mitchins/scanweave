#!/usr/bin/env python3
"""Text and PDF object measurements for pilot inputs. Never commits text."""
import collections,ctypes,hashlib,json,os,pathlib,re,subprocess,unicodedata
from html.parser import HTMLParser
import pikepdf,pypdfium2 as pdfium
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]; Q=P/'pilot'; ids=json.loads((P/'corpus.frozen.json').read_text())['pilot_6']; locks=json.loads((P/'sources.lock.json').read_text())['pages']; works={p['id']:p['work'] for p in json.loads((P/'corpus.frozen.json').read_text())['pages']}; runs=json.loads((Q/'results/runs.json').read_text()); lib=ctypes.CDLL(str(B/'pilot/edit.so')); lib.books01_edit.argtypes=[ctypes.POINTER(ctypes.c_uint32),ctypes.c_size_t,ctypes.POINTER(ctypes.c_uint32),ctypes.c_size_t];lib.books01_edit.restype=ctypes.c_int
class Hocr(HTMLParser):
 def __init__(self):super().__init__();self.active=0;self.words=[];self.buf=[]
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='span' and 'ocrx_word' in a.get('class','').split():self.active=1;self.buf=[]
  elif self.active:self.active+=1
 def handle_endtag(self,t):
  if self.active:
   self.active-=1
   if not self.active:self.words.append(''.join(self.buf))
 def handle_data(self,s):
  if self.active and s.strip():self.buf.append(s)
def gt(id):
 p=locks[id]; segments=id.split('/'); obj=json.loads((B/'gt'/works[id]/(segments[-1]+'.json')).read_text()); items=obj['lines'] or obj['regions']; return '\n'.join(x['text'] for x in items if x.get('text') is not None),obj
# Reading: Unicode NFKC, long-s folding, casefold, join line-break hyphen,
# then collapse whitespace. Diplomatic: retain script/case, collapse whitespace.
def norm(s,reading):
 s=s.replace('\r\n','\n').replace('\r','\n')
 if reading:s=unicodedata.normalize('NFKC',s.replace('ſ','s'));s=re.sub(r'-\s*\n\s*','',s).casefold()
 return re.sub(r'\s+',' ',s).strip()
def char_distance(a,b):
 x=(ctypes.c_uint32*len(a))(*map(ord,a)); y=(ctypes.c_uint32*len(b))(*map(ord,b));return lib.books01_edit(x,len(a),y,len(b))
def token_distance(a,b):
 prev=list(range(len(b)+1))
 for i,ref in enumerate(a,1):
  cur=[i]; pat=re.compile('^'+'.'.join(re.escape(part) for part in ref.split('\ufffd'))+'$') if '\ufffd' in ref else None
  for j,hyp in enumerate(b,1):cur.append(min(prev[j]+1,cur[-1]+1,prev[j-1]+(not (bool(pat.fullmatch(hyp)) if pat else ref==hyp))))
  prev=cur
 return prev[-1]
def score(a,b):
 out={}
 for reading,label in [(False,'diplomatic'),(True,'reading')]:
  x=norm(a,reading);y=norm(b,reading);known=len(x)-x.count('\ufffd'); xx=x.split();yy=y.split(); known_words=sum('\ufffd' not in w for w in xx); c=char_distance(x,y);w=token_distance(xx,yy); out[label]={'cer':c/known if known else None,'character_edits':c,'known_characters':known,'unknown_characters':x.count('\ufffd'),'wer':w/known_words if known_words else None,'word_edits':w,'known_words':known_words}
  counter=collections.Counter(x.replace('\ufffd','')); obs=collections.Counter(y);out[label]['bag_character_recall']=sum(min(v,obs[k]) for k,v in counter.items())/sum(counter.values()) if counter else None
 return out
def selftest():
 h=Hocr();h.feed("<span class='ocrx_word'>\n  <span class='ocrx_cinfo'>a</span>\n  <span class='ocrx_cinfo'>b</span>\n</span>");assert h.words==['ab']
 assert char_distance('a\ufffdc','axc')==0 and char_distance('abc','axc')==1
 assert token_distance(['a\ufffdc'],['axc'])==0 and token_distance(['abc'],['axc'])==1
selftest()
def objects(path):
 counts=collections.Counter(); sizes=collections.Counter()
 with pikepdf.open(path) as pdf:
  contents=set()
  for page in pdf.pages:
   a=page.obj.get('/Contents'); arr=list(a) if isinstance(a,pikepdf.Array) else [a] if a is not None else []
   contents.update(o.objgen for o in arr if isinstance(o,pikepdf.Stream))
  for obj in pdf.objects:
   if not isinstance(obj,pikepdf.Stream):continue
   size=len(obj.read_raw_bytes()); sub=str(obj.get('/Subtype','')); filt=str(obj.get('/Filter','none'))
   if sub=='/Image':category=('mask' if obj.get('/ImageMask',False) else 'image')+':'+filt
   elif obj.objgen in contents:category='page_content_stream'
   elif obj.get('/Length1') is not None:category='font_program'
   else:category='other_stream'
   counts[category]+=1;sizes[category]+=size
 total=path.stat().st_size;return {'stream_bytes_by_category':dict(sizes),'stream_count_by_category':dict(counts),'structure_xref_dictionary_and_unclassified_bytes':total-sum(sizes.values()),'file_bytes':total,'reconciles':sum(sizes.values())+(total-sum(sizes.values()))==total}
def extract(path):
 ret={}
 for mode in ['plain','raw']:
  cmd=['/usr/bin/pdftotext']+(['-raw'] if mode=='raw' else [])+[str(path),'-'];p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE);ret['poppler_'+mode]=p.stdout.decode('utf-8','replace') if p.returncode==0 else ''
 pdf=pdfium.PdfDocument(str(path));page=pdf[0];text=page.get_textpage();ret['pdfium']=text.get_text_range();return ret
result={}
for id in ids:
 row=runs[id]; key=id.split('/')[-1];p=locks[id]; ref,g=gt(id); h=Hocr();h.feed((B/'ocr-frozen'/key/('psm'+str(row['selected_psm'])+'-1.hocr')).read_text()); htxt=' '.join(h.words); baselines=score(ref,htxt); outputs={}
 for name in ['src','sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E']:
  path=pathlib.Path(row['rows'][name].get('path',B/'pilot/runs'/key/(name+'.pdf')))
  if not path.exists():outputs[name]={'status':'missing','dpi_confidence':p['dpi_evidence']['confidence']};continue
  texts=extract(path); entry={'status':'ok','size':objects(path),'size_ratio':path.stat().st_size/(B/p['source_pdf_path']).stat().st_size,'dpi_confidence':p['dpi_evidence']['confidence'],'source_type':p['source_type'],'extraction':{}}
  for engine,text in texts.items():
   n=norm(text,True); hnorm=norm(htxt,True); entry['extraction'][engine]={'scores':score(ref,text),'empty_text_layer':not bool(n),'control_characters':sum(unicodedata.category(c)=='Cc' and c not in '\r\n\t' for c in text),'private_use_characters':sum(unicodedata.category(c)=='Co' for c in text),'frozen_hocr_words_absent':sum(1 for w in set(hnorm.split()) if w and w not in set(n.split()))}
  entry['poppler_pdfium_reading_disagreement']={'character_edits':char_distance(norm(texts['poppler_plain'],True),norm(texts['pdfium'],True))};outputs[name]=entry
 result[id]={'dpi':p['resolved_dpi'],'dpi_confidence':p['dpi_evidence']['confidence'],'source_type':p['source_type'],'frozen_hocr_scores':baselines,'rows':outputs};print(id,flush=True)
(Q/'results/text-and-size.json').write_text(json.dumps(result,indent=2)+'\n')
