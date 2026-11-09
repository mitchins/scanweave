from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import hashlib,json
base=Path('/data/coding/scanweave/qualification/acr06'); out=base/'local/ink37/table-candidates';out.mkdir(parents=True,exist_ok=True)
text='Nos quod Chicken 123.45 08.00 BOOK'
fonts=[Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
truth={'seed':370614,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'font_licence':'DejaVu-LICENSE.txt','cases':{}}
for fp in fonts:
 for size in (20,28,36,44):
  im=Image.new('RGB',(1600,2200),(52,40,30)); d=ImageDraw.Draw(im);d.rectangle((80,80,1520,2120),fill=(232,220,198));font=ImageFont.truetype(str(fp),size)
  for y in range(200,2000,80):d.text((180,y),text,fill=(26,19,16),font=font)
  name=f'{fp.stem}-{size}';png=out/f'{name}.png';pdf=out/f'{name}.pdf';im.save(png);im.save(pdf,resolution=300)
  truth['cases'][name]={'text':text,'paper_rgb':[232,220,198],'ink_rgb':[26,19,16],'font':str(fp),'font_sha256':hashlib.sha256(fp.read_bytes()).hexdigest(),'font_size_px':size,'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()}
(base/'ink37/table-candidates-truth.json').write_text(json.dumps(truth,indent=2)+'\n')
