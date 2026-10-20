import json
from pathlib import Path
import pypdfium2 as pdfium
from PIL import Image,ImageDraw
B=Path(__file__).resolve().parent;P=B.parent/'pdf_packaging';D=B/'inspection';D.mkdir(exist_ok=True)
for id in ['history-02','cord-00']:
 new=B/'results'/f'{id}.pdf'
 if not new.exists():continue
 report=json.loads(Path(str(new)+'.json').read_text());r=report['conversion']['page_reports'][0];vis=[o for o in r['occurrences'] if o['owner'].startswith('visible')];obs={o['symbol_id']:o for o in r['reconstruction']['observations']};boxes=[obs[o['symbol_id']]['bbox_px'] for o in vis if o['symbol_id'] in obs][:8]
 paths=[P/'real/input'/f'{id}.pdf',P/'real/scanweave'/f'{id}.pdf',new];images=[pdfium.PdfDocument(str(p))[0].render(scale=300/72).to_pil().convert('RGB') for p in paths]
 thumbs=[]
 for b in boxes:
  x,y=(b[0]+b[2])/2,(b[1]+b[3])/2;rect=(int(max(0,x-150)),int(max(0,y-30)),int(x+150),int(y+40))
  for im in images:thumbs.append(im.crop(rect).resize((600,140)))
 sheet=Image.new('RGB',(1800,30+140*len(boxes)),'white');d=ImageDraw.Draw(sheet)
 for i,label in enumerate(['Source','Previous','New']):d.text((i*600,3),label,fill='black')
 for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*600,30+(i//3)*140))
 if boxes:sheet.save(D/f'{id}-words.png')
 images[-1].thumbnail((700,1000));images[-1].save(D/f'{id}-page.png')
 print(id,len(vis),r.get('segmentation_method'),r.get('coverage'),flush=True)
