#!/usr/bin/env python3
"""Validate existing completed PDF font text objects against padded source references."""
import pathlib,json,sys,io,ctypes,hashlib,math
import numpy as np,pikepdf,pypdfium2 as pdfium,pypdfium2.raw as raw
from PIL import Image,ImageDraw
sys.path.insert(0,'/data/coding/scanweave/qualification/acr06/ink33r')
from prepare import chars_from_hocr
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41c';L=R/'local';P=L/'hvc41c/panels';P.mkdir(parents=True,exist_ok=True);cal=json.loads((E/'calibration-words.json').read_text());wt=np.array([.2126,.7152,.0722]);allrows=[];index=[]
for name,docpath,pageno in [('white',L/'hvc41b/controls/control/white/baseline.pdf',1),('financial-01',L/'ink33r/financial.pdf',1),('financial-02',L/'ink33r/financial.pdf',2)]:
 if name=='white':
  inp=pikepdf.open(L/'ink37/controls/white.pdf');obj=next(o for o in inp.pages[0].Resources.XObject.values() if str(o.get('/Subtype'))=='/Image');src=np.asarray(Image.open(io.BytesIO(obj.read_raw_bytes())).convert('RGB'));inp.close();meta=json.loads((L/'ink37/control-measured/white.pdf.json').read_text())['pages'][0]
 else:src=np.asarray(Image.open(L/'ink33r/renders/financial'/f'{pageno:02}-source.png').convert('RGB'));meta=json.loads((L/'ink33r/financial.pdf.json').read_text())['pages'][pageno-1]
 h,w=src.shape[:2];lum=src.astype(float)@wt;words=[word for line in chars_from_hocr(meta['hocr']) for word in line['words']];admitted={x['word_index']:x for x in cal if x['control']==name and x['admitted']};doc=pdfium.PdfDocument(str(docpath));pg=doc[pageno-1];pw,ph=pg.get_size();candidates=[]
 for oi,obj in enumerate(pg.get_objects()):
  if obj.type!=raw.FPDF_PAGEOBJ_TEXT or raw.FPDFTextObj_GetTextRenderMode(obj.raw) not in (0,2,4,6):continue
  bx0,by0,bx1,by1=obj.get_bounds();bounds=[bx0*w/pw,(ph-by1)*h/ph,bx1*w/pw,(ph-by0)*h/ph];best=None
  for wi,word in enumerate(words):
   if wi not in admitted:continue
   for ci,char in enumerate(word['chars']):
    x0,y0,x1,y1=char['box'];ix=max(0,min(x1,bounds[2])-max(x0,bounds[0]));iy=max(0,min(y1,bounds[3])-max(y0,bounds[1]));inter=ix*iy;den=(bounds[2]-bounds[0])*(bounds[3]-bounds[1])+(x1-x0)*(y1-y0)-inter;score=inter/den if den else 0
    if score>.35 and (best is None or score>best[0]):best=(score,wi,ci,char)
  if best:candidates.append((oi,bounds,best))
 pg.close();doc.close();used=set();picked=[]
 for oi,bounds,(score,wi,ci,char) in candidates:
  if wi in used:continue
  x0,y0,x1,y1=map(int,char['box']);ax=max(0,x0-3);ay=max(0,y0-3);bx=min(w,x1+3);by=min(h,y1+3)
  # Avoid ambiguous cropped neighbours: reject any candidate whose padded box overlaps another OCR character.
  neighbours=[c['box'] for c in words[wi]['chars'] if c is not char]
  if any(x0b<bx and x1b>ax and y0b<by and y1b>ay for x0b,y0b,x1b,y1b in neighbours):continue
  used.add(wi);picked.append((oi,bounds,score,wi,ci,char,(ax,ay,bx,by)))
  if len(picked)>=12:break
 for oi,bounds,score,wi,ci,char,box in picked:
  ax,ay,bx,by=box;original=pdfium.PdfDocument(str(docpath));p=original[pageno-1];objects=list(p.get_objects());target=objects[oi];rgba=[ctypes.c_uint() for _ in range(4)];ok=raw.FPDFPageObj_GetFillColor(target.raw,*[ctypes.byref(x) for x in rgba]);fill=[x.value for x in rgba] if ok else None
  for j,obj in enumerate(objects):
   if j!=oi:
    if not raw.FPDFPage_RemoveObject(p.raw,obj.raw):raise RuntimeError('could not isolate top-level object')
  full=p.render(scale=w/pw,rev_byteorder=True,fill_color=(255,255,255,255)).to_pil().convert('RGB');p.close();original.close();bitmap=full.crop((ax,ay,bx,by));vec=np.asarray(bitmap);source=src[ay:by,ax:bx];r=admitted[wi];paper=r['paper_luma'];yl=lum[ay:by,ax:bx];dark=yl<paper-30;ink=float(np.median(yl[dark])) if dark.any() else None;valid=abs(full.width-w)<=1 and abs(full.height-h)<=1 and vec.shape[:2]==source.shape[:2] and ink is not None and fill is not None
  if valid:
   ref=yl<(paper+ink)/2;vlum=vec.astype(float)@wt;fill_luma=float(np.array(fill[:3])@wt);vmask=vlum<(255+fill_luma)/2;u=int((ref|vmask).sum());iou=float((ref&vmask).sum()/u) if u else None;delta=abs(fill_luma-ink)
  else:iou=None;delta=None;ref=np.zeros(source.shape[:2],bool);vmask=np.zeros(vec.shape[:2],bool)
  source_im=Image.fromarray(source);ref_im=Image.fromarray((ref*255).astype('uint8')).convert('RGB');vec_im=Image.fromarray((vmask*255).astype('uint8')).convert('RGB');panels=[source_im,bitmap,ref_im,vec_im];cw=max(im.width for im in panels);ch=max(im.height for im in panels);canvas=Image.new('RGB',(cw*4,ch+24),'white');draw=ImageDraw.Draw(canvas)
  for k,(im,title) in enumerate(zip(panels,['source','actual font','source ref','font mask'])):canvas.paste(im,(k*cw,20));draw.text((k*cw,2),title,fill='black')
  canvas=canvas.resize((canvas.width*4,canvas.height*4),Image.Resampling.NEAREST);file=P/f'{name}-{wi:04}-{ci:02}.png';canvas.save(file);sha=hashlib.sha256(file.read_bytes()).hexdigest();row={'control':name,'word_index':wi,'text_ocr_unverified':r['text_ocr_unverified'],'char_ocr_unverified':char['text'],'ocr_box':char['box'],'actual_font_bbox':bounds,'object_to_ocr_bbox_iou':score,'ring_paper_luminance':paper,'source_ink_luminance':ink,'actual_font_fill_rgba':fill,'source_reference_pixel_count':int(ref.sum()),'font_mask_pixel_count':int(vmask.sum()),'source_vs_font_mask_iou':iou,'fill_luminance_error':delta,'pass_iou_090':iou is not None and iou>=.90,'pass_fill_15':delta is not None and delta<=15,'bbox_shapes_match':vec.shape[:2]==source.shape[:2],'panel':str(file),'panel_sha256':sha,'visual_identity_review':'pending'};allrows.append(row);index.append({'control':name,'word_index':wi,'char':char['text'],'path':str(file),'sha256':sha});print(name,wi,char['text'],'iou',iou,flush=True)
(E/'font-control-ledger.json').write_text(json.dumps(allrows,indent=2,ensure_ascii=False)+'\n');(E/'font-control-panel-index.json').write_text(json.dumps(index,indent=2,ensure_ascii=False)+'\n');print('completed',len(allrows),flush=True)
