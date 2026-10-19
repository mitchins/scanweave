import json,math,subprocess
from pathlib import Path
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image,ImageDraw
from oracle import B,R
D=B/'stage-a';paper=np.asarray(Image.open(D/'counterfactual-paper.png')).astype(float);base=R/'qualification/clearscan_contours/300';audit=json.loads((base/'final/audit.json').read_text());report=json.loads((base/'final.json').read_text());obs={o['symbol_id']:o for o in report['page_reports'][0]['reconstruction']['observations']};mask=np.zeros(paper.shape,bool)
for r in audit['placements']:
 if r['page']!=0 or r['symbol'] not in obs:continue
 x0,y0,x1,y1=map(int,obs[r['symbol']]['bbox_px']);mask[max(0,y0-2):y1+2,max(0,x0-2):x1+2]=True
src=np.asarray(Image.open(R/'qualification/experiments/m1g/fixture/dpi300/input/page00.png').convert('L')).astype(float);ink=mask & (paper-src>8);rows={}
for arm in ['A0','A1-native','A1','A2']:
 path=D/(arm+'.pdf')
 if not path.exists():continue
 p=pikepdf.open(path);rows[arm]={'pdf_bytes':path.stat().st_size,'raster_bytes':sum(len(o.read_raw_bytes()) for o in p.objects if isinstance(o,pikepdf.Stream) and o.get('/Subtype')=='/Image')}
 for ren in ['pdfium','poppler']:
  for layer in ['final','background','vector']:
   q=pikepdf.open(path);page=q.pages[0];ops=[];inside=False
   for i in pikepdf.parse_content_stream(page):
    op=str(i.operator)
    if op=='BT':inside=True
    if (layer=='final' or (layer=='background' and not inside) or (layer=='vector' and op!='Do')):ops.append(i)
    if op=='ET':inside=False
   out=D/f'{arm}-{layer}.pdf';page.Contents=pikepdf.Stream(q,pikepdf.unparse_content_stream(ops));q.save(out)
   if ren=='pdfium':im=pdfium.PdfDocument(out)[0].render(scale=math.nextafter(300/72,0)).to_pil().convert('L')
   else:
    subprocess.run(['pdftoppm','-singlefile','-r','300','-gray','-png',str(out),str(out.with_suffix(''))],check=True,capture_output=True);im=Image.open(out.with_suffix('.png')).convert('L')
   a=np.asarray(im).astype(float);im.save(D/f'{arm}-{ren}-{layer}.png')
   if layer=='background':
    delta=paper-a;outside=~mask;rows[arm][ren]={'source_ink_band_residual_dark_contrast':float(np.maximum(delta[ink],0).mean()),'owned_background_mae':float(abs(delta[mask]).mean()),'owned_paper_dark_bias':float(delta[mask].mean()),'outside_mae':float(abs(delta[outside]).mean()),'background_std_owned':float(a[mask].std()),'counterfactual_std_owned':float(paper[mask].std())}
   if layer=='final':final=a
   if layer=='vector':rows[arm][ren]['mean_final_minus_vector_coverage']=float(((255-final)-(255-a))[ink].mean()/255)
(D/'measurements.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2))
