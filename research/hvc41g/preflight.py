#!/usr/bin/env python3
"""Inspect the exact complete graphics PDF and freeze its bytes on success."""
import ast,hashlib,json,os,pathlib,shutil,subprocess,sys,tempfile
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41g';L=R/'local/hvc41g';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41G_PREFLIGHT')!='1':sys.exit('preflight switch required')
ledger=R/'hvc41e/review-decisions.json';base=R/'local/ink33r/historical.pdf';prev=R/'local/hvc41e/final/historical-composed.pdf';candidate=L/'historical-preflight.pdf';side=R/'local/ink33r/historical.pdf.json';bld=json.loads((E/'preflight-build.json').read_text())
if sha(ledger.read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha(base.read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b' or sha(prev.read_bytes())!='9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0' or sha(candidate.read_bytes())!=bld['sha256']:sys.exit('input hash mismatch')
s=json.loads(side.read_text());source=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');w,h=source.size
if sha((R.parent/'pdf_packaging/groups/historical-input.pdf').read_bytes())!=s['input_sha256'] or any(sha(p['hocr'].encode())!=p['hocr_sha256'] for p in s['pages']) or [w,h]!=[s['pages'][0]['raster_width'],s['pages'][0]['raster_height']] or sha(f'SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n'.encode()+source.tobytes())!=s['pages'][0]['pixel_sha256'] or sha(source.tobytes())!=s['pages'][0]['native_source']['decoded_rgb_sha256']:sys.exit('OCR or source mismatch')
sys.path.insert(0,str(R/'ink33r'));from prepare import chars_from_hocr
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'hvc41d'));from pdf_font import pdf_path
rows=[r for r in json.loads(ledger.read_text()) if r['decision']=='accept'];assert len(rows)==38
outlines=json.loads((R/'local/hvc41b/interior/p000001-outlines.json').read_text())['outlines'];words=[word for line in chars_from_hocr(s['pages'][0]['hocr']) for word in line['words']];queries=['Bacharias','Boect!','Wud','Dat','fram','Ber)','den']
for r in rows:
 word=''.join(z['text'] for z in words[r['word_index']]['chars']).strip()
 if word and word not in queries:queries.append(word)
def txt(path):
 d=pdfium.PdfDocument(str(path));out=[]
 for p in d:
  t=p.get_textpage();out.append(t.get_text_range().encode());t.close();p.close()
 d.close();return out
def search(path,word):
 d=pdfium.PdfDocument(str(path));p=d[0];t=p.get_textpage();ss=t.search(word);out=[]
 while (x:=ss.get_next()) is not None:out.append(list(x))
 ss.close();t.close();p.close();d.close();return out
def pop(path,i,layout):return subprocess.check_output(['pdftotext','-f',str(i),'-l',str(i),'-enc','UTF-8']+(['-layout'] if layout else [])+[str(path),'-'])
def mu(path,i):
 code='import pymupdf,sys;d=pymupdf.open(sys.argv[1]);sys.stdout.buffer.write(d[int(sys.argv[2])-1].get_text().encode())';return subprocess.check_output(['/data/coding/scanweave/qualification/acr06/local/mupdf-venv/bin/python','-I','-c',code,str(path),str(i)])
with tempfile.TemporaryDirectory(prefix='hvc41g-preflight-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=L/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(side)
 if marker.exists():sys.exit('OCR marker exists')
 bt=txt(base);ct=txt(candidate);pages=[]
 for i in range(1,6):
  p0=pop(base,i,False);p1=pop(candidate,i,False);l0=pop(base,i,True);l1=pop(candidate,i,True);m0=mu(base,i);m1=mu(candidate,i);pages.append({'page':i,'pdfium_equal':bt[i-1]==ct[i-1],'pdfium_sha256':sha(bt[i-1]),'poppler_equal':p0==p1,'poppler_sha256':sha(p0),'poppler_layout_equal':l0==l1,'poppler_layout_sha256':sha(l0),'mupdf_equal':m0==m1,'mupdf_sha256':sha(m0)})
 searches=[{'query':q,'baseline':search(base,q),'candidate':search(candidate,q)} for q in queries]
 with pikepdf.open(base) as a,pikepdf.open(candidate) as b,pikepdf.open(prev) as e:
  if len(a.pages)!=5 or len(b.pages)!=5:sys.exit('page count mismatch')
  pa=a.pages[0];pb=b.pages[0];former=e.pages[0].Resources.Pattern['/Research41E'];lines=former.read_bytes().decode().splitlines();font=former.Resources.Font.FR;new=pb.Resources.XObject['/ResearchPaths'];streams=[pb.Contents[1],pb.Contents[2],new];forbidden={'BT','ET','Tj','TJ',"'",'"','Tf'};operations=[]
  for i,stream in enumerate(streams):
   ops=[str(z.operator) for z in pikepdf.parse_content_stream(stream)];operations.append({'stream':['patch','invocation','form'][i],'operators':sorted(set(ops)),'operator_count':len(ops),'sha256_decoded':sha(stream.read_bytes()),'forbidden':sorted(forbidden.intersection(ops))})
  if any(x['forbidden'] for x in operations) or '/Font' in new.Resources or set(map(str,new.Resources.keys())):sys.exit('form introduces forbidden resources or text')
  if set(map(str,pb.Resources.Font.keys()))!=set(map(str,pa.Resources.Font.keys())) or set(map(str,pb.Resources.XObject.keys()))!=set(map(str,pa.Resources.XObject.keys()))|{'/ResearchPaths'}:sys.exit('new resource mismatch')
  # Expected emitted commands are regenerated from frozen outlines and the accepted C algorithm.
  tree=ast.parse((pathlib.Path(__file__).parent/'build.py').read_text());funcs=ast.Module(body=[x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name in ('quant','simplify')],type_ignores=[]);import re
  namespace={'np':np,'w':w,'h':h,'num':re.compile(r'(?<![A-Za-z0-9_.])[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?')};exec(compile(funcs,'build_functions','exec'),namespace);pw=float(pb.MediaBox[2]);ph=float(pb.MediaBox[3]);expected=[];glyphs=[]
  for j,r in enumerate(rows,1):
   g=outlines[r['proposal']];raw=pdf_path(g['path_svg']);colour=' '.join(f'{v/255:.8f}' for v in r['fill_rgb']);matrix=' '.join(str(v) for v in g['matrix']);assert font.CharProcs[f'/g{j}'].read_bytes()==('2048 0 d0 '+raw+' f').encode() and lines[j-1]==f'BT /FR 1 Tf {colour} rg {matrix} Tm <{j:02x}> Tj ET' and g['symbol']==r['symbol_id']
   q,_=namespace['quant'](raw);q,_,_=namespace['simplify'](q,g['matrix'],pw,ph);a0,b0,c0,d0,x,y=g['matrix'];mat=[a0/2048,b0/2048,c0/2048,d0/2048,x,y];expected.append('q '+colour+' rg '+' '.join(str(v) for v in mat)+' cm '+q+' f Q')
   masks={}
   for key in ('patch','owner'):
    spec=r['masks'][key];path=pathlib.Path(spec['path']);assert sha(path.read_bytes())==spec['sha256'];masks[key]=np.asarray(Image.open(path).convert('L'))>0
   assert not (masks['patch']&~masks['owner']).any();glyphs.append({'proposal':r['proposal'],'symbol':r['symbol_id'],'identity':r['claude_identity'],'matrix':g['matrix'],'reference_box':r['reference_box'],'patch_outside_owned':0,'owner_sha256':r['masks']['owner']['sha256'],'patch_sha256':r['masks']['patch']['sha256']})
  if new.read_bytes()!=('\n'.join(expected)).encode():sys.exit('actual form differs from 38 frozen commands')
  structure=[]
  for i,(x,y) in enumerate(zip(a.pages,b.pages),1):
   old=x.Contents;current=y.Contents[0] if i==1 else y.Contents;images=all(sha(v.read_raw_bytes())==sha(y.Resources.XObject[k].read_raw_bytes()) for k,v in x.Resources.XObject.items() if str(v.get('/Subtype'))=='/Image');structure.append({'page':i,'raw_content_equal':sha(old.read_raw_bytes())==sha(current.read_raw_bytes()),'decoded_content_equal':sha(old.read_bytes())==sha(current.read_bytes()),'source_images_equal':images})
  representation_sha=sha(b'\0'.join(z.read_bytes() for z in streams))
 if not all(all(r[k] for k in ('pdfium_equal','poppler_equal','poppler_layout_equal','mupdf_equal')) for r in pages) or not all(x['baseline']==x['candidate'] for x in searches) or not all(x['raw_content_equal'] and x['decoded_content_equal'] and x['source_images_equal'] for x in structure) or marker.exists():sys.exit('preflight check failed')
 # Freeze only the exact file whose bytes were just tested.
 frozen=L/'historical-frozen.pdf';shutil.copyfile(candidate,frozen);digest=sha(candidate.read_bytes());assert sha(frozen.read_bytes())==digest and digest==bld['sha256']
 result={'pdf_sha256':digest,'representation_sha256':representation_sha,'frozen_path':str(frozen),'ledger_sha256':sha(ledger.read_bytes()),'operations':operations,'pages':pages,'searches':searches,'glyphs':glyphs,'structure':structure,'ocr_stub_not_invoked':True}
 (E/'preflight.json').write_text(json.dumps(result,indent=2)+'\n');(E/'freeze.json').write_text(json.dumps({'pdf_sha256':digest,'representation_sha256':representation_sha,'glyph_count':len(glyphs),'search_query_count':len(queries)},indent=2)+'\n');print('PREFLIGHT PASS',digest,'searches',len(queries),flush=True)
