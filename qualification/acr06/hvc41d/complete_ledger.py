"""Index every p1 proposal and render its final rejection context."""
import pathlib,json,hashlib,collections
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41d';L=R/'local/hvc41d';rows=json.loads((E/'p1-preflight-ledger.json').read_text());review={x['proposal']:x for x in json.loads((E/'p1-visual-review.json').read_text())};src=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');base=Image.open(L/'renders/pdfium-300-01-baseline.png').convert('RGB');diag=Image.open(L/'renders/pdfium-300-01-candidate.png').convert('RGB');folder=L/'ledger-panels';folder.mkdir(exist_ok=True);index=[]
for x in rows:
 i=x['proposal'];v=review.get(i)
 if v:x['outcome']='rejected';x['reasons'].append('ownership_footprint_violation' if i==243 else 'visual_or_residual_confidence_not_established');x['visual_review']=v
 a,b,c,d=map(int,x['bbox']);box=(max(0,a-6),max(0,b-6),min(src.width,c+6),min(src.height,d+6));ims=[src.crop(box),base.crop(box),diag.crop(box) if i==243 else base.crop(box)];scale=4;cw=max(120,max(im.width for im in ims)*scale+10);ch=max(im.height for im in ims)*scale+28;sheet=Image.new('RGB',(cw*3,ch),'white');draw=ImageDraw.Draw(sheet)
 for k,(im,lab) in enumerate(zip(ims,['source','baseline','rejected trial' if i==243 else 'final baseline'])):
  draw.text((k*cw+2,3),lab,fill='black');sheet.paste(im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST),(k*cw+3,23))
 f=folder/f'p1-{i:03}.png';sheet.save(f);digest=hashlib.sha256(f.read_bytes()).hexdigest();x['ledger_panel']=str(f);x['ledger_panel_sha256']=digest;index.append({'proposal':i,'path':str(f),'sha256':digest})
(E/'p1-final-ledger.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n');(E/'p1-ledger-panel-index.json').write_text(json.dumps(index,indent=2)+'\n');print('rows',len(rows),'rejected',sum(x['outcome']=='rejected' for x in rows),'panels',len(index))
