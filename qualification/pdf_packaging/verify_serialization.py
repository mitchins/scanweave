"""Semantic, decoded-resource and two-renderer exactness of serializer changes."""
import json,hashlib,subprocess,tempfile,sys
from pathlib import Path
import pikepdf,pypdfium2 as pdfium
B=Path(__file__).resolve().parent;R=B.parents[1];sys.path.insert(0,str(R/'qualification'))
from tools_env import qpdf_bin,qpdf_env,ots_bin
sha=lambda b:hashlib.sha256(b).hexdigest()
def streams(p):
 result={}
 for o in p.objects:
  if not isinstance(o,pikepdf.Stream) or o.get('/Type') in [pikepdf.Name.ObjStm,pikepdf.Name.XRef]:continue
  try:data=o.read_bytes()
  except pikepdf.PdfError:
   # DCT remains byte-identical, including color interpretation dictionary.
   data=o.read_raw_bytes()+str(o.get('/Filter')).encode()+str(o.get('/ColorSpace')).encode()
  result[str(o.objgen)]=sha(data)
 return result
def render(path,renderer,idx,resolution):
 if renderer=='pdfium':
  doc=pdfium.PdfDocument(str(path));page=doc[idx];return page.render(scale=resolution/72).to_pil().convert('RGB').tobytes()
 with tempfile.TemporaryDirectory() as t:
  prefix=Path(t)/'r';subprocess.run(['pdftoppm','-f',str(idx+1),'-l',str(idx+1),'-singlefile','-r',str(resolution),'-png',str(path),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  from PIL import Image
  return Image.open(prefix.with_suffix('.png')).convert('RGB').tobytes()
rows=[]
for dpi in [300,600]:
 old=B.parent/'clearscan_background'/str(dpi)/'final.pdf';new=B/str(dpi)/'final.pdf';a=pikepdf.open(old);b=pikepdf.open(new)
 assert len(a.pages)==len(b.pages)==8
 assert streams(a)==streams(b),'decoded streams changed'
 assert [list(p.MediaBox) for p in a.pages]==[list(p.MediaBox) for p in b.pages]
 for x,y in zip(a.pages,b.pages):
  assert list(x.obj.get('/CropBox',x.MediaBox))==list(y.obj.get('/CropBox',y.MediaBox))
  assert int(x.obj.get('/Rotate',0))==int(y.obj.get('/Rotate',0))
 for opt in ['-raw','-layout']:
  assert subprocess.check_output(['pdftotext',opt,str(old),'-'])==subprocess.check_output(['pdftotext',opt,str(new),'-'])
 results=[]
 for ren in ['pdfium','poppler']:
  for i in range(8):
   x=sha(render(old,ren,i,dpi));y=sha(render(new,ren,i,dpi));assert x==y,(dpi,ren,i);results.append({'renderer':ren,'dpi':dpi,'page':i,'sha256':x,'identical':True})
 font=[]
 with tempfile.TemporaryDirectory() as t:
  for o in b.objects:
   if isinstance(o,pikepdf.Dictionary) and '/FontFile2' in o:
    f=Path(t)/f'{len(font)}.ttf';f.write_bytes(o.FontFile2.read_bytes());check=subprocess.run([ots_bin(),str(f)],capture_output=True,text=True);assert check.returncode==0; font.append({'decoded_bytes':f.stat().st_size,'sha256':sha(f.read_bytes()),'ots_status':check.returncode})
 check=subprocess.run([qpdf_bin(),'--check',str(new)],env=qpdf_env(),capture_output=True,text=True);assert check.returncode==0,check.stdout+check.stderr
 searches=[]
 for path in [old,new]:
  doc=pdfium.PdfDocument(str(path));texts=[];found=[]
  for page in doc:
   t=page.get_textpage();text=t.get_text_range();texts.append(text)
   import re
   tokens=re.findall('[A-Za-z0-9]{3,}',text);found.append([(s,t.search(s).get_next() is not None) for s in tokens[:10]])
  searches.append({'text_sha256':sha('\n'.join(texts).encode()),'searches':found})
 assert searches[0]==searches[1]
 rows.append({'dpi':dpi,'old_bytes':old.stat().st_size,'new_bytes':new.stat().st_size,'decoded_streams_identical':True,'geometry_identical':True,'extraction_identical':True,'search_identical':True,'renders':results,'fonts':font,'qpdf':check.stdout+check.stderr,'search':searches[1]})
 print(dpi,'PASS',new.stat().st_size,flush=True)
(B/'serialization-verification.json').write_text(json.dumps(rows,indent=2))
