"""Background error against evaluator-only paired paper, common emitted instances."""
import json,math,subprocess,hashlib
from pathlib import Path
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image,ImageDraw
from oracle import paired,B,R

def layer(source,out,kind,page_index=None):
 q=pikepdf.open(source)
 if page_index is not None:
  p=pikepdf.Pdf.new();p.pages.append(q.pages[page_index]);q=p
 for page in q.pages:
  ops=[];inside=False
  for i in pikepdf.parse_content_stream(page):
   op=str(i.operator)
   if op=='BT':inside=True
   if kind=='final' or (kind=='background' and not inside) or (kind=='vector' and op!='Do'):ops.append(i)
   if op=='ET':inside=False
  page.Contents=pikepdf.Stream(q,pikepdf.unparse_content_stream(ops))
 q.save(out)

def run():
 results=[]
 for dpi in [300,600]:
  d=B/str(dpi);paper,records=paired(dpi,0);Image.fromarray(paper).save(d/'counterfactual-paper.png');paper=paper.astype(float);src=np.asarray(Image.open(R/f'qualification/experiments/m1g/fixture/dpi{dpi}/input/page00.png').convert('L')).astype(float)
  audit=json.loads((d/'final/audit.json').read_text());report=json.loads((d/'final.json').read_text());obs={o['symbol_id']:o for o in report['page_reports'][0]['reconstruction']['observations']};owned=np.zeros(paper.shape,bool); common=np.zeros(paper.shape,bool); boxes=[]
  for row in audit['placements']:
   if row['page']!=0 or row['symbol'] not in obs:continue
   x0,y0,x1,y1=map(int,obs[row['symbol']]['bbox_px']);r=2*dpi//300;owned[max(0,y0-r):y1+r,max(0,x0-r):x1+r]=True
   if all(ord(c)<128 for c in obs[row['symbol']]['text_hypothesis']):
    common[max(0,y0-r):y1+r,max(0,x0-r):x1+r]=True;boxes.append((x0,y0,x1,y1))
  ink=owned&(paper-src>8)
  for arm in ['previous','final','adobe']:
   paths={};data={}
   for kind in ['background','vector','final']:
    dest=d/arm/(kind+'-page0.pdf');dest.parent.mkdir(exist_ok=True);layer(d/(arm+'.pdf'),dest,kind,0);paths[kind]=dest
   for ren in ['pdfium','poppler']:
    rasters={}
    for kind,path in paths.items():
     if ren=='pdfium':im=pdfium.PdfDocument(path)[0].render(scale=math.nextafter(dpi/72,0)).to_pil().convert('L')
     else:
      subprocess.run(['pdftoppm','-singlefile','-r',str(dpi),'-gray','-png',str(path),str(path.with_suffix(''))],check=True,capture_output=True);im=Image.open(path.with_suffix('.png')).convert('L')
     rasters[kind]=np.asarray(im).astype(float);im.save(d/arm/f'{ren}-{kind}-page0.png')
    bg=rasters['background'];diff=bg-paper
    local=[];common_ink=common&(paper-src>8);margin=6*dpi//300
    for x0,y0,x1,y1 in boxes:
     ax=max(0,x0-margin);ay=max(0,y0-margin);bx=min(paper.shape[1],x1+margin);by=min(paper.shape[0],y1+margin)
     ring=np.ones((by-ay,bx-ax),bool);ring[y0-ay:y1-ay,x0-ax:x1-ax]=False;ring&=(paper[ay:by,ax:bx]-src[ay:by,ax:bx]<3)
     region=common_ink[y0:y1,x0:x1];delta=-diff[y0:y1,x0:x1]
     bias=float(np.median(-diff[ay:by,ax:bx][ring])) if ring.any() else 0.0
     local.extend(np.maximum(delta[region]-bias,0).tolist())
    results.append({'dpi':dpi,'arm':arm,'renderer':ren,'glyph_population':'new emitted page0 bbox +2 physical300px halo; source contrast>8 against paired paper','source_ink_pixels':int(ink.sum()),'ghost_contrast':float(np.mean(local)),'raw_inkband_dark_contrast':float(np.maximum(-diff[ink],0).mean()),'common_ascii_inkband_dark_contrast':float(np.maximum(-diff[common_ink],0).mean()),'ghost_method':'Only common vectorized ASCII; per-glyph surrounding-paper residual median removed; kana excluded because Adobe retains it as legitimate raster','pdf_sha256':hashlib.sha256((d/(arm+'.pdf')).read_bytes()).hexdigest(),'paper_mae_owned':float(abs(diff[owned]).mean()),'paper_mae_common_ascii':float(abs(diff[common]).mean()),'paper_bias_owned':float(diff[owned].mean()),'paper_std_owned':float(bg[owned].std()),'oracle_std_owned':float(paper[owned].std()),'paper_mae_outside':float(abs(diff[~owned]).mean()),'vector_to_final_inkband_mae':float(abs(rasters['vector'][ink]-rasters['final'][ink]).mean())})
   # Full page vector/raster composition is actually rerendered at each zoom.
   for zoom in [1,8,16]:
    for kind,path in paths.items():
     doc=pdfium.PdfDocument(path);doc[0].render(scale=math.nextafter(zoom,0)).to_pil().save(d/arm/f'{kind}-{zoom*100}pct.png')
  # Fixed physical crop around complete first word, paper row separately visible.
  for zoom in [1,8,16]:
   panels=[]
   for label,path in [('paired paper',None)]+[(arm+' '+kind,d/arm/(kind+'-page0.pdf')) for arm in ['previous','final','adobe'] for kind in ['background','vector','final']]:
    if path:
     pg=pdfium.PdfDocument(path)[0];w,h=pg.get_size();im=pg.render(scale=zoom,crop=(65*.24,h-135*.24,w-475*.24,75*.24)).to_pil().convert('RGB')
    else:im=Image.fromarray(paper.astype('uint8')).crop((65*dpi//300,75*dpi//300,475*dpi//300,135*dpi//300)).resize((round(410*.24*zoom),round(60*.24*zoom)),Image.Resampling.LANCZOS).convert('RGB')
    panels.append((label,im))
   out=Image.new('RGB',(max(i.width for _,i in panels)+145,sum(i.height+22 for _,i in panels)),'white');draw=ImageDraw.Draw(out);y=0
   for label,im in panels:draw.text((3,y+2),label,fill='black');out.paste(im,(140,y+18));y+=im.height+22
   out.save(d/f'background-context-{zoom*100}pct.png')
 (B/'background-metrics.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
if __name__=='__main__':run()
