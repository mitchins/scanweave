"""Complete pages at 72 pixels/inch, with context preserved (no glyph resizing)."""
from pathlib import Path
from PIL import Image,ImageDraw
import pypdfium2 as pdfium
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
for dpi in [300,600]:
 for pi in [0,6]:
  panel=Image.new('RGB',(432,5*240),'white');draw=ImageDraw.Draw(panel)
  for i,name in enumerate(['source','pristine','adobe','previous','final']):
   if name in ['source','pristine']:
    part='input' if name=='source' else 'oracle';im=Image.open(ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/{part}/page{pi:02}.png').resize((432,216),Image.Resampling.LANCZOS)
   else:
    doc=pdfium.PdfDocument(B/str(dpi)/(name+'.pdf'));im=doc[pi].render(scale=1).to_pil()
   panel.paste(im.convert('RGB'),(0,i*240+20));draw.text((4,i*240+2),name+' / 72 DPI',fill='black')
  panel.save(B/str(dpi)/f'final-native-page{pi:02}.png')
