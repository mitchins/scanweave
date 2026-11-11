import pathlib,json,io,hashlib
import numpy as np,pikepdf
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41c';L=R/'local';P=L/'hvc41c/panels';P.mkdir(parents=True,exist_ok=True);rows=json.loads((E/'calibration-words.json').read_text());idx=[]
for name in ('white','financial-01','financial-02'):
 if name=='white':
  d=pikepdf.open(L/'ink37/controls/white.pdf');o=next(o for o in d.pages[0].Resources.XObject.values() if str(o.get('/Subtype'))=='/Image');src=Image.open(io.BytesIO(o.read_raw_bytes())).convert('RGB');d.close()
 else:src=Image.open(L/'ink33r/renders/financial'/f"{int(name[-2:]):02}-source.png").convert('RGB')
 selected=[x for x in rows if x['control']==name and x['admitted']][:5]
 for k,x in enumerate(selected):
  a,b,c,d=x['bbox'];pad=12;crop=src.crop((max(0,a-pad),max(0,b-pad),min(src.width,c+pad),min(src.height,d+pad)));read=crop.resize((max(1,round(crop.width*.32)),max(1,round(crop.height*.32))),Image.Resampling.LANCZOS);big=read.resize((read.width*4,read.height*4),Image.Resampling.NEAREST);sheet=Image.new('RGB',(max(big.width,read.width),big.height+read.height+40),'white');draw=ImageDraw.Draw(sheet);draw.text((3,2),'source; OCR hypothesis: '+x['text_ocr_unverified'],fill='black');sheet.paste(read,(0,20));sheet.paste(big,(0,30+read.height));f=P/f'admission-{name}-{k+1:02}.png';sheet.save(f);idx.append({'control':name,'word_index':x['word_index'],'text_ocr_unverified':x['text_ocr_unverified'],'bbox':x['bbox'],'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(E/'admission-panel-index.json').write_text(json.dumps(idx,indent=2,ensure_ascii=False)+'\n');print('panels',len(idx))
