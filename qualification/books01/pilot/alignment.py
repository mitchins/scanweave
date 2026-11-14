#!/usr/bin/env python3
"""Dev pilot GT and frozen OCR geometry checks, with FineBooks line proxies."""
import json,pathlib,re,statistics
from html.parser import HTMLParser
import numpy as np
from PIL import Image,ImageDraw
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot'; corpus=json.loads((P/'corpus.frozen.json').read_text()); ids=corpus['pilot_6']; works={p['id']:p['work'] for p in corpus['pages']}; runs=json.loads((Q/'results/runs.json').read_text()); lock=json.loads((P/'sources.lock.json').read_text())['pages']
class Boxes(HTMLParser):
 def __init__(self):super().__init__();self.boxes=[]
 def handle_starttag(self,t,attrs):
  a=dict(attrs);m=re.search(r'\bbbox (\d+) (\d+) (\d+) (\d+)',a.get('title',''))
  if 'ocrx_word' in a.get('class','').split() and m:self.boxes.append(tuple(map(int,m.groups())))
out={}
for id in ids:
 key=id.split('/')[-1]; g=json.loads((B/'gt'/works[id]/(key+'.json')).read_text()); im=Image.open(B/'ocr-frozen'/key/'page.png').convert('RGB'); gray=np.asarray(im.convert('L')); full=Image.new('1',im.size);draw=ImageDraw.Draw(full); overlay=im.copy(); d=ImageDraw.Draw(overlay); lines=g['lines'];proxy=False
 if not lines:
  proxy=True; lines=[r for r in g['regions'] if r['kind']=='TextRegion' and r['text'] and len(r['text'].strip().splitlines())==1]
 ratios=[]
 for line in lines:
  points=[tuple(p) for p in line['polygon']]
  if len(points)<3:continue
  mask=Image.new('1',im.size); ImageDraw.Draw(mask).polygon(points,fill=1);mask=np.asarray(mask,dtype=bool); ratios.append(float((gray[mask]<128).mean()) if mask.any() else 0);draw.polygon(points,fill=1);d.line(points+[points[0]],fill='red',width=3)
 psm=runs[id]['selected_psm'];h=Boxes();h.feed((B/'ocr-frozen'/key/f'psm{psm}-1.hocr').read_text());arr=np.asarray(full,dtype=bool); inside=0
 for x0,y0,x1,y1 in h.boxes:
  x=(x0+x1)//2;y=(y0+y1)//2
  inside+=0<=x<im.width and 0<=y<im.height and arr[y,x]
 out[id]={'type':'single-line TextRegion proxy' if proxy else 'TextLine','line_or_proxy_count':len(lines),'known_characters_covered':sum(len((x.get('text') or '').replace('\ufffd','')) for x in lines),'nonempty_regions_total':sum(bool((r.get('text') or '').strip()) for r in g['regions'] if r['kind']=='TextRegion'),'median_polygon_ink_fraction':statistics.median(ratios) if ratios else None,'polygon_ink_threshold_gray_below':128,'ocr_word_count':len(h.boxes),'ocr_word_centres_in_line_polygon':int(inside),'ocr_word_centre_fraction':float(inside/len(h.boxes)) if h.boxes else None,'dpi_confidence':lock[id]['dpi_evidence']['confidence']}
 dst=B/'qa/pilot-alignment'/(key+'.png');dst.parent.mkdir(parents=True,exist_ok=True);overlay.save(dst)
(Q/'results/alignment.json').write_text(json.dumps(out,indent=2)+'\n')
