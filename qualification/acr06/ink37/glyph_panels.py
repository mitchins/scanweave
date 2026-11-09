from pathlib import Path
from PIL import Image, ImageDraw
import json, math, hashlib
base=Path('/data/coding/scanweave/qualification/acr06')
old=base/'local/ink33'
local=base/'local/ink37'
out=local/'glyph-panels'
out.mkdir(parents=True,exist_ok=True)
items=[]
for doc,page in [('historical',2),('historical',5),('receipts',4)]:
    stem=f'{page:02}'
    mapping=json.loads((old/'maps'/doc/(stem+'.json')).read_text())
    images=[Image.open(old/'renders'/doc/(stem+'-source.png')).convert('RGB'),Image.open(old/'renders'/doc/(stem+'-scanweave.png')).convert('RGB'),Image.open(local/'three-engine/pdfium'/doc/('candidate-'+stem+'.png')).convert('RGB')]
    if len({im.size for im in images})!=1: raise ValueError((doc,page,'render size mismatch'))
    for g in mapping['scan_objects']:
        x0,y0,x1,y1=g['box']; margin=12
        box=(max(0,math.floor(x0)-margin),max(0,math.floor(y0)-margin),min(images[0].width,math.ceil(x1)+margin),min(images[0].height,math.ceil(y1)+margin))
        crops=[im.crop(box) for im in images]
        items.append({'document':doc,'page':page,'box':box,'object_box':g['box'],'old_fill_rgba':g['rgba'],'crops':crops})
for start in range(0,len(items),8):
    batch=items[start:start+8]; row_h=max(120,max(im.height*4+30 for item in batch for im in item['crops']))
    col_w=max(150,max(im.width*4+12 for item in batch for im in item['crops']))
    sheet=Image.new('RGB',(col_w*6,row_h*len(batch)),(255,255,255)); draw=ImageDraw.Draw(sheet)
    for j,item in enumerate(batch):
        y=j*row_h
        for k,(label,im) in enumerate(zip(('source','main','candidate'),item['crops'])):
            draw.text((k*col_w,y),f"{start+j+1:03d} {item['document']} p{item['page']} {label}",fill=(0,0,0))
            sheet.paste(im,(k*col_w,y+20))
            large=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST)
            draw.text(((k+3)*col_w,y),label+' 4x',fill=(0,0,0))
            sheet.paste(large,((k+3)*col_w,y+20))
        item['sheet']=f'sheet-{start//8+1:02}.png'; item['sheet_row']=j+1
        del item['crops']
    path=out/f'sheet-{start//8+1:02}.png'; sheet.save(path)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    for item in batch:item['sheet_sha256']=digest
(base/'ink37/glyph-panel-index.json').write_text(json.dumps(items,indent=2)+'\n')
