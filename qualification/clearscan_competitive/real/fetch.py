import json,urllib.request,hashlib,concurrent.futures
from pathlib import Path
B=Path(__file__).resolve().parent
jobs=[]
# Signed asset URLs expire. Resolve the stable public training split again.
endpoint='https://datasets-server.huggingface.co/first-rows?dataset=naver-clova-ix%2Fcord-v2&config=default&split=train'
response=json.loads(urllib.request.urlopen(endpoint,timeout=60).read())
rows=response['rows'][:10]
(B/'cord_rows.json').write_text(json.dumps({'rows':rows},indent=2))
for r in rows:
 i=r['row_idx'];jobs.append((f'cord-{i:02}.jpg',r['row']['image']['src']));(B/f'cord-{i:02}.truth.json').write_text(r['row']['ground_truth'])
rev='379f597a8dada882e6c2e4f509dbf9fdf2ebffa1'
frozen=json.loads((B/'downloads.json').read_text())
expected={r['name']:r.get('sha256') for r in frozen}
jobs.extend((r['name'],r['url']) for r in frozen if r['name'].startswith('history-'))
jobs.append(('ocrd-LICENSE.md',f'https://raw.githubusercontent.com/OCR-D/gt_structure_text/{rev}/LICENSE.md'))
def get(job):
 name,url=job
 try:
  data=urllib.request.urlopen(url,timeout=60).read();digest=hashlib.sha256(data).hexdigest()
  if expected.get(name) and digest!=expected[name]:raise ValueError(f'frozen asset hash mismatch: {name}')
  (B/name).write_bytes(data);return {'name':name,'url':url,'sha256':digest,'bytes':len(data)}
 except Exception as e:return {'name':name,'url':url,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:res=list(ex.map(get,jobs))
(B/'downloads.json').write_text(json.dumps(res,indent=2));print([(r['name'],r.get('bytes',r.get('error'))) for r in res])
from PIL import Image
for r in res:
 if r['name'].endswith(('.jpg','.tif')) and 'error' not in r:
  Image.open(B/r['name']).convert('RGB').save((B/r['name']).with_suffix('.png'))
