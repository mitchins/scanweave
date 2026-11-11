import json,pathlib,hashlib
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41c';P=R/'local/hvc41c/panels';rows=json.loads((E/'calibration-words.json').read_text());index=[]
for r in rows:
 if not r['control'].startswith('financial') or r['admitted']:continue
 n=int(r['control'][-2:]);im=Image.open(R/'local/ink33r/renders/financial'/f'{n:02}-source.png').convert('RGB');a,b,c,d=r['bbox'];pad=24;crop=im.crop((max(0,a-pad),max(0,b-pad),min(im.width,c+pad),min(im.height,d+pad)));crop.thumbnail((400,200));crop=crop.resize((crop.width*2,crop.height*2),Image.Resampling.NEAREST);f=P/f"rejected-{r['control']}-{r['word_index']:04}.png";crop.save(f);index.append({'control':r['control'],'word_index':r['word_index'],'ocr_label_unverified':r['text_ocr_unverified'],'reason':r['reasons'],'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(E/'rejected-panel-index.json').write_text(json.dumps(index,indent=2,ensure_ascii=False)+'\n')
