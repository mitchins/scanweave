import json,hashlib,subprocess,tempfile,sys
from pathlib import Path
import pikepdf,pypdfium2 as pdfium
from PIL import Image
B=Path(__file__).resolve().parent;R=B.parents[1];P=R/'qualification/pdf_packaging';sys.path.insert(0,str(R/'qualification'));from tools_env import qpdf_bin,qpdf_env,ots_bin
sha=lambda b:hashlib.sha256(b).hexdigest();frozen=json.loads((P/'serialization-verification.json').read_text());out=[]
for dpi in [300,600]:
 old=P/str(dpi)/'final.pdf';new=B/str(dpi)/'final.pdf';a=pikepdf.open(old);b=pikepdf.open(new);expected=next(r for r in frozen if r['dpi']==dpi);record={'dpi':dpi,'old_bytes':old.stat().st_size,'new_bytes':new.stat().st_size,'renders':[]}
 assert len(a.pages)==len(b.pages)==8
 for x,y in zip(a.pages,b.pages):assert list(x.MediaBox)==list(y.MediaBox)
 for flag in ['-raw','-layout']:assert subprocess.check_output(['pdftotext',flag,str(old),'-'])==subprocess.check_output(['pdftotext',flag,str(new),'-'])
 def payloads(q):
  return sorted(sha(o.read_bytes()) for o in q.objects if isinstance(o,pikepdf.Stream) and o.get('/Subtype')!=pikepdf.Name.Image and o.get('/Type') not in [pikepdf.Name.ObjStm,pikepdf.Name.XRef])
 assert payloads(a)==payloads(b),'decoded font/maps/content changed'
 for renderer in ['poppler','pdfium']:
  for i in range(8):
   if renderer=='pdfium':im=pdfium.PdfDocument(str(new))[i].render(scale=dpi/72).to_pil().convert('RGB')
   else:
    with tempfile.TemporaryDirectory() as t:
     root=Path(t)/'r';subprocess.run(['pdftoppm','-f',str(i+1),'-l',str(i+1),'-singlefile','-r',str(dpi),'-png',str(new),str(root)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);im=Image.open(root.with_suffix('.png')).convert('RGB').copy()
   digest=sha(im.tobytes());previous=next(r['sha256'] for r in expected['renders'] if r['renderer']==renderer and r['page']==i);assert digest==previous,(dpi,renderer,i);record['renders'].append({'page':i,'renderer':renderer,'sha256':digest,'pixel_identical_to_frozen':True});print(dpi,renderer,i,'PASS',flush=True)
 v=subprocess.run([qpdf_bin(),'--check',str(new)],env=qpdf_env(),capture_output=True,text=True);assert v.returncode==0;record['qpdf']=v.stdout+v.stderr
 record['fonts']=[]
 with tempfile.TemporaryDirectory() as t:
  for o in b.objects:
   if isinstance(o,pikepdf.Dictionary) and '/FontFile2' in o:
    data=o.FontFile2.read_bytes();p=Path(t)/'font.ttf';p.write_bytes(data);v=subprocess.run([ots_bin(),str(p)],capture_output=True,text=True);assert v.returncode==0;record['fonts'].append({'sha256':sha(data),'ots_status':v.returncode})
 texts=[]
 for path in [old,new]:texts.append([page.get_textpage().get_text_range() for page in pdfium.PdfDocument(str(path))])
 assert texts[0]==texts[1];record['pdfium_text_equal']=True;record['decoded_streams_equal']=True;out.append(record)
(B/'synthetic-verification.json').write_text(json.dumps(out,indent=2))
