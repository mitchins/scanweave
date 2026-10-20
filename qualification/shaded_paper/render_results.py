"""Render actual candidates with unchanged text matrices; no pristine oracle."""
from pathlib import Path
import json,subprocess,collections,hashlib,sys
import pikepdf,pypdfium2 as pdfium,numpy as np
from PIL import Image,ImageDraw
B=Path(__file__).resolve().parent;R=B.parents[1];sys.path.insert(0,str(R/'qualification'));from tools_env import qpdf_bin,qpdf_env,ots_bin
arms=[('source',R/'qualification/pdf_packaging/real/input/history-02.pdf',0),('published',R/'qualification/real_convergence/outputs/history-02.pdf',0),('adobe',R/'qualification/pdf_packaging/groups/historical-adobe.pdf',2)]
for name in ['a','b']:
 p=B/f'{name}.pdf'
 if not p.exists():continue
 arms.append((name,p,0));q=pikepdf.open(p)
 for layer in ['vector','raster']:
  out=pikepdf.open(p)
  for pg in out.pages:
   ops=[];inside=False
   for op in pikepdf.parse_content_stream(pg):
    o=str(op.operator)
    if o=='BT':inside=True
    if (layer=='vector' and o not in ['Do','f','f*']) or (layer=='raster' and not inside):ops.append(op)
    if o=='ET':inside=False
   pg.Contents=pikepdf.Stream(out,pikepdf.unparse_content_stream(ops))
  out.save(B/f'{name}-{layer}.pdf')
  arms.append((name+'-'+layer,B/f'{name}-{layer}.pdf',0))
rows=[];sheets={}
for name,path,page in arms:
 d=pdfium.PdfDocument(str(path));pg=d[page];size=pg.get_size();text=pg.get_textpage().get_text_range();ptext=subprocess.check_output(['pdftotext','-raw','-f',str(page+1),'-l',str(page+1),str(path),'-']).decode();r={'arm':name,'path':str(path),'page':page,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pdfium_text':text,'poppler_text':ptext}
 for scale in [1,3,8]:
  if scale==1:im=pg.render(scale=1).to_pil().convert('RGB')
  else:
   # Contextual first text line, fixed physical fractions across all arms.
   x0,y0,x1,y1=(.12,.18,.70,.225);w,h=size;im=pg.render(scale=scale,crop=(w*x0,h*(1-y1),w*(1-x1),h*y0)).to_pil().convert('RGB')
  if scale==1:im.thumbnail((600,850))
  canvas=Image.new('RGB',(im.width,im.height+22),'white');canvas.paste(im,(0,22));ImageDraw.Draw(canvas).text((4,3),name,fill='black');sheets.setdefault(scale,[]).append(canvas)
 # Independent Poppler render at native 300% reading scale for same source coords.
 subprocess.run(['pdftoppm','-f',str(page+1),'-l',str(page+1),'-singlefile','-scale-to','1400','-png',str(path),str(B/(name+'-poppler'))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 report=Path(str(path)+'.json')
 if report.exists():
  pr=json.loads(report.read_text())['conversion']['page_reports'][0];r['observations']=len(pr['reconstruction']['observations']);r['prototypes']=len(pr['reconstruction']['prototypes']);r['decisions']=dict(collections.Counter(o['decision'] for o in pr['reconstruction']['occurrences']));r['fallback_reasons']=pr['fallback_reasons'];r['coverage']=pr['coverage'];r['visible_owners']=sum(o['owner'].startswith('visible') for o in pr['occurrences']);r['observations_detail']=pr['reconstruction']['observations'];r['qpdf_status']=subprocess.run([qpdf_bin(),'--check',str(path)],env=qpdf_env(),capture_output=True).returncode
 rows.append(r)
for scale,ims in sheets.items():
 out=Image.new('RGB',(max(im.width for im in ims),sum(im.height for im in ims)),'white');y=0
 for im in ims:out.paste(im,(0,y));y+=im.height
 out.save(B/f'comparison-{scale}x.png')
(B/'results.json').write_text(json.dumps(rows,indent=2));print([(r['arm'],r['bytes'],r.get('observations'),r.get('visible_owners')) for r in rows])
