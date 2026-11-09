from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image
import numpy as np,json
root=Path('/data/coding/scanweave/qualification/acr06');loc=root/'local/ink37'; old=root/'local/ink33';idx=json.loads((root/'ink37/glyph-panel-index.json').read_text());pdf=pdfium.PdfDocument(loc/'historical-invisible-experiment.pdf');out=[]
for page in (2,5):
 p=pdf[page-1]; hidden=np.asarray(p.render(scale=300/72,rev_byteorder=True).to_pil().convert('RGB'));p.close(); source=np.asarray(Image.open(old/'renders/historical'/f'{page:02}-source.png').convert('RGB'))
 if hidden.shape!=source.shape: raise ValueError((hidden.shape,source.shape))
 l=lambda a:a[:,:,0]*.2126+a[:,:,1]*.7152+a[:,:,2]*.0722
 sl=l(source);hl=l(hidden)
 for n,x in enumerate(idx,1):
  if x['document']!='historical' or x['page']!=page:continue
  x0,y0,x1,y1=map(int,x['box']);s=sl[y0:y1,x0:x1];h=hl[y0:y1,x0:x1]
  out.append({'number':n,'page':page,'box':x['box'],'source_dark_pixels_l_under_100':int((s<100).sum()),'source_dark_pixels_brightened_20_or_more':int(((s<100)&(h-s>=20)).sum()),'all_changed_pixels':int(np.any(hidden[y0:y1,x0:x1]!=source[y0:y1,x0:x1],axis=2).sum())})
pdf.close();(root/'ink37/invisible-ink-loss.json').write_text(json.dumps(out,indent=2)+'\n')
