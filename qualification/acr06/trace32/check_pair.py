import json,sys,subprocess,hashlib,re,collections
from pathlib import Path
import pypdfium2 as pdf
from fontTools.ttLib import TTFont
q=Path('/data/coding/scanweave/qualification'); out=Path(sys.argv[1]);name=sys.argv[2]; a,b=[out/f'{name}-{arm}-1.pdf' for arm in ('main','candidate')]
mu=q/'acr06/local/mupdf-venv/bin/python';script=q/'acr06/trace32/extract_pdf.py';logs={}
for arm,file in zip(('main','candidate'),(a,b)):
 d=out/f'audit-{name}-{arm}';p=subprocess.run([str(mu),'-I',str(script),str(file),str(d)],capture_output=True,text=True); assert p.returncode==0,p.stderr
 p=subprocess.run(['/data/coding/scanweave/tools/dist/bin/qpdf','--check',str(file)],capture_output=True,text=True);logs[arm+' qpdf']=p.stdout+p.stderr;assert p.returncode==0,logs[arm+' qpdf']
 for font in d.glob('*.ttf'):
  p=subprocess.run(['/data/coding/scanweave/tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize',str(font),str(d/'sanitized.ttf')],capture_output=True,text=True); logs[arm+' ots']=p.stdout+p.stderr;assert p.returncode==0,logs[arm+' ots']
ss=[json.load(open(out/f'audit-{name}-{arm}/structure.json')) for arm in ('main','candidate')]
assert len(ss[0]['pages'])==len(ss[1]['pages'])
for i,(x,y) in enumerate(zip(ss[0]['pages'],ss[1]['pages'])):
 for k in ('content','images'):
  assert x[k]==y[k],(name,i,k,x[k],y[k])
print('PASS page content and images',flush=True)
afont=list((out/f'audit-{name}-main').glob('*.ttf')); bfont=list((out/f'audit-{name}-candidate').glob('*.ttf'))
afont=[f for f in afont if f.name!='sanitized.ttf'];bfont=[f for f in bfont if f.name!='sanitized.ttf'];assert len(afont)==len(bfont)==1
fa,fb=map(TTFont,(afont[0],bfont[0])); tables=sorted(set(fa.keys())|set(fb.keys())); diffs={}
for tag in tables:
 if tag=='GlyphOrder':continue
 x=fa.getTableData(tag);y=fb.getTableData(tag)
 if x!=y:diffs[tag]=[hashlib.sha256(x).hexdigest(),hashlib.sha256(y).hexdigest()]
for tag in ('glyf','CFF ','CFF2','hmtx','cmap','maxp','loca'):
 if tag in fa and tag in fb: assert fa.getTableData(tag)==fb.getTableData(tag),(name,tag)
for t in (fa,fb):
 h=t['head'];print('bounds',h.xMin,h.yMin,h.xMax,h.yMax)
print('table differences',json.dumps(diffs),flush=True)
for engine in ('poppler','pdfium'):
 texts=[]
 for file in (a,b):
  if engine=='poppler': texts.append(subprocess.check_output(['pdftotext','-layout',str(file),'-']))
  else:
   doc=pdf.PdfDocument(str(file));texts.append([page.get_textpage().get_text_range() for page in doc])
 assert texts[0]==texts[1],(name,engine,'extraction mismatch')
 print('PASS text',engine,flush=True)
print(json.dumps(logs),flush=True)
