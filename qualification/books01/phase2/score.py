#!/usr/bin/env python3
"""Score one existing page/row using the pilot routines; writes no OCR/GT text."""
import collections,ctypes,hashlib,json,math,os,pathlib,random,re,subprocess,sys,time,traceback
import numpy as np,pypdfium2 as pdfium,pikepdf
from PIL import Image
from lxml import html
from skimage.metrics import structural_similarity
from skimage.color import rgb2lab,deltaE_ciede2000
from skimage.feature import match_descriptors
from skimage.measure import ransac
from skimage.transform import SimilarityTransform
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot';D=B/'phase2';id,row=sys.argv[1:3];key=id.split('/')[-1];locks=json.loads((P/'sources.lock.json').read_text())['pages'];lock=locks[id];dpi=int(lock['resolved_dpi']);run=json.loads((D/'runs'/key/'runs.json').read_text());src=pathlib.Path(run['rows']['src']['path']);dest=D/'metrics'/key/(row+'.json');dest.parent.mkdir(parents=True,exist_ok=True);entry={'id':id,'row':row,'dpi':dpi,'dpi_confidence':lock['dpi_evidence']['confidence'],'source_type':lock['source_type']};t0=time.monotonic()
if row=='adobe-E':
 entry['adobe_label']='Acrobat default OCR language (not matched); no Fraktur support; page straightened (deskew)'
 path=B/'runs'/('adobe' if id in json.loads((P/'corpus.frozen.json').read_text())['pilot_6'] else 'adobe-p2')/(key+'.adobe.pdf')
else:path=pathlib.Path(run['rows'].get(row,{}).get('path','/nonexistent'))
if not path.is_file():dest.write_text(json.dumps({**entry,'status':'missing','path':str(path)},indent=2));sys.exit()
# Load trusted pilot functions without running their pilot batch loops.
def load(file,marker):
 code=file.read_text();ns={'__file__':str(file)};exec(compile(code[:code.index(marker)],str(file),'exec'),ns);return ns
textlib=load(Q/'text_metrics.py','result={}\nfor id in ids:');line=load(Q/'phase1b/line_ocr.py','out={}\nfor id in ids:');obj=load(Q/'object_sizes.py','for id,x in runs.items():');reg=load(Q/'phase1b/register.py','tasks=[(id,renderer,dpi)');vis=load(Q/'phase1b/fidelity.py','out={};start=time.monotonic()');calc=load(Q/'phase1b/calibrate.py','records=[]');cal=json.loads((Q/'results/phase1b/calibration.json').read_text())['detectors'];out=D/'renders'/key/row;out.mkdir(parents=True,exist_ok=True)
entry['status']='ok';entry['size']=obj['classify'](path);entry['size_ratio']=path.stat().st_size/src.stat().st_size
# Preserve image properties without pretending the largest image is always a background.
with pikepdf.open(path) as pdf:
 imgs=[]
 for o in pdf.objects:
  if isinstance(o,pikepdf.Stream) and o.get('/Subtype')==pikepdf.Name('/Image'):
   imgs.append({'width':int(o.get('/Width',0)),'height':int(o.get('/Height',0)),'bytes':len(o.read_raw_bytes()),'filter':str(o.get('/Filter','')),'mask':bool(o.get('/ImageMask',False))})
 entry['images']=imgs
# Timed 150 DPI render: pilot worker warms once and times five.
entry['render_150']={}
for renderer in ['pdfium','poppler','mupdf']:
 png=out/(renderer+'-150.png');cmd=[sys.executable,'-I',str(Q/'render_worker.py'),str(path),renderer,'150',str(png)]
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=240,env={**os.environ,'TMPDIR':str(B/'tmp'),'OMP_THREAD_LIMIT':'1','OPENBLAS_NUM_THREADS':'1'});entry['render_150'][renderer]=json.loads(p.stdout) if p.returncode==0 else {'error':p.stderr[-1000:]}
 except Exception as e:entry['render_150'][renderer]={'error':repr(e)}
# PDFium source-DPI native render.
native=out/'pdfium-native.png';doc=pdfium.PdfDocument(str(path));page=doc[0];tp=page.get_textpage();page.render(scale=dpi/72).to_pil().convert('RGB').save(native);source=D/'renders'/key/'src'/'pdfium-native.png'
if row=='src':source=native
if not source.exists():raise RuntimeError('source render must be scored first')
a=Image.open(source).convert('RGB');im=Image.open(native).convert('RGB');arr=np.asarray(im);ref=np.asarray(a);g={'status':'unaccepted','reason':None,'rotation_degrees':None,'scale_x':None,'scale_y':None,'translation_px':None};eq=arr.shape==ref.shape and np.array_equal(arr,ref)
try:
 if eq:tr=SimilarityTransform();g.update(status='accepted',method='exact pixel identity',rotation_degrees=0.,scale_x=1.,scale_y=1.,translation_px=[0.,0.],inlier_fraction=None,residual_p95_px_150_equivalent=None)
 else:
  sp,sd=reg['features'](a,dpi);op,od=reg['features'](im,dpi);m=match_descriptors(od,sd,cross_check=True,max_ratio=.8)
  if len(m)<8:raise ValueError('fewer than eight matches')
  x=op[m[:,0]];y=sp[m[:,1]];model,ins=ransac((x,y),SimilarityTransform,min_samples=3,residual_threshold=3,max_trials=1200,rng=0);res=np.linalg.norm(model(x)-y,axis=1)[ins];n=int(ins.sum());frac=n/len(m);med=float(np.median(res));p95=float(np.percentile(res,95));quadrants=len({(int(x>=a.width*150/dpi/2),int(y>=a.height*150/dpi/2)) for x,y in y[ins]});angle=float(np.degrees(model.rotation));sc=float(model.scale);trans=model.translation*dpi/150;g.update(method='SIFT global similarity',rotation_degrees=angle,scale_x=sc,scale_y=sc,translation_px=trans.tolist(),inlier_count=n,inlier_fraction=frac,residual_median_px_150_equivalent=med,residual_p95_px_150_equivalent=p95,quadrants_covered=quadrants)
  if n<8 or frac<.60 or quadrants<3 or med>3 or p95>6 or abs(angle)>2 or not .97<=sc<=1.03:raise ValueError('fit failed predeclared criteria')
  tr=SimilarityTransform(scale=sc,rotation=model.rotation,translation=trans);g['status']='accepted'
except Exception as e:g['reason']=str(e)
with pikepdf.open(src) as spdf,pikepdf.open(path) as opdf:
 def boxes(pdf):
  p=pdf.pages[0];return {'media':[float(x) for x in p.mediabox],'crop':[float(x) for x in p.cropbox],'rotation':int(p.obj.get('/Rotate',0))}
 g['source_page_boxes']=boxes(spdf);g['output_page_boxes']=boxes(opdf);g['page_box_changed']=g['source_page_boxes']!=g['output_page_boxes']
entry['geometry']=g
ms=vis['masks'](id,a.size);sg=np.asarray(a.convert('L'));si=sg<128;sl=vis['L'](ref)
def fidelity(dst):
 da=np.asarray(dst.convert('RGB'));dg=np.asarray(dst.convert('L'));hh,ww=dg.shape;src0=ref[:hh,:ww];sink=si[:hh,:ww];di=dg<128;dl=np.abs(sl[:hh,:ww]-vis['L'](da));_,sm=structural_similarity(sg[:hh,:ww],dg,data_range=255,full=True);out={}
 for name,mask in ms.items():
  mask=mask[:hh,:ww];n=int(mask.sum());i=int((sink&mask).sum());p=int((di&mask).sum());tp0=int((sink&di&mask).sum());z=dl[mask];v={'pixels':n,'ssim':float(sm[mask].mean()) if n else None,'ink_recall':tp0/i if i else None,'ink_precision':tp0/p if p else None,'mean_abs_delta_L':float(z.mean()) if n else None}
  if name=='illustration' and n:
   aa=src0[mask];bb=da[mask];count=0;total=0.
   for off in range(0,len(aa),100000):
    dd=deltaE_ciede2000(rgb2lab(aa[off:off+100000].reshape(-1,1,3)),rgb2lab(bb[off:off+100000].reshape(-1,1,3)));total+=float(dd.sum());count+=dd.size
   v['deltaE2000_mean']=total/count if count else None
  out[name]=v
 return out
entry['native_fidelity']=fidelity(im.crop((0,0,min(a.width,im.width),min(a.height,im.height)))) if abs(a.width-im.width)<=1 and abs(a.height-im.height)<=1 else {'status':'dimension_mismatch','source':a.size,'output':im.size}
if a.size!=im.size:entry['native_overlap']={'source':list(a.size),'output':list(im.size),'overlap':[min(a.width,im.width),min(a.height,im.height)],'policy':'pilot common top-left grid; only dimensions within one pixel are scored'}
if g['status']=='accepted':
 if eq:aligned=im
 else:
  inv=tr.inverse.params;aligned=im.transform(a.size,Image.Transform.AFFINE,tuple(float(v) for v in [inv[0,0],inv[0,1],inv[0,2],inv[1,0],inv[1,1],inv[1,2]]),resample=Image.Resampling.BICUBIC,fillcolor='white')
 aligned.save(out/'pdfium-aligned.png');entry['aligned_fidelity']=fidelity(aligned)
# Native text scores and conditional literal + diplomatic search.
gt,gtobj=textlib['gt'](id);extracted=tp.get_text_range();entry['text']={'empty':not bool(extracted.strip()),'scores':textlib['score'](gt,extracted)};hpath=D/'runs'/key/'selected.hocr'
if hpath.exists():
 root=html.parse(str(hpath));frozen=[];words=[]
 for el in root.xpath('//*[@class="ocr_line" or @class="ocr_caption" or @class="ocr_header" or @class="ocr_textfloat"]'):
  m=re.search(r'\bbbox (\d+) (\d+) (\d+) (\d+)',el.get('title',''))
  if not m:continue
  ws=[''.join(t.strip() for t in w.itertext() if t.strip()) for w in el.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]')];words.extend(ws);frozen.append({'box':list(map(int,m.groups())),'text':' '.join(ws)})
 nl=line['norm'];allgt=' '.join(x['text'] for x in (gtobj['lines'] or gtobj['regions']) if x.get('text'));allwords=sorted(set(re.findall(r'\w{4,}',nl(allgt))));rnd=random.Random(int.from_bytes(hashlib.sha256(('books01-search-v1/'+id).encode()).digest()[:8],'big'));positive=rnd.sample(allwords,min(20,len(allwords)));recognized=set(re.findall(r'\w{4,}',nl(' '.join(words))));subset=[w for w in positive if w in recognized];tokens=re.findall(r'[^\W_]+(?:[\u0300-\u036f]+)?',extracted,re.UNICODE)
 def search(q):
  try:s=tp.search(q,match_case=False);ok=s.get_next() is not None;s.close();return ok
  except Exception:return False
 hits=alt=0
 for w in subset:
  hit=search(w);hits+=hit;alt+=bool(hit or any(nl(t)==w and search(t) for t in tokens))
 entry['search']={'recognized_words':len(subset),'literal_hits':hits,'diplomatic_variant_hits':alt,'variant':'literal or a text-layer token with identical reading-normalised form','limitation':'long-s normalised query may fail literal search'};entry['frozen_hocr_scores']=textlib['score'](gt,' '.join(words));ref_lines,_=line['gt'](id)
 if g['status']=='accepted':
  pdf_lines,_=line['pdf_lines'](page,dpi,g);entry['line_ocr']={}
  for mode in ['reading','diplomatic']:
   line['norm']=nl if mode=='reading' else lambda s:textlib['norm'](s,False)
   try:
    lines,part=line['locked_pdf_lines'](frozen,tp) if row in ['sw-E','mrc-M'] else (pdf_lines,None);s=line['score'](ref_lines,lines);same=line['same_gt_comparison'](ref_lines,frozen,lines)
    if part is not None:s['kendall_tau']=None
    entry['line_ocr'][mode]={'line_metrics':s,'same_gt':same,'partition':part}
   except Exception as e:entry['line_ocr'][mode]={'error':repr(e)}
  line['norm']=nl
 # Existing calibrated detector scores on aligned output, using selected OCR word boxes.
 if g['status']=='accepted' and row!='src':
  words_boxes=[]
  for w in root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]'):
   m=re.search(r'\bbbox (\d+) (\d+) (\d+) (\d+)',w.get('title',''))
   if m:words_boxes.append(list(map(int,m.groups())))
  counts=collections.Counter(); calc['gtcache'].clear()
  for box in words_boxes:
   val=calc['calc'](a,aligned,box,id)
   if val:
    for det in ['glyph_shape','missing_ink','spurious_ink']:
     v=val[det];threshold=cal[det]['threshold'];counts[det]+=bool(v is not None and threshold is not None and v>=threshold)
  entry['detectors']={'status':'automated suspicions, unreviewed','word_boxes':len(words_boxes),'counts':dict(counts),'limitation':'word-box detectors; no confirmation; illustration and border tile counts unavailable in this pass'}
entry['elapsed_seconds']=time.monotonic()-t0;dest.write_text(json.dumps(entry,indent=2,allow_nan=False)+'\n');print(key,row,'done',round(entry['elapsed_seconds'],1),flush=True)
