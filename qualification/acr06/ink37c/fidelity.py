from pathlib import Path
from PIL import Image
import io,json,numpy as np,xml.etree.ElementTree as ET,re
from skimage.metrics import structural_similarity
base=Path('/data/coding/scanweave/qualification/acr06'); rows=[]
for doc,n in [('historical',2),('historical',5),('receipts',4)]:
 p=base/'local/ink33/renders'/doc/f'{n:02d}-source.png';im=Image.open(p).convert('RGB');w,h=im.size; small=im.resize((round(w*2/3),round(h*2/3)),Image.Resampling.LANCZOS);b=io.BytesIO();small.save(b,'JPEG',quality=85,subsampling=2,optimize=True,progressive=True);q=Image.open(base/'local/ink37c/renders/pdfium'/f'{doc}-{n:02d}-300.png').convert('RGB');a=np.asarray(im);z=np.asarray(q);lum=lambda a: a[:,:,0]*.2126+a[:,:,1]*.7152+a[:,:,2]*.0722
 src=lum(a);can=lum(z);mask=np.zeros((h,w),bool);side=json.load(open(base/'local/ink37/owner37'/f'{doc}.pdf.json'));root=ET.fromstring(side['pages'][n-1]['hocr'])
 for x in root.iter():
  if 'ocrx_word' not in x.attrib.get('class','').split():continue
  m=re.search(r'bbox (\d+) (\d+) (\d+) (\d+)',x.attrib.get('title',''))
  if m:
   x0,y0,x1,y1=map(int,m.groups());mask[max(0,y0):min(h,y1),max(0,x0):min(w,x1)]=True
 ink=mask & (src<128); rows.append({'doc':doc,'page':n,'simulation_bytes':len(b.getvalue()),'mae':float(np.abs(a.astype('int16')-z.astype('int16')).mean()),'ssim':float(structural_similarity(np.asarray(im.convert('L')),np.asarray(q.convert('L')),data_range=255)),'ink_pixels':int(ink.sum()),'ink_recall':float((can[ink]<160).mean())});print(rows[-1],flush=True)
(base/'ink37c/fidelity.json').write_text(json.dumps(rows,indent=2)+'\n')
