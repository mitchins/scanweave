import pikepdf,json
from pathlib import Path
root=Path('/data/coding/scanweave/qualification/acr06/local/ink37c');rows=[]
for doc,n in [('historical',2),('historical',5),('receipts',4)]:
 p=pikepdf.open(root/f'{doc}.pdf');mode=0;visible=0;invisible=0
 for op in pikepdf.parse_content_stream(p.pages[n-1]):
  name=str(op.operator)
  if name=='Tr':mode=int(op.operands[0])
  if name in ('Tj','TJ',"'",'"'):
   if mode==3:invisible+=1
   else:visible+=1
 rows.append({'document':doc,'page':n,'visible_show_ops':visible,'invisible_show_ops':invisible});p.close()
Path('/data/coding/scanweave/qualification/acr06/ink37c/text-modes.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:print(r)
