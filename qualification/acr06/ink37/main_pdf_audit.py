from pathlib import Path
import json,hashlib
import pikepdf
root=Path('/data/coding/scanweave/qualification/acr06')
rows=[]
for doc in ('historical','financial','mixed','receipts','forms'):
 p=root/'local/ink37'/f'{doc}-main.pdf'
 with pikepdf.open(p) as pdf:
  for i,pg in enumerate(pdf.pages,1):
   current=None; paper=None; text_fill=None; tr=0; fills=set(); n=0; before=True
   for inst in pikepdf.parse_content_stream(pg):
    op=str(inst.operator); a=inst.operands
    if op=='rg':
     current=tuple(round(float(x)*255) for x in a)
     if before: paper=current
     else: text_fill=current
    elif op=='BT': before=False
    elif op=='Tr': tr=int(a[0])
    elif op in ('Tj','TJ') and tr in (0,2,4,6): fills.add(current); n+=1
   weights=(.2126,.7152,.0722)
   rows.append(dict(document=doc,page=i,pdf_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),paper_rgb=paper,paper_luminance=sum(a*b for a,b in zip(paper,weights)) if paper else None,text_fill_rgb=text_fill,text_luminance=sum(a*b for a,b in zip(text_fill,weights)) if text_fill else None,visible_fills_rgb=sorted(fills),visible_show_count=n))
(root/'ink37/main-pdf-audit.json').write_text(json.dumps(rows,indent=2)+'\n')
