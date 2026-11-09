from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import hashlib,json
out=Path('/data/coding/scanweave/qualification/acr06/local/ink37/gate37/black-border-new.pdf')
im=Image.new('RGB',(1800,2400),(255,255,255));d=ImageDraw.Draw(im);d.rectangle((0,0,1799,2399),outline=(0,0,0),width=75)
f='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';font=ImageFont.truetype(f,56);t='Normal dark text, 0123456789; cost control.'
for i in range(12):d.text((160,200+i*140),t,font=font,fill=(10,10,10))
im.save(out,'PDF',resolution=300.0)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
Path('/data/coding/scanweave/qualification/acr06/ink37/polarity37/black-border-new-truth.json').write_text(json.dumps({'input_sha256':sha(out),'generator_sha256':sha(__file__),'paper':[255,255,255],'ink':[10,10,10],'border':[0,0,0],'text':t,'font':f,'font_sha256':sha(f),'licence':'DejaVu-LICENSE.txt'},indent=2)+'\n')
