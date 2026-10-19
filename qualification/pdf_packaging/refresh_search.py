"""Native search probes with correctly joined Tesseract character spans.
CORD annotation queries are separate from Tesseract-reference probes.
"""
import json,re,importlib.util
from pathlib import Path
from lxml import etree
import pypdfium2 as pdfium
B=Path(__file__).resolve().parent;R=B.parents[1];D=B/'real'
def probes(id):
 doc=etree.parse(str(D/'archive'/(id+'.hocr')));words=[]
 for e in doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]'):
  chars=e.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_cinfo ")]')
  word=''.join(''.join(c.itertext()) for c in chars) if chars else ''.join(e.itertext())
  word=word.strip()
  if re.fullmatch(r'[A-Za-z0-9.,-]{3,}',word):words.append(word)
 unique=list(dict.fromkeys(words));numbers=[w for w in unique if sum(c.isdigit() for c in w)>=3]
 return list(dict.fromkeys(unique[:2]+numbers[-1:]))[:3]
def search(path,index,queries):
 doc=pdfium.PdfDocument(str(path));tp=doc[index].get_textpage();return [{'text':q,'found':tp.search(q).get_next() is not None} for q in queries]
real=json.loads((B/'real-measurements.json').read_text())
for index,row in enumerate(real):
 id=row['id'];queries=probes(id)
 for arm,data in row['arms'].items():
  path=R/data['pdf'] if 'pdf' in data else D/arm/(id+'.pdf')
  if arm=='source':path=D/'input'/(id+'.pdf')
  if arm=='adobe':path=D/('adobe-all.pdf' if index<30 else 'adobe-forms.pdf')
  data['queries']=search(path,data['source_page_index'],queries)
 (D/'measurement'/(id+'.json')).write_text(json.dumps(row,indent=2))
(B/'real-measurements.json').write_text(json.dumps(real,indent=2))
groups=json.loads((B/'group-measurements.json').read_text());byid={r['id']:r for r in real}
for group in groups:
 if group.get('missing'):continue
 path=B/'groups'/f"{group['group']}-{group['arm']}.pdf"
 for i,page in enumerate(group['pages']):page['queries']=search(path,i,probes(page['id']))
 (B/'groups'/f"{group['group']}-{group['arm']}.measure.json").write_text(json.dumps(group,indent=2))
(B/'group-measurements.json').write_text(json.dumps(groups,indent=2))
# Known receipt labels are not supplied to any converter or the source OCR.
known=[]
for i in range(10):
 id=f'cord-{i:02}';truth=json.loads((R/'qualification/clearscan_competitive/real'/(id+'.truth.json')).read_text());numeric=[]
 for line in truth.get('valid_line',[]):
  for w in line['words']:
   text=w['text']
   if len(text)>=4 and sum(c.isdigit() for c in text)>=3:numeric.append(text)
 queries=list(dict.fromkeys(numeric))[:5]
 for arm in ['scanweave','adobe','ocrmypdf1','ocrmypdf3','archive']:
  path=B/'groups'/f'receipts-{arm}.pdf';known.append({'id':id,'arm':arm,'queries':search(path,i,queries),'reference':'CORD v2 training annotation; exact punctuation retained; OCR errors separate from visual reconstruction'})
(B/'cord-known-numeric-search.json').write_text(json.dumps(known,indent=2))
print('native probes refreshed; known CORD numeric queries',sum(len(r['queries']) for r in known))
