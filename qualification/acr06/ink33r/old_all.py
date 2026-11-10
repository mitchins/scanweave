#!/usr/bin/env python3
"""Reassemble all-line old results from the frozen #33 per-character records."""
import json,collections,pathlib,sys
import numpy as np
from PIL import Image
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from measure import summarize,ssim
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');old=R/'local/ink33';new=R/'ink33r';docs=('historical','financial','mixed','receipts','forms')
for doc in docs:
 for mp in sorted((old/'maps'/doc).glob('*.json')):
  page=int(mp.stem);dat=json.loads(mp.read_text());chars=[x for f in sorted((old/'raw-chars').glob(f'chars-{doc}-{page:02d}-*.json')) for x in json.loads(f.read_text())];byline=collections.defaultdict(list)
  for c in chars:byline[c['line']].append(c)
  imgs={n:np.asarray(Image.open(old/'renders'/doc/f'{page:02d}-{n}.png').convert('RGB')) for n in ('source','scanweave','adobe')};out=[]
  for line in dat['lines']:
   lc=byline[line['id']]
   if not lc:continue
   vals=summarize(lc)
   for name in imgs:vals[name]['ssim']=ssim(imgs['source'],imgs[name],line['box'])
   words=[]
   for w in line['words']:
    wc=[c for c in lc if c['word']==w['id']]
    if wc:words.append({'id':w['id'],'n_vector':sum(c['class']=='vector' for c in wc),'n_raster':sum(c['class']=='raster' for c in wc),'metrics':summarize(wc)})
   out.append({'id':line['id'],'box':line['box'],'n_vector':sum(c['class']=='vector' for c in lc),'n_raster':sum(c['class']=='raster' for c in lc),'metrics':vals,'words':words})
  (new/f'old-all-lines-{doc}-{page:02d}.json').write_text(json.dumps({'page':page,'lines':out},separators=(',',':'))+'\n');print(doc,page,flush=True)
print('COMPLETE',flush=True)
