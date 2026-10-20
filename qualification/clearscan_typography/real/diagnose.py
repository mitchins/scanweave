"""Source-only diagnosis of real pages with no vectors; no pristine truth."""
from pathlib import Path
import json,re
import numpy as np
from PIL import Image
B=Path(__file__).resolve().parent;ROOT=B.parents[2];DATA=ROOT/'qualification/clearscan_competitive/real';rows=[]
for path in sorted((B/'final').glob('*.json')):
 if path.name in ('runs.json','metrics.json'):continue
 j=json.loads(path.read_text());name=path.stem
 if not name.startswith(('cord-','history-')):continue
 a=np.asarray(Image.open(DATA/(name+'.png')).convert('RGB'),dtype=float);h,w=a.shape[:2]
 corners=[np.median(a[y:y+6,x:x+6].reshape(-1,3),axis=0) for x,y in [(0,0),(w-6,0),(0,h-6),(w-6,h-6)]]
 paper=np.sort(corners,axis=0)[2];lum=lambda p:p@np.array([.2126,.7152,.0722]);gray=lum(a);pg=float(lum(paper));word=[]
 text=(DATA/(name+'.regions.hocr')).read_text()
 for m in re.finditer(r'<span[^>]*class=[\"\'][^\"\']*ocrx_word[^\"\']*[\"\'][^>]*>',text):
  bb=re.search(r'bbox (\d+) (\d+) (\d+) (\d+)',m[0])
  if not bb:continue
  x0,y0,x1,y1=map(int,bb.groups());g=gray[y0:y1,x0:x1]
  if g.size:word.append({'paper_p90':float(np.percentile(g,90)),'ink_p10':float(np.percentile(g,10)),'global_foreground_fraction':float((np.abs(g-pg)>60).mean())})
 obs=j['reconstruction']['observations'];valid=[o for o in obs if o['height']>=4 and o['ink_pixels']>=6]
 rows.append({'name':name,'vector_ink_px':j['coverage']['text_ink_px_vector'],'observations':len(obs),'observations_at_least_4px_6ink':len(valid),'global_corner_paper_rgb':paper.tolist(),'global_corner_paper_luma':pg,'ocr_words_measured':len(word),'median_word_paper_p90':float(np.median([x['paper_p90'] for x in word])) if word else None,'median_word_ink_p10':float(np.median([x['ink_p10'] for x in word])) if word else None,'median_word_global_foreground_fraction':float(np.median([x['global_foreground_fraction'] for x in word])) if word else None,'fallback_reasons':j['fallback_reasons']})
(B/'source-diagnosis.json').write_text(json.dumps({'method':__doc__,'pages':rows},indent=2))
for r in rows:
 if r['vector_ink_px']==0:print(r)
