#!/usr/bin/env python3
"""Join hOCR line baseline metadata to instrumented target and emitted bounds."""
import json,re
from html.parser import HTMLParser
from pathlib import Path
q=Path('/data/coding/scanweave/qualification/acr06');traces=json.loads((q/'donorfix/instrumented-traces.json').read_text());cache={}
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.stack=[];self.words={};self.word_boxes=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);cls=a.get('class','');line=next((x for x in reversed(self.stack) if x),None)
  if 'ocr_line' in cls:line=a.get('title','')
  if 'ocrx_word' in cls and line:
   self.words[a.get('id')]=line; self.word_boxes.append((a.get('id'),a.get('title',''),line))
  self.stack.append(line if 'ocr_line' in cls else None)
 def handle_endtag(self,tag):
  if self.stack:self.stack.pop()
def value(title,key,n=1):
 m=re.search(r'(?:^|;\s*)'+re.escape(key)+r'\s+'+r'\s+'.join([r'(-?\d+(?:\.\d+)?)']*n),title)
 return [float(x) for x in m.groups()] if m else None
out=[]
for t in traces:
 doc=t['document'];pi=t['page_index'];key=(doc,pi)
 if key not in cache:
  f=q/'local/donorfix/baseline'/('single.pdf.json' if doc=='single' else doc+'-off.pdf.json');r=json.loads(f.read_text());p=Parser();p.feed(r['pages'][pi]['hocr']);cache[key]=(p.words,p.word_boxes)
 word=int(t['id'][1:7])+1; words,word_boxes=cache[key]; word_id=f'word_1_{word}'; matches=[(wid,wt,lt) for wid,wt,lt in word_boxes if wid==word_id]; b=t['ink'];cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
 def contains(item):
  bb=value(item[1],'bbox',4);return bool(bb and bb[0]<=cx<=bb[2] and bb[1]<=cy<=bb[3])
 if not matches or not contains(matches[0]): matches=[item for item in word_boxes if contains(item)]
 title=matches[0][2] if len(matches)==1 else None
 box=value(title,'bbox',4) if title else None;base=value(title,'baseline',2) if title else None;size=value(title,'x_size') if title else None;desc=value(title,'x_descenders') if title else None;asc=value(title,'x_ascenders') if title else None
 line_baseline=None;xh=None
 if box and base:
  x=(t['ink'][0]+t['ink'][2])/2;line_baseline=box[3]+base[1]+base[0]*(x-box[0])
 if size and asc and desc:xh=size[0]-asc[0]-desc[0]
 emitted=t.get('emitted_outline');e=emitted['outline_bbox_px'] if emitted else None
 out.append({'document':doc,'page_index':pi,'id':t['id'],'hocr_line_title':title,'estimated_line_baseline_y':line_baseline,'estimated_x_height_px':xh,'observed_bottom_from_line_baseline':t['ink'][3]-line_baseline if line_baseline is not None else None,'emitted_bottom_from_line_baseline':e[3]-line_baseline if e and line_baseline is not None else None,'observed_top_from_x_height_line':t['ink'][1]-(line_baseline-xh) if line_baseline is not None and xh is not None else None,'emitted_top_from_x_height_line':e[1]-(line_baseline-xh) if e and line_baseline is not None and xh is not None else None})
(q/'donorfix/line-metrics.json').write_text(json.dumps(out,indent=2)+'\n');print('lines',len(out),'with baseline',sum(x['estimated_line_baseline_y'] is not None for x in out),'with x-height',sum(x['estimated_x_height_px'] is not None for x in out))
