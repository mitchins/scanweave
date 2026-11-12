import pathlib,json,hashlib
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41e';L=R/'local/hvc41e/final';idx=json.loads((E/'final-panel-index.json').read_text());glyphs=[x for x in idx if x['kind']=='emitted_glyph_4x'];out=[]
for start in range(0,len(glyphs),8):
 sub=glyphs[start:start+8];cw=720;rh=260;sheet=Image.new('RGB',(cw*2,rh*4),'white');d=ImageDraw.Draw(sheet)
 for i,x in enumerate(sub):
  px=i%2*cw;py=i//2*rh;d.text((px+3,py+3),f"{x['proposal']} | {x['symbol']} | lead identity {x['claude_identity']!r}",fill='black');im=Image.open(x['path']).convert('RGB');im.thumbnail((cw-8,rh-28),Image.Resampling.NEAREST);sheet.paste(im,(px+3,py+24))
 f=L/'panels'/f'composed-review-{start//8+1:02}.png';sheet.save(f);out.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'proposals':[x['proposal'] for x in sub]})
(E/'composed-review-index.json').write_text(json.dumps(out,indent=2)+'\n');print(len(glyphs),len(out))
