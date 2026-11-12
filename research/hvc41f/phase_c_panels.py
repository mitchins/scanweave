#!/usr/bin/env python3
"""Render a contact sheet of the size-only PDF; this is not Phase D qualification."""
import hashlib,json,os,pathlib,subprocess,sys,tempfile
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_SIZE_PANELS')!='1':sys.exit('research switch required')
ledger=R/'hvc41e/review-decisions.json';base=R/'local/ink33r/historical.pdf';size=L/'SIZE-MEASUREMENT-NOT-FINAL.pdf';spec=json.loads((E/'phase-c-size.json').read_text())
if sha(ledger.read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha(base.read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b' or sha(size.read_bytes())!=spec['sha256']:sys.exit('input mismatch')
rows=[r for r in json.loads(ledger.read_text()) if r['decision']=='accept'];assert len(rows)==38
with tempfile.TemporaryDirectory(prefix='hvc41f-c-panels-noocr-') as td:
 marker=L/'ocr-invoked';stub=pathlib.Path(td)/'tesseract';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(R/'local/ink33r/historical.pdf.json')
 d=pdfium.PdfDocument(str(size));p=d[0];image=p.render(scale=300/72,rev_byteorder=True).to_pil().convert('RGB');image.save(L/'size-only-p1-300.png');p.close();d.close();source=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');sw,sh=source.size;W,H=image.size
 def pdftext(path):
  d=pdfium.PdfDocument(str(path));v=[]
  for p in d:
   t=p.get_textpage();v.append(t.get_text_range());t.close();p.close()
  d.close();return v
 def searches(path):
  d=pdfium.PdfDocument(str(path));p=d[0];t=p.get_textpage();result={}
  for word in ['Bacharias','Boect!','Wud','Dat','fram','Ber)']:
   search=t.search(word);hits=[]
   while (hit:=search.get_next()) is not None:hits.append(list(hit))
   search.close();result[word]=hits
  t.close();p.close();d.close();return result
 search_equal=searches(base)==searches(size)
 t1=pdftext(base)==pdftext(size);t2=subprocess.check_output(['pdftotext','-layout',str(base),'-'])==subprocess.check_output(['pdftotext','-layout',str(size),'-']);
 with pikepdf.open(base) as b, pikepdf.open(size) as c:
  imsame=all(sha(b.pages[k].Resources.XObject['/Im0'].read_raw_bytes())==sha(c.pages[k].Resources.XObject['/Im0'].read_raw_bytes()) for k in range(5));content=all(sha(b.pages[k].Contents.read_bytes())==sha((c.pages[k].Contents[0] if k==0 else c.pages[k].Contents).read_bytes()) for k in range(5))
 if not all([t1,t2,imsame,content,search_equal]) or marker.exists():sys.exit('size-only invariant failed')
 env=os.environ.copy();env['LD_LIBRARY_PATH']='/data/coding/scanweave/tools/dist/lib';q=subprocess.run(['/data/coding/scanweave/tools/dist/bin/qpdf','--check',str(size)],env=env,capture_output=True,text=True)
 if q.returncode:sys.exit('qpdf failed')
 cw,ch=230,180;sheet=Image.new('RGB',(cw*6,ch*7),'white');draw=ImageDraw.Draw(sheet);idx=[]
 for j,r in enumerate(rows):
  a,b,c,d=r['reference_box'];pad=5;sbox=(max(0,a-pad),max(0,b-pad),min(sw,c+pad),min(sh,d+pad));pbox=(int(sbox[0]*W/sw),int(sbox[1]*H/sh),int(np.ceil(sbox[2]*W/sw)),int(np.ceil(sbox[3]*H/sh)));left=source.crop(sbox);right=image.crop(pbox);left=left.resize((left.width*max(1,min(105//left.width,145//left.height)),left.height*max(1,min(105//left.width,145//left.height))),Image.Resampling.NEAREST);right=right.resize((right.width*max(1,min(105//right.width,145//right.height)),right.height*max(1,min(105//right.width,145//right.height))),Image.Resampling.NEAREST);x=(j%6)*cw;y=(j//6)*ch;draw.text((x+3,y+2),f"{r['proposal']:03} {r['claude_identity'][:15]}",fill='black');draw.text((x+3,y+18),'source',fill='black');draw.text((x+117,y+18),'size-only',fill='black');sheet.paste(left,(x+3,y+34));sheet.paste(right,(x+117,y+34));idx.append({'proposal':r['proposal'],'symbol_id':r['symbol_id'],'sheet_cell':[j%6,j//6],'source_box':sbox,'candidate_box':pbox})
 panel=L/'size-only-38-contact.png';sheet.save(panel);result={'size_only_not_final':True,'contact_sheet':str(panel),'contact_sha256':sha(panel.read_bytes()),'candidate_render':str(L/'size-only-p1-300.png'),'candidate_render_sha256':sha((L/'size-only-p1-300.png').read_bytes()),'glyphs':idx,'pdfium_text_equal':t1,'poppler_text_equal':t2,'pdfium_six_searches_equal':search_equal,'image_streams_equal':imsame,'original_content_equal':content,'qpdf_exit':q.returncode,'ocr_stub_not_invoked':True};(E/'phase-c-panel-index.json').write_text(json.dumps(result,indent=2)+'\n');print('size-only contact sheet',len(idx),'qpdf',q.returncode)
