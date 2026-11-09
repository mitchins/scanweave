from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, random

SEED = 370611
random.seed(SEED)
base = Path('/data/coding/scanweave/qualification/acr06')
out = base / 'local/ink37/controls'
out.mkdir(parents=True, exist_ok=True)
font_path = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
font = ImageFont.truetype(str(font_path), 48)
photo = Path('/data/coding/scanweave/qualification/clearscan_competitive/real/cord-02.jpg')
text = 'Invoice No. 4821: Chicken $12.50'
cases = {
    'white': ((255,255,255), (18,18,18)),
    'black_border': ((242,240,232), (33,30,28)),
    'binding_shadow': ((242,238,223), (34,31,29)),
    'receipt_table': ((239,235,224), (35,31,28)),
    'yellow': ((246,232,154), (45,38,28)),
    'blue': ((178,212,235), (20,34,56)),
    'pink': ((238,193,205), (55,25,35)),
    'faded_brown': ((242,230,209), (126,91,63)),
    'reverse_panel': ((243,241,235), (236,235,227)),
    'reverse_page': ((34,38,43), (236,235,227)),
    'photograph': (None, (250,250,250)),
}
truth = {'seed': SEED, 'font': str(font_path), 'font_sha256': hashlib.sha256(font_path.read_bytes()).hexdigest(), 'font_licence': '/usr/share/doc/fonts-dejavu-core/copyright', 'photo_source': str(photo), 'photo_sha256': hashlib.sha256(photo.read_bytes()).hexdigest(), 'cases': {}}
for name, (paper, ink) in cases.items():
    size=(1800,2400)
    if name == 'photograph':
        im=Image.open(photo).convert('RGB').resize(size)
    else:
        im=Image.new('RGB',size,paper)
    d=ImageDraw.Draw(im)
    if name == 'black_border':
        d.rectangle((0,0,1799,2399), outline=(5,5,5), width=85)
    if name == 'binding_shadow':
        for x in range(250):
            v=int(22 + 218 * x / 249)
            d.line((x,0,x,2399),fill=(v,max(0,v-3),max(0,v-8)))
    if name == 'receipt_table':
        d.rectangle((0,0,1799,2399), fill=(79,52,35))
        d.rectangle((220,120,1580,2280), fill=paper)
    if name == 'reverse_panel':
        d.rectangle((160,250,1640,950), fill=(35,39,45))
    for y in (350,500,650,800):
        d.text((280,y),text,font=font,fill=ink)
    d.line((280,1000,1480,1000),fill=ink,width=2)
    png=out / (name+'.png')
    pdf=out / (name+'.pdf')
    im.save(png)
    im.save(pdf, resolution=300.0)
    truth['cases'][name]={'paper_rgb':paper, 'ink_rgb':ink, 'text':text, 'png_sha256':hashlib.sha256(png.read_bytes()).hexdigest(), 'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(), 'note': 'paper varies with the source photograph' if name == 'photograph' else ('text is on a dark panel' if name == 'reverse_panel' else '')}
truth['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(base / 'ink37/controls-truth.json').write_text(json.dumps(truth,indent=2)+'\n')
