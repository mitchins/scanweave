import pikepdf,json,hashlib
from pathlib import Path
base=Path('/data/coding/scanweave/qualification/acr06/local/ink37');rows=[]
for d,n in [('historical',2),('historical',5),('receipts',4)]:
 files=[base/'polarity37'/f'{d}-main.pdf',base/'owner37'/f'{d}.pdf'];data=[]
 for f in files:
  pdf=pikepdf.open(f);p=pdf.pages[n-1];values=[]
  for inst in pikepdf.parse_content_stream(p):
   if str(inst.operator)=='BDC':
    for obj in inst.operands:
     if isinstance(obj,pikepdf.Dictionary) and '/ActualText' in obj:values.append(str(obj['/ActualText']))
  fonts={}
  for name,font in p.Resources.get('/Font',{}).items():
   if '/ToUnicode' in font: fonts[str(name)]=hashlib.sha256(font['/ToUnicode'].read_bytes()).hexdigest()
  data.append((values,fonts));pdf.close()
 rows.append({'document':d,'page':n,'actualtext_main_count':len(data[0][0]),'actualtext_candidate_count':len(data[1][0]),'actualtext_equal':data[0][0]==data[1][0],'tounicode_equal':data[0][1]==data[1][1],'tounicode':data[0][1]})
Path('/data/coding/scanweave/qualification/acr06/ink37/polarity37/owner-actualtext.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:print(row)
