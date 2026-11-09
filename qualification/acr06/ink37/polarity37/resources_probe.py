from pathlib import Path
import json,hashlib,pikepdf
base=Path('/data/coding/scanweave/qualification/acr06/local/ink37'); rows=[]
def h(x):return hashlib.sha256(x).hexdigest()
def content(page):
 x=page.obj['/Contents'];return b''.join(i.read_bytes() for i in x) if isinstance(x,pikepdf.Array) else x.read_bytes()
def decoded(o):
 try:return h(o.read_bytes())
 except pikepdf.PdfError:return None
def resources(page):
 r=page.obj['/Resources'];z={}
 if '/XObject' in r:
  for n,o in r['/XObject'].items():z['xobject:'+str(n)]={'raw':h(o.read_raw_bytes()),'decoded':decoded(o),'type':str(o.get('/Subtype'))}
 if '/Font' in r:
  for n,font in r['/Font'].items():
   desc=font
   if '/DescendantFonts' in font: desc=font['/DescendantFonts'][0]
   if '/FontDescriptor' in desc:
    fd=desc['/FontDescriptor']
    for key in ('/FontFile','/FontFile2','/FontFile3'):
     if key in fd:z['font:'+str(n)]={'raw':h(fd[key].read_raw_bytes()),'decoded':h(fd[key].read_bytes())}
   if '/ToUnicode' in font:z['unicode:'+str(n)]={'raw':h(font['/ToUnicode'].read_raw_bytes()),'decoded':h(font['/ToUnicode'].read_bytes())}
 return z
for doc in ('historical','financial','mixed','receipts','forms'):
 paths=[base/f'polarity37/{doc}-main.pdf',base/f'gate37/{doc}-candidate.pdf']
 if not paths[1].exists():continue
 a,b=[pikepdf.open(p) for p in paths]
 for i,(x,y) in enumerate(zip(a.pages,b.pages)):
  aa,bb=resources(x),resources(y); rows.append({'document':doc,'page':i+1,'content_main_sha256':h(content(x)),'content_candidate_sha256':h(content(y)),'content_identical':content(x)==content(y),'resources_main':aa,'resources_candidate':bb,'resources_identical':aa==bb})
 for p in (a,b):p.close()
Path('/data/coding/scanweave/qualification/acr06/ink37/polarity37/gate-resources.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:print(row['document'],row['page'],row['content_identical'],row['resources_identical'])
