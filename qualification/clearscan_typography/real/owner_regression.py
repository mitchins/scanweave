"""Native extraction regression: invisible owners use stable font geometry."""
from pathlib import Path
import json,re,subprocess
import pypdfium2 as pdfium
B=Path(__file__).resolve().parent;ROOT=B.parents[2]
def norm(t):return re.sub(r'\s+','',t)
def edit(a,b):
 v=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  u=[i]
  for j,y in enumerate(b,1):u.append(min(u[-1]+1,v[j]+1,v[j-1]+(x!=y)))
  v=u
 return v[-1]
rows=[]
for arm,p in [('previous',ROOT/'qualification/clearscan_competitive/real/product/cord-00.pdf'),('final',B/'final/cord-00.pdf')]:
 doc=pdfium.PdfDocument(p);t=doc[0].get_textpage().get_text_range();pop=subprocess.check_output(['pdftotext','-raw',str(p),'-'],text=True)
 rows.append({'arm':arm,'pdfium_nonspace_chars':len(norm(t)),'poppler_nonspace_chars':len(norm(pop)),'native_vs_poppler_nonspace_edit':edit(norm(t),norm(pop))})
assert rows[-1]['native_vs_poppler_nonspace_edit']==0,rows
(B/'owner-regression.json').write_text(json.dumps({'method':__doc__,'rows':rows},indent=2));print(rows)
