from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json
root=Path('/data/coding/scanweave/qualification/acr06'); dest=root/'local/ink37/controls-supplemental'; dest.mkdir(parents=True,exist_ok=True)
font_path=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'); font=ImageFont.truetype(str(font_path),42)
text='Total Chicken 1234.56'
truth={'seed':370612,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'font_sha256':hashlib.sha256(font_path.read_bytes()).hexdigest(),'font_licence':'DejaVu-LICENSE.txt','cases':{}}
for name in ('small_receipt','reverse_with_margin','midtone_table'):
    if name=='small_receipt':
        paper,ink=(235,230,220),(30,30,30); im=Image.new('RGB',(1800,2400),(35,35,35)); d=ImageDraw.Draw(im); d.rectangle((600,700,1200,1700),fill=paper); x=620; ys=(900,1000,1100,1200)
    elif name=='reverse_with_margin':
        paper,ink=(30,35,40),(240,240,240); im=Image.new('RGB',(1800,2400),(255,255,255)); d=ImageDraw.Draw(im); d.rectangle((100,100,1700,2300),fill=paper); x=260; ys=(400,600,800,1000)
    else:
        paper,ink=(235,230,220),(30,30,30); im=Image.new('RGB',(1800,2400),(120,120,120)); d=ImageDraw.Draw(im); d.rectangle((300,200,1500,2200),fill=paper); x=350; ys=(400,600,800,1000,1200,1400,1600,1800)
    for y in ys:d.text((x,y),text,font=font,fill=ink)
    png=dest/(name+'.png'); pdf=dest/(name+'.pdf'); im.save(png); im.save(pdf,resolution=300.0)
    truth['cases'][name]={'paper_rgb':paper,'ink_rgb':ink,'text':text,'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest()}
(root/'ink37/supplemental-truth.json').write_text(json.dumps(truth,indent=2)+'\n')
