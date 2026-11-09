from pathlib import Path
import pikepdf,hashlib,numpy as np,json
from PIL import Image
base=Path('/data/coding/scanweave/qualification/acr06/local');rows=[]
for d,n in [('historical',2),('historical',5),('receipts',4)]:
 source=base/'ink33/renders'/d/f'{n:02d}-source.png'; arr=np.asarray(Image.open(source).convert('RGB')); pdf=pikepdf.open(base/'ink37/owner37'/f'{d}.pdf'); img=pdf.pages[n-1].Resources.XObject['/Im0']; data=img.read_bytes(); out=np.frombuffer(data,dtype=np.uint8).reshape(int(img.Height),int(img.Width),3); diff=out!=arr
 rows.append({'document':d,'page':n,'width':int(img.Width),'height':int(img.Height),'decoded_sha256':hashlib.sha256(data).hexdigest(),'source_rgb_sha256':hashlib.sha256(arr.tobytes()).hexdigest(),'differing_samples':int(diff.sum()),'differing_pixels':int(np.any(diff,axis=2).sum()),'encoded_bytes':len(img.read_raw_bytes())});pdf.close()
Path('/data/coding/scanweave/qualification/acr06/ink37/polarity37/owner-embedded.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:print(r)
