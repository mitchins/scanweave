"""Restore the 15 existing licensed development originals without modifying prior work."""
from pathlib import Path
import json,urllib.request,hashlib
from PIL import Image
B=Path(__file__).resolve().parent;D=B/'originals'
def fetch():
 D.mkdir(exist_ok=True);frozen=json.loads((B/'attribution/downloads.json').read_text());cord={}
 if not all((D/f'cord-{i:02}.png').exists() for i in range(10)):
  data=json.load(urllib.request.urlopen('https://datasets-server.huggingface.co/first-rows?dataset=naver-clova-ix%2Fcord-v2&config=default&split=train',timeout=60));cord={f"cord-{r['row_idx']:02}.jpg":r['row']['image']['src'] for r in data['rows'][:10]}
 for row in frozen:
  name=row['name']
  if not (name.startswith('cord-') and name.endswith('.jpg') or name.startswith('history-') and name.endswith('.tif')):continue
  original=D/name;png=original.with_suffix('.png')
  if png.exists():continue
  data=urllib.request.urlopen(cord.get(name,row['url']),timeout=90).read();assert hashlib.sha256(data).hexdigest()==row['sha256'],name;original.write_bytes(data);Image.open(original).convert('RGB').save(png)
 (D/'downloads.json').write_text(json.dumps(frozen,indent=2))
if __name__=='__main__':fetch()
