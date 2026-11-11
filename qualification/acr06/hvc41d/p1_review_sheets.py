import json,pathlib,hashlib
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41d';L=R/'local/hvc41d';r=json.loads((E/'p1-preflight-ledger.json').read_text());r=[x for x in r if x['outcome']=='requires_visual_review'];index=[]
for start in range(0,len(r),8):
 subset=r[start:start+8];cw=720;rh=260;sheet=Image.new('RGB',(cw*2,rh*4),'white');d=ImageDraw.Draw(sheet)
 for k,x in enumerate(subset):
  px=(k%2)*cw;py=(k//2)*rh;d.text((px+4,py+3),f"Proposal {x['proposal']} | OCR {x['ocr_unverified']!r} | source / baseline / font / source mask",fill='black');p=Image.open(x['panel']).convert('RGB');p.thumbnail((cw-10,rh-28),Image.Resampling.NEAREST);sheet.paste(p,(px+4,py+24))
 f=L/f'p1-review-{start//8+1:02}.png';sheet.save(f);index.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'proposals':[x['proposal'] for x in subset]})
(E/'p1-review-index.json').write_text(json.dumps(index,indent=2)+'\n');print(len(r),len(index))
