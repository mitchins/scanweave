#!/usr/bin/env python3
"""Prepare aligned OCR geometry and color-only PDF counterfactuals for issue 33.

Coordinates are the source OCR raster. A vector match requires substantial
mutual overlap, and one OCR symbol can be assigned to at most one vector object.
Unmatched vector shows are left untouched in counterfactuals and counted.
"""
import ctypes, json, pathlib, re, sys, xml.etree.ElementTree as ET
from decimal import Decimal
import numpy as np
from PIL import Image
from skimage.transform import resize, AffineTransform
from skimage.feature import ORB, match_descriptors
from skimage.measure import ransac
from skimage.registration import phase_cross_correlation
import pikepdf, pypdfium2 as pdfium, pypdfium2.raw as raw

R=pathlib.Path('/data/coding/scanweave'); E=R/'qualification/acr06/ink33'; O=R/'qualification/acr06/local/ink33'; B=R/'qualification/acr06/local/bg150/baseline'; P=R/'qualification/pdf_packaging/groups'
G=['historical','financial','mixed','receipts','forms']
def baseline(g): return O/'forms-main.pdf' if g=='forms' else B/f'{g}.pdf'

def bbox(s):
 m=re.search(r'(?:x_bboxes|bbox) (\d+) (\d+) (\d+) (\d+)',s or '')
 return list(map(int,m.groups())) if m else None

def inter(a,b): return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
def area(a): return max(0,a[2]-a[0])*max(0,a[3]-a[1])
def lum(a): return np.asarray(a,dtype=np.float32)@np.array([.2126,.7152,.0722],dtype=np.float32)
def render(pdf,idx,w,h):
 pg=pdf[idx]; img=pg.render(scale=300/72,rev_byteorder=True).to_pil().convert('RGB'); pg.close()
 if abs(img.width-w)>1 or abs(img.height-h)>1: raise ValueError(f'page geometry mismatch {idx+1} render={img.size} OCR={(w,h)}')
 if img.size!=(w,h): img=img.resize((w,h),Image.Resampling.BILINEAR)
 return np.asarray(img)
def core_rgb(img,b):
 x0,y0,x1,y1=map(int,b); h,w=img.shape[:2]; x0=max(0,x0); y0=max(0,y0); x1=min(w,x1); y1=min(h,y1)
 if x1<=x0 or y1<=y0: return None
 pixels=img[y0:y1,x0:x1].reshape(-1,3); y=lum(pixels); bg=float(np.percentile(y,85)); ink=y<bg-10
 if ink.sum()<3: return None
 cutoff=np.quantile(y[ink],.30); core=pixels[ink & (y<=cutoff)]
 if not len(core): return None
 return np.median(core,axis=0).tolist()
def registration(source, adobe):
 """Estimate Adobe-to-source affine from independent image feature matches."""
 h,w=source.shape[:2]; scale=min(0.5,1000/max(h,w)); shape=(max(32,round(h*scale)),max(32,round(w*scale)))
 a=resize(lum(source)/255,shape,anti_aliasing=True); b=resize(lum(adobe)/255,shape,anti_aliasing=True)
 try:
  x=ORB(n_keypoints=2500,fast_threshold=.05); x.detect_and_extract(a)
  y=ORB(n_keypoints=2500,fast_threshold=.05); y.detect_and_extract(b)
  matches=match_descriptors(y.descriptors,x.descriptors,cross_check=True,max_ratio=.8)
  if len(matches)<10: raise ValueError('fewer than 10 descriptor matches')
  src=y.keypoints[matches[:,0]][:,::-1]/scale; dst=x.keypoints[matches[:,1]][:,::-1]/scale
  model,inliers=ransac((src,dst),AffineTransform,min_samples=3,residual_threshold=4,max_trials=1200,rng=33)
  if model is None or inliers.sum()<8: raise ValueError('fewer than 8 affine inliers')
  resid=model.residuals(src[inliers],dst[inliers]); mat=model.params
  if abs(np.linalg.det(mat[:2,:2])-1)>.15: raise ValueError('implausible affine scale')
  info={'method':'ORB-RANSAC affine','matches':len(matches),'inliers':int(inliers.sum()),'residual_px_p50':float(np.median(resid)),'residual_px_p90':float(np.percentile(resid,90)),'matrix':mat.tolist()}
 except (ValueError,RuntimeError) as e:
  shift,err,_=phase_cross_correlation(a,b,upsample_factor=10)
  dy,dx=(shift/scale).tolist(); mat=np.array([[1.,0.,dx],[0.,1.,dy],[0.,0.,1.]])
  info={'method':'translation fallback','reason':str(e),'phase_error':float(err),'matrix':mat.tolist()}
 inv=np.linalg.inv(mat); coeff=tuple(inv[:2,:].ravel()); aligned=np.asarray(Image.fromarray(adobe).transform((w,h),Image.Transform.AFFINE,coeff,resample=Image.Resampling.BILINEAR,fillcolor=(255,255,255)))
 return aligned,mat,info

def transform_boxes(objects,mat):
 for o in objects:
  x0,y0,x1,y1=o['box']; pts=np.array([[x0,y0,1],[x1,y0,1],[x0,y1,1],[x1,y1,1]])@mat.T
  o['box']=[float(pts[:,0].min()),float(pts[:,1].min()),float(pts[:,0].max()),float(pts[:,1].max())]

def get_objects(pg,W,H):
 pw,ph=pg.get_size(); out=[]
 for obj in pg.get_objects():
  if obj.type!=raw.FPDF_PAGEOBJ_TEXT: continue
  mode=raw.FPDFTextObj_GetTextRenderMode(obj.raw)
  if mode not in (0,2,4,6): continue
  x0,y0,x1,y1=obj.get_bounds(); b=[x0*W/pw,(ph-y1)*H/ph,x1*W/pw,(ph-y0)*H/ph]
  c=[ctypes.c_uint() for _ in range(4)]; ok=raw.FPDFPageObj_GetFillColor(obj.raw,*[ctypes.byref(x) for x in c]); out.append({'box':b,'rgba':[x.value for x in c] if ok else None,'mode':mode})
 return out
def chars_from_hocr(s):
 root=ET.fromstring(s); lines=[]
 for node in root.iter():
  if 'ocr_line' not in node.attrib.get('class','').split(): continue
  lb=bbox(node.get('title')); words=[]
  for word in node.iter():
   if 'ocrx_word' not in word.attrib.get('class','').split(): continue
   cc=[]
   for c in word.iter():
    if 'ocrx_cinfo' in c.attrib.get('class','').split():
     b=bbox(c.get('title')); t=''.join(c.itertext())
     if b and area(b)>0 and t.strip(): cc.append({'box':b,'text':t})
   if cc: words.append({'id':word.get('id'),'box':bbox(word.get('title')),'chars':cc})
  if words and lb: lines.append({'id':node.get('id'),'box':lb,'words':words})
 return lines
def ins_color(rgb):
 return pikepdf.ContentStreamInstruction([Decimal(str(round(float(x)/255,6))) for x in rgb],pikepdf.Operator('rg'))

def process(g):
 print('start',g,flush=True)
 base=baseline(g); rep=json.loads(pathlib.Path(str(base)+'.json').read_text()); sw=pdfium.PdfDocument(str(base)); src=pdfium.PdfDocument(str(P/f'{g}-input.pdf')); ad=pdfium.PdfDocument(str(P/f'{g}-adobe.pdf'))
 if not(len(rep['pages'])==len(sw)==len(src)==len(ad)): raise ValueError(f'{g} page counts differ')
 pda=pikepdf.open(base); pdb=pikepdf.open(base); pdc=pikepdf.open(base); summary=[]
 for pi,p in enumerate(rep['pages']):
  W,H=p['raster_width'],p['raster_height']; dirs=O/'renders'/g; dirs.mkdir(parents=True,exist_ok=True)
  imgs={}
  for label,doc in [('source',src),('scanweave',sw),('adobe',ad)]:
   arr=render(doc,pi,W,H)
   if label=='adobe':
    Image.fromarray(arr).save(dirs/f'{pi+1:02d}-adobe-raw.png'); arr,reg,reginfo=registration(imgs['source'],arr)
   imgs[label]=arr; Image.fromarray(arr).save(dirs/f'{pi+1:02d}-{label}.png')
  lines=chars_from_hocr(p['hocr']); symbols=[]
  for li,line in enumerate(lines):
   for wi,word in enumerate(line['words']):
    for ci,c in enumerate(word['chars']):
     c['source_rgb']=core_rgb(imgs['source'],c['box']); c['vector']=False; c['object']=None; symbols.append((li,wi,ci,c))
  sp=sw[pi]; ap=ad[pi]; sv=get_objects(sp,W,H); av=get_objects(ap,W,H); sp.close(); ap.close(); transform_boxes(av,reg)
  # Greedy highest-overlap bipartite assignment. Record unmatched objects.
  candidates=[]
  for oi,o in enumerate(sv):
   oa=area(o['box'])
   if oa<=0: continue
   for si,(_,_,_,c) in enumerate(symbols):
    a=inter(o['box'],c['box']); ca=area(c['box'])
    if a/oa>=.35 and a/ca>=.12: candidates.append((a/(oa+ca-a),oi,si))
  usedo=set(); useds=set()
  for score,oi,si in sorted(candidates,reverse=True):
   if oi in usedo or si in useds: continue
   usedo.add(oi); useds.add(si); li,wi,ci,c=symbols[si]; c['vector']=True; c['object']=oi; sv[oi]['symbol']=[li,wi,ci]; sv[oi]['iou']=score
  for line in lines:
   cols=[c['source_rgb'] for word in line['words'] for c in word['chars'] if c['source_rgb'] is not None]
   line['rgb']=np.median(cols,axis=0).tolist() if cols else None
   for word in line['words']:
    cols=[c['source_rgb'] for c in word['chars'] if c['source_rgb'] is not None]
    word['rgb']=np.median(cols,axis=0).tolist() if cols else None
  # Match Adobe text objects by maximal overlapping OCR line/word/character.
  for o in av:
   hits=[(inter(o['box'],c['box']),li,wi,ci) for li,wi,ci,c in symbols if inter(o['box'],c['box'])>0]
   if hits:
    _,li,wi,ci=max(hits); o['symbol']=[li,wi,ci]
  # Assign every object to an OCR word using the closest word box, including
  # weak character matches; record those as geometric fallback, not measured vectors.
  words=[(li,wi,word) for li,line in enumerate(lines) for wi,word in enumerate(line['words']) if word['box']]
  def dist_box(point,b):
   x,y=point; return max(b[0]-x,0,x-b[2])**2+max(b[1]-y,0,y-b[3])**2
  for o in sv:
   if 'symbol' in o: li,wi,_=o['symbol']; o['target']=[li,wi]; o['target_method']='character_overlap'
   elif words:
    b=o['box']; point=((b[0]+b[2])/2,(b[1]+b[3])/2)
    li,wi,_=min(words,key=lambda t:dist_box(point,t[2]['box'])); o['target']=[li,wi]; o['target_method']='nearest_word'
  # Adobe spatial color transfer is an observable-output proxy, not Adobe's algorithm.
  for o in sv:
   if 'target' not in o: continue
   li,wi=o['target']; b=o['box']; point=((b[0]+b[2])/2,(b[1]+b[3])/2)
   cand=[a for a in av if a.get('rgba') and 'symbol' in a and a['symbol'][0]==li]
   if not cand: cand=[a for a in av if a.get('rgba')]
   if cand: o['adobe_rgb']=min(cand,key=lambda a:dist_box(point,a['box']))['rgba'][:3]
  instructions=list(pikepdf.parse_content_stream(pda.pages[pi])); visible_show=[]; tr=0; stack=[]
  for idx,ins in enumerate(instructions):
   op=str(ins.operator)
   if op=='q': stack.append(tr)
   elif op=='Q' and stack: tr=stack.pop()
   elif op=='Tr': tr=int(ins.operands[0])
   elif op in ('Tj','TJ',"'",'"') and tr in (0,2,4,6): visible_show.append(idx)
  if len(visible_show)!=len(sv): raise ValueError(f'{g} page {pi+1}: visible PDF shows {len(visible_show)} != PDFium objects {len(sv)}')
  # Insert an RGB before and restore original color immediately after each visible show.
  # All ScanWeave pages audited have exactly one visible DeviceRGB color.
  for mode,pdf in [('a',pda),('b',pdb),('c',pdc)]:
   byidx=dict(zip(visible_show,sv)); out=[]; changed=0
   for idx,ins in enumerate(instructions):
    o=byidx.get(idx); rgb=None
    if o and 'target' in o:
     li,wi=o['target']; line=lines[li]; word=line['words'][wi]
     rgb=line['rgb'] if mode=='a' else word['rgb'] if mode=='b' else o.get('adobe_rgb')
    if rgb is not None and o.get('rgba'):
     out.append(ins_color(rgb)); out.append(ins); out.append(ins_color(o['rgba'][:3])); changed+=1
    else: out.append(ins)
   pdf.pages[pi].Contents=pdf.make_stream(pikepdf.unparse_content_stream(out))
   if mode=='a': na=changed
   elif mode=='b': nb=changed
   else: nc=changed
  (O/'maps'/g).mkdir(parents=True,exist_ok=True)
  (O/'maps'/g/f'{pi+1:02d}.json').write_text(json.dumps({'width':W,'height':H,'lines':lines,'scan_objects':sv,'adobe_objects':av},separators=(',',':')))
  summary.append({'page':pi+1,'ocr_lines':len(lines),'symbols':len(symbols),'scan_visible':len(sv),'mapped_visible':len(usedo),'adobe_visible':len(av),'a_changed':na,'b_changed':nb,'c_changed':nc,'registration':reginfo})
  print(g,pi+1,summary[-1],flush=True)
 for mode,pdf in [('a',pda),('b',pdb),('c',pdc)]: pdf.save(O/f'{g}-cf-{mode}.pdf'); pdf.close()
 (E/f'prepare-{g}.json').write_text(json.dumps(summary,indent=2)+'\n'); print('done',g,flush=True)

if __name__=='__main__':
 for g in (sys.argv[1:] or G): process(g)
