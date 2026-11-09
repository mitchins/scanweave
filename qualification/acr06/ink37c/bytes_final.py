from pathlib import Path
import pikepdf,json,hashlib
base=Path('/data/coding/scanweave/qualification/acr06/local');rows=[];docs=[]
for doc in ('historical','financial','mixed','receipts','forms'):
 paths=[base/'ink37/polarity37'/f'{doc}-main.pdf',base/'ink37/owner37'/f'{doc}.pdf',base/'ink37c/detail-gate'/f'{doc}.pdf']
 if not all(p.exists() for p in paths):continue
 pdfs=[pikepdf.open(p) for p in paths]
 docs.append({'document':doc,'sizes':[p.stat().st_size for p in paths],'sha256':[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]})
 for i,pages in enumerate(zip(*(p.pages for p in pdfs))):
  data=[]
  for p in pages:
   images=[]
   for obj in p.Resources.get('/XObject',{}).values():
    if str(obj.get('/Subtype'))=='/Image':images.append({'encoded_bytes':len(obj.read_raw_bytes()),'filter':str(obj.get('/Filter')),'width':int(obj.get('/Width')),'height':int(obj.get('/Height'))})
   data.append(images)
  rows.append({'document':doc,'page':i+1,'images':data,'totals':[sum(x['encoded_bytes'] for x in image) for image in data]})
 for p in pdfs:p.close()
Path('/data/coding/scanweave/qualification/acr06/ink37c/bytes-final.json').write_text(json.dumps({'documents':docs,'pages':rows},indent=2)+'\n')
for x in docs:print(x['document'],x['sizes'],flush=True)
