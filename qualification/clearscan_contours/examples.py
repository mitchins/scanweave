"""Ten best/worst families and fixed-position 800% PDFium crop sheets."""
from pathlib import Path
from collections import defaultdict
import json
import numpy as np
from PIL import Image, ImageDraw
import pypdfium2 as pdfium
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
for dpi in (300,600):
    base=ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}'
    ms={a:json.loads((B/str(dpi)/a/'metrics.json').read_text()) for a in ('adobe','previous','final')}
    docs={a:pdfium.PdfDocument(str(B/str(dpi)/(a+'.pdf'))) for a in ms}
    rankings={}
    for arm in ('adobe','final'):
        families=defaultdict(list)
        for r in ms[arm]['glyphs']:
            if r['geometry']=='exact' and 'source_isolated' in r:families[('kana' if ord(r['text'][0])>127 else 'italic' if r['page']>=6 else 'serif',r['text'])].append(r)
        ranks=[]
        for (style,ch),rs in families.items():
            rank={'text':ch,'style':style,'n':len(rs)}
            for renderer in ('poppler','pdfium'):
                rank[renderer]=float(np.mean([r[renderer+'_isolated'] for r in rs]));rank[renderer+'_gain']=float(np.mean([r[renderer+'_isolated']-r['source_isolated'] for r in rs]))
            ranks.append(rank)
        rankings[arm]={renderer:{kind:sorted(ranks,key=lambda r:r[renderer+'_gain'],reverse=(kind=='best'))[:10] for kind in ('best','worst')} for renderer in ('poppler','pdfium')}
        for kind in ('best','worst'):
            sheet=Image.new('RGB',(1100,10*150+35),'white');draw=ImageDraw.Draw(sheet)
            for col,label in enumerate(['family / PDFium gain','source','pristine','Adobe XI','previous','new']):draw.text((col*180+5,5),label,fill='black')
            for row,fam in enumerate(rankings[arm]['pdfium'][kind]):
                rs=families[(fam['style'],fam['text'])];r=sorted(rs,key=lambda r:r['pdfium_isolated']-r['source_isolated'],reverse=(kind=='best'))[0];pi=r['page'];x0,y0,x1,y1=map(int,r['bbox']);margin=4;x0-=margin;y0-=margin;x1+=margin;y1+=margin;src=Image.open(base/'input'/f'page{pi:02}.png');truth=Image.open(base/'oracle'/f'page{pi:02}.png');w,h=src.size;pt=72/dpi;crop=(x0*pt,(h-y1)*pt,(w-x1)*pt,y0*pt)
                panels=[src.crop((x0,y0,x1,y1)),truth.crop((x0,y0,x1,y1))]+[docs[a][pi].render(scale=8,crop=crop).to_pil() for a in ('adobe','previous','final')]
                draw.text((5,40+row*150),f"{fam['style']} {fam['text']} n={fam['n']}\n{fam['pdfium_gain']:+.4f}\np{pi:02} {r['id']}",fill='black')
                for col,img in enumerate(panels,1):
                    if col<3:img=img.resize((round(img.width*pt*8),round(img.height*pt*8)),Image.Resampling.NEAREST)
                    img.thumbnail((170,140));sheet.paste(img.convert('RGB'),(col*180,35+row*150))
            sheet.save(B/str(dpi)/f'{arm}-{kind}-800pct.png')
    (B/str(dpi)/'family-rankings.json').write_text(json.dumps(rankings,indent=2,ensure_ascii=False))
