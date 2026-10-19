"""Rejected contour refinement, isolated from paper using actual vector PDFs."""
import json,math,subprocess
from pathlib import Path
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image
B=Path(__file__).resolve().parent;R=B.parents[1];D=B/'contour-trial';D.mkdir(exist_ok=True);sources={'before':B/'300/final.pdf','refined':B/'contour-300.pdf'};reports={'before':B/'300/final.json','refined':B/'contour-300.json'};accepted={};arrays={};rows=[]
for arm,path in sources.items():
 report=json.loads(reports[arm].read_text());accepted[arm]={o['symbol_id'] for p in report['page_reports'] for o in p['occurrences'] if o['owner']=='visible_tounicode'}
 q=pikepdf.open(path)
 for p in q.pages:p.Contents=pikepdf.Stream(q,pikepdf.unparse_content_stream([i for i in pikepdf.parse_content_stream(p) if str(i.operator)!='Do']))
 out=D/(arm+'-vectors.pdf');q.save(out);doc=pdfium.PdfDocument(out);arrays[arm]={};arrays[arm]['pdfium']=[np.asarray(p.render(scale=math.nextafter(300/72,0)).to_pil().convert('L')) for p in doc];subprocess.run(['pdftoppm','-r','300','-gray','-png',str(out),str(D/arm)],check=True,capture_output=True);arrays[arm]['poppler']=[np.asarray(Image.open(D/f'{arm}-{i+1}.png').convert('L')) for i in range(8)]
for pi in range(8):
 oracle=R/f'qualification/experiments/m1g/fixture/dpi300/oracle';truth=json.loads((oracle/f'page{pi:02}.truth.json').read_text());image=np.asarray(Image.open(oracle/f'page{pi:02}.png').convert('L'))
 for g in truth['records']:
  if g['text'] not in ['8','0','g'] or g['id'] not in accepted['before']&accepted['refined']:continue
  x0,y0,x1,y1=map(int,g['bbox']);sl=(slice(y0+5,y1-5),slice(x0+5,x1-5));t=image[sl]<170;r={'page':pi,'id':g['id'],'char':g['text']}
  for arm in sources:
   for ren in ['pdfium','poppler']:
    a=arrays[arm][ren][pi][sl]<170;r[arm+'_'+ren]=float((a&t).sum()/max(1,(a|t).sum()))
  rows.append(r)
result={'method':__doc__,'n':len(rows),'means':{a+'_'+r:float(np.mean([x[a+'_'+r] for x in rows])) for a in sources for r in ['pdfium','poppler']},'glyphs':rows,'decision':'reject; keep existing canonical outlines'}
(B/'contour-trial.json').write_text(json.dumps(result,indent=2));print(result['n'],result['means'])
