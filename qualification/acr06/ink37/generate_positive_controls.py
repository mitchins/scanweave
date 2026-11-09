from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import hashlib,json
ROOT=Path('/data/coding/scanweave/qualification/acr06'); OUT=ROOT/'local/ink37/positive-controls';OUT.mkdir(parents=True,exist_ok=True)
fontpath=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf');text='SCAN 37 VECTOR 4821'; truth={'seed':370613,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'font_sha256':hashlib.sha256(fontpath.read_bytes()).hexdigest(),'font_licence':'DejaVu-LICENSE.txt','cases':{}}
for kind in ('reverse_page','reverse_panel','dark_table'):
 for size in (44,72,108,160):
  paper=(28,32,36) if kind=='reverse_page' else (245,241,231)
  ink=(241,238,225) if kind.startswith('reverse') else (38,30,25)
  image=Image.new('RGB',(1800,2400),(43,31,24) if kind=='dark_table' else paper); d=ImageDraw.Draw(image)
  if kind=='dark_table':d.rectangle((120,100,1680,2300),fill=paper)
  if kind=='reverse_panel':d.rectangle((180,200,1620,2150),fill=(28,32,36))
  font=ImageFont.truetype(str(fontpath),size)
  for y in range(350,2000,200): d.text((240,y),text,font=font,fill=ink)
  name=f'{kind}-{size}';png=OUT/(name+'.png');pdf=OUT/(name+'.pdf');image.save(png);image.save(pdf,resolution=300.0)
  truth['cases'][name]={'paper_rgb':paper,'ink_rgb':ink,'text':text,'font_size_px':size,'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest()}
(ROOT/'ink37/positive-controls-truth.json').write_text(json.dumps(truth,indent=2)+'\n')
