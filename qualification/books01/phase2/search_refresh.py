#!/usr/bin/env python3
"""Reapply unchanged pilot word sampling to completed Phase 2 text layers."""
import hashlib,json,pathlib,random,re,unicodedata
from lxml import html
import pypdfium2 as pdfium
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];D=B/'phase2';corpus=json.loads((P/'corpus.frozen.json').read_text());ids=[x for x in corpus['pages'] if x['split']=='dev'];pilot=set(corpus['pilot_6']);
def norm(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',re.sub(r'-\s*\n\s*','',s.replace('ſ','s'))).casefold()).strip()
for p in ids:
 id=p['id'];key=id.split('/')[-1];h=D/'runs'/key/'selected.hocr'
 if not h.exists():continue
 g=json.loads((B/'gt'/p['work']/(key+'.json')).read_text());gt=' '.join(x['text'] for x in (g['lines'] or g['regions']) if x.get('text'));allwords=sorted(set(re.findall(r'\w{4,}',norm(gt))));rnd=random.Random(int.from_bytes(hashlib.sha256(('books01-search-v1/'+id).encode()).digest()[:8],'big'));pos=rnd.sample(allwords,min(20,len(allwords)));root=html.parse(str(h));words=[]
 for w in root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]'):words.append(''.join(t.strip() for t in w.itertext() if t.strip()))
 recognized=set(re.findall(r'\w{4,}',norm(' '.join(words))));subset=[w for w in pos if w in recognized];run=json.loads((D/'runs'/key/'runs.json').read_text())
 for row in ['src','sw-E','mrc-M','ocrmypdf-E','adobe-E']:
  f=D/'metrics'/key/(row+'.json')
  if not f.exists():continue
  result=json.loads(f.read_text())
  if result.get('status')!='ok':continue
  path=B/'runs'/('adobe' if id in pilot else 'adobe-p2')/(key+'.adobe.pdf') if row=='adobe-E' else pathlib.Path(run['rows'][row]['path']);doc=pdfium.PdfDocument(str(path));tp=doc[0].get_textpage();tokens=re.findall(r'[^\W_]+(?:[\u0300-\u036f]+)?',tp.get_text_range(),re.UNICODE)
  def search(w):
   try:q=tp.search(w,match_case=False);found=q.get_next() is not None;q.close();return found
   except Exception:return False
  hits=alt=0
  for w in subset:
   hit=search(w);hits+=hit;alt+=bool(hit or any(norm(t)==w and search(t) for t in tokens))
  result['search']={'recognized_words':len(subset),'literal_hits':hits,'diplomatic_variant_hits':alt,'variant':'literal or a text-layer token with identical reading-normalised form','limitation':'long-s normalised query may fail literal search'};f.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
print('search sampling refreshed')
