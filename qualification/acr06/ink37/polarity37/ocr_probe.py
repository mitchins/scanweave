from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
import json,re,subprocess,pypdfium2 as pdfium
class H(HTMLParser):
 def __init__(self):super().__init__();self.depth=0;self.words=[];self.current=''
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if self.depth:self.depth+=1
  elif 'ocrx_word' in d.get('class','').split():self.depth=1;self.current=''
 def handle_data(self,s):
  if self.depth:self.current+=s.strip()
 def handle_endtag(self,tag):
  if self.depth:
   self.depth-=1
   if not self.depth:self.words.append(self.current)
root=Path('/data/coding/scanweave/qualification/acr06/local/ink37/gate37');rows=[]
for doc in ('historical','receipts'):
 path=root/f'{doc}-candidate.pdf';side=json.loads(Path(str(path)+'.json').read_text());pdf=pdfium.PdfDocument(path)
 for i,p in enumerate(side['pages']):
  if not side['conversion']['page_reports'][i]['polarity_raster_baseline']:continue
  parser=H();parser.feed(p['hocr']); expected=re.findall(r'[^\W_]+',' '.join(parser.words),re.UNICODE)
  page=pdf[i];tp=page.get_textpage();pdfwords=re.findall(r'[^\W_]+',tp.get_text_range(),re.UNICODE);tp.close();page.close()
  lost=Counter(expected)-Counter(pdfwords)
  pops=subprocess.run(['pdftotext','-f',str(i+1),'-l',str(i+1),str(path),'-'],capture_output=True,check=True).stdout.decode();popwords=re.findall(r'[^\W_]+',pops,re.UNICODE)
  rows.append({'document':doc,'page':i+1,'ocr_words':len(expected),'pdfium_words':len(pdfwords),'pdfium_missing':dict(lost),'poppler_words':len(popwords),'poppler_missing':dict(Counter(expected)-Counter(popwords))})
 pdf.close()
Path('/data/coding/scanweave/qualification/acr06/ink37/polarity37/ocr-probe.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
for row in rows:print(row)
