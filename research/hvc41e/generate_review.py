#!/usr/bin/env python3
"""Generate only per-glyph HVC-41E trials and unsigned review material.
No multi-glyph final PDF is constructed; no identity or decision is inferred.
"""
import argparse,collections,hashlib,json,os,pathlib,subprocess,sys,tempfile,io
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image,ImageDraw
from scipy import ndimage as nd
HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'hvc41d'))
from ownership_guard import clip_owned,require_owned,require_contained_bbox
from pdf_font import pattern
from validator import metrics
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41e';L=R/'local/hvc41e';E.mkdir(exist_ok=True);L.mkdir(exist_ok=True);(L/'trials').mkdir(exist_ok=True);(L/'review').mkdir(exist_ok=True);(L/'masks').mkdir(exist_ok=True)
sys.path.insert(0,str(R/'ink33r'));from prepare import chars_from_hocr
ap=argparse.ArgumentParser();ap.add_argument('--sidecar',type=pathlib.Path,required=True);a=ap.parse_args();sha=lambda x:hashlib.sha256(x).hexdigest()
if os.environ.get('SCANWEAVE_HVC41E_CLIP_OWNERSHIP')!='1':sys.exit('HVC-41E clipping switch required')
if not a.sidecar.is_file():sys.exit('frozen OCR sidecar required')
side=json.loads(a.sidecar.read_text());inp=R.parent/'pdf_packaging/groups/historical-input.pdf';baseline=R/'local/ink33r/historical.pdf';expected=json.loads((R/'hvc41c/baseline-results.json').read_text())[0]['baseline_sha256']
if sha(inp.read_bytes())!=side['input_sha256'] or sha(baseline.read_bytes())!=expected:sys.exit('frozen input or baseline hash mismatch')
if any(sha(p['hocr'].encode())!=p['hocr_sha256'] for p in side['pages']):sys.exit('frozen hOCR mismatch')
source=np.asarray(Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB'));h,w=source.shape[:2];meta=side['pages'][0]
if [w,h]!=[meta['raster_width'],meta['raster_height']]:sys.exit('raster dimensions mismatch')
if sha(f'SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n'.encode()+source.tobytes())!=meta['pixel_sha256']:sys.exit('raster pixel hash mismatch')
if sha(source.tobytes())!=meta['native_source']['decoded_rgb_sha256']:sys.exit('decoded source hash mismatch')
freeze=(R/'hvc41d/RULE_FREEZE.md').read_text()
if sha((HERE.parent/'hvc41d/validator.py').read_bytes()) not in freeze:sys.exit('validator differs from frozen rule')
with tempfile.TemporaryDirectory(prefix='hvc41e-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';stub.write_text('#!/bin/sh\ntouch "'+str(L/'ocr-invoked')+'"\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ.get('PATH','');os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(a.sidecar)
 if (L/'ocr-invoked').exists():sys.exit('OCR stub marker exists')
 entries=json.loads((R/'hvc41d/p1-preflight-ledger.json').read_text());review=json.loads((R/'hvc41d/p1-visual-review.json').read_text());ids=[x['proposal'] for x in review]
 if len(ids)!=54 or len(set(ids))!=54 or any(entries[i]['outcome']!='requires_visual_review' for i in ids):sys.exit('frozen 54 list invalid')
 info=json.loads((R/'local/hvc41b/interior/p000001-outlines.json').read_text());outlines=info['outlines'];dump=json.loads((R/'local/hvc41/trial2/historical/p000001.json').read_text());units={u['symbol']:u for u in dump['units']};words=[word for line in chars_from_hocr(meta['hocr']) for word in line['words']];wt=np.array([.2126,.7152,.0722]);lum=source.astype(float)@wt;reference=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0
 # Reconstruct 8-connected component labels exactly and verify every recorded artwork
 # component against its stored bbox and count before using it for foreign-ink detection.
 paper=np.array(dump['paper'])@wt;fg=abs(lum-paper)>60;labels,nlabels=nd.label(fg,np.ones((3,3),bool));counts=np.bincount(labels.ravel());slices=nd.find_objects(labels);artids=[]
 for art in info['artwork']:
  ids0=art['component_ids'];parts=[slices[i-1] for i in ids0 if 0<i<=nlabels]
  if not parts:sys.exit('artwork component missing')
  box=[min(p[1].start for p in parts),min(p[0].start for p in parts),max(p[1].stop for p in parts),max(p[0].stop for p in parts)];count=int(sum(counts[i] for i in ids0))
  if box!=art['bbox'] or count!=art['pixels']:sys.exit(f'artwork reconstruction mismatch {art["index"]}')
  artids.extend(ids0)
 lookup=np.zeros(nlabels+1,bool);lookup[artids]=True;artwork=lookup[labels]
 baseline_rgb={}
 for engine in ['pdfium','poppler','mupdf']:
  f=R/f'local/hvc41d/renders/{engine}-300-01-baseline.png';baseline_rgb[engine]=np.asarray(Image.open(f).convert('RGB')).copy()
 doc=pikepdf.open(baseline);pw=float(doc.pages[0].MediaBox[2]);ph=float(doc.pages[0].MediaBox[3]);base_images={str(k):sha(v.read_raw_bytes()) for k,v in doc.pages[0].Resources.XObject.items() if str(v.get('/Subtype'))=='/Image'};doc.close()
 result=[];index=[];allchars=[(wi,ci,c['box']) for wi,word in enumerate(words) for ci,c in enumerate(word['chars'])];CROSS=np.ones((3,3),bool)
 for ordinal,i in enumerate(ids,1):
  row=entries[i];o=outlines[i];unit=units.get(row['symbol'])
  if unit is None:sys.exit(f'unit missing {i}')
  require_contained_bbox(row['bbox'],unit['bbox'])
  a0,b0,c0,d0=row['reference_box'];ux0,uy0,ux1,uy1=map(int,unit['bbox']);owner=np.zeros((h,w),bool);u=np.zeros((unit['crop_h'],unit['crop_w']),bool);u.flat[unit['mask_indices']]=True;owner[uy0:uy1,ux0:ux1]=u
  local_lum=lum[b0:d0,a0:c0];ref=local_lum<(row['admission']['paper_luma']+row['source_ink_luma'])/2
  # Frozen HVC-41D diagnostic supplies the original un-clipped proposal support.
  df=pdfium.PdfDocument(str(R/'local/hvc41d/p1-font-diagnostic.pdf'));dp=df[0];dv=np.asarray(dp.render(scale=300/72,rev_byteorder=True,fill_color=(255,255,255,255)).to_pil().convert('RGB'))[b0:d0,a0:c0].copy();dp.close();df.close();support=np.any(dv<254,axis=2);proposed=ref|support;clipped=clip_owned(proposed,owner[b0:d0,a0:c0]);require_owned(clipped,owner[b0:d0,a0:c0]);patch_full=np.zeros((h,w),bool);patch_full[b0:d0,a0:c0]=clipped
  if np.any(patch_full&~owner):sys.exit('clip violated ownership')
  pdf=pikepdf.open(baseline);page=pdf.pages[0];original=page.Contents;newres=pikepdf.Dictionary(dict(page.Resources));pats=pikepdf.Dictionary(dict(newres.get('/Pattern',pikepdf.Dictionary())));pats['/Research41E']=pattern(pdf,[{'outline':o,'fill_rgb':row['fill_rgb']}],pw,ph);newres['/Pattern']=pats;page.Resources=newres
  ops=['q',' '.join(str(x/255) for x in row['admission']['paper_rgb'])+' rg']
  for yy,rr in enumerate(clipped):
   dd=np.diff(np.pad(rr.astype(np.int8),(1,1)));starts=np.where(dd==1)[0];ends=np.where(dd==-1)[0]
   for x0,x1 in zip(starts,ends):ops.append(f'{(a0+x0)*pw/w:.9f} {ph-(b0+yy+1)*ph/h:.9f} {(x1-x0)*pw/w:.9f} {ph/h:.9f} re')
  ops+=['f','Q'];patchstream=pdf.make_stream(('\n'.join(ops)).encode());overlay=pdf.make_stream(f'q /Pattern cs /Research41E scn 0 0 {pw} {ph} re f Q'.encode());page.Contents=pikepdf.Array([original,patchstream,overlay]);trial=L/'trials'/f'p1-{i:03}.pdf';pdf.save(trial);pdf.close()
  check=pikepdf.open(trial);same={str(k):sha(v.read_raw_bytes()) for k,v in check.pages[0].Resources.XObject.items() if str(v.get('/Subtype'))=='/Image'}==base_images;pg=check.pages[0];pg.Contents=pg.Contents[-1];isofile=L/'trials'/f'.iso-{i:03}.pdf';check.save(isofile);check.close()
  def pdfium_render(f):
   dd=pdfium.PdfDocument(str(f));pp=dd[0];im=np.asarray(pp.render(scale=300/72,rev_byteorder=True,fill_color=(255,255,255,255)).to_pil().convert('RGB')).copy();pp.close();dd.close();return im
  trial_rgb=pdfium_render(trial);font=pdfium_render(isofile);isofile.unlink();font_lum=font[b0:d0,a0:c0].astype(float)@wt;fl=float(np.array(row['fill_rgb'])@wt);fontmask=font_lum<(255+fl)/2;score=metrics(ref,fontmask,row['fill_error']);union=int((ref|fontmask).sum());score['iou']=float((ref&fontmask).sum()/union) if union else None
  vector=np.zeros((h,w),bool);vector[b0:d0,a0:c0]=fontmask;neighborhood=np.zeros((h,w),bool);neighborhood[b0:d0,a0:c0]=True;ghost=reference&neighborhood&~vector&~patch_full&nd.binary_dilation(vector,structure=CROSS);under=reference&patch_full&~vector
  symci=int(row['symbol'].split('s')[-1]);wi=row['word_index'];otherboxes=np.zeros((h,w),bool)
  for j,k,(x0,y0,x1,y1) in allchars:
   if (j,k)!=(wi,symci):otherboxes[max(0,y0):min(h,y1),max(0,x0):min(w,x1)]=True
  foreign_other=patch_full&reference&otherboxes;foreign_art=patch_full&artwork;foreign=foreign_other|foreign_art
  boundary=nd.binary_dilation(patch_full,structure=CROSS)&~patch_full&~owner&~otherboxes&~artwork&~reference&(lum>=row['admission']['paper_luma']-30);by,bx=np.nonzero(patch_full)
  if by.size:
   near=np.zeros((h,w),bool);near[max(0,by.min()-2):min(h,by.max()+3),max(0,bx.min()-2):min(w,bx.max()+3)]=True;boundary &= near
  ring=lum[boundary];patch_lum=float(np.array(row['admission']['paper_rgb'])@wt);diffs=np.abs(ring-patch_lum)
  # Save masks for exact, independently reproducible source-pixel accounting.
  masks={}
  for name,mask in [('owner',owner),('patch',patch_full),('ghost',ghost),('under',under),('foreign',foreign),('vector',vector)]:
   mf=L/'masks'/f'p1-{i:03}-{name}.png';Image.fromarray((mask[b0:d0,a0:c0]*255).astype('uint8')).save(mf);masks[name]={'path':str(mf),'sha256':sha(mf.read_bytes())}
  ghost_contrast=float(np.max(row['admission']['paper_luma']-lum[ghost])) if ghost.any() else 0.0
  rowout={'proposal':i,'symbol_id':row['symbol'],'ocr_label':row['ocr_unverified'],'claude_identity':None,'decision':None,'reason':None,'source_box':row['bbox'],'recorded_owner_box':unit['bbox'],'owner_box_equals_proposal':unit['bbox']==row['bbox'],'reference_box':row['reference_box'],'word_index':wi,'frozen_validator':row['font_validation'],'trial_font_validator':score,'owned_mask_pixels':int(owner.sum()),'proposed_patch_pixels':int(proposed.sum()),'patch_pixels':int(patch_full.sum()),'patch_outside_owned_pixels':int((patch_full&~owner).sum()),'ghost_ink_pixels':int(ghost.sum()),'ghost_max_luminance_contrast':ghost_contrast,'under_replaced_ink_pixels':int(under.sum()),'foreign_ink_pixels':int(foreign.sum()),'foreign_other_ocr_pixels':int(foreign_other.sum()),'foreign_artwork_pixels':int(foreign_art.sum()),'halo_ring_pixels':int(ring.size),'halo_mean_abs_delta_luma':float(diffs.mean()) if diffs.size else None,'halo_max_abs_delta_luma':float(diffs.max()) if diffs.size else None,'fill_rgb':row['fill_rgb'],'paper_fill_rgb':row['admission']['paper_rgb'],'outline_review':None,'placement_review':None,'fill_review':None,'counters_review':None,'neighbouring_marks_review':None,'masks':masks,'trial_pdf':str(trial),'trial_pdf_sha256':sha(trial.read_bytes()),'baseline_image_streams_unchanged':same,'flags':{'ghost_present':bool(ghost.any()),'under_replaced_present':bool(under.any()),'foreign_ink_present':bool(foreign.any()),'boundary_ring_missing':not bool(ring.size)},'renderer_differences':{}}
  # Actual rendered pixels, not source samples: report exact footprint and separately
  # a two-render-pixel antialiasing envelope; never treat envelope as source ownership.
  for engine in ['pdfium','poppler','mupdf']:
   if engine=='pdfium':arr=trial_rgb
   elif engine=='poppler':
    temp=L/'trials'/f'.{i:03}-pop';subprocess.run(['pdftoppm','-f','1','-l','1','-r','300','-png','-singlefile',str(trial),str(temp)],check=True,stdout=subprocess.DEVNULL);imgfile=temp.with_suffix('.png');arr=np.asarray(Image.open(imgfile).convert('RGB')).copy();imgfile.unlink()
   else:
    imgfile=L/'trials'/f'.{i:03}-mu.png';code='import pymupdf,sys;d=pymupdf.open(sys.argv[1]);d[0].get_pixmap(matrix=pymupdf.Matrix(300/72,300/72),alpha=False).save(sys.argv[2])';subprocess.run(['/data/coding/scanweave/qualification/acr06/local/mupdf-venv/bin/python','-I','-c',code,str(trial),str(imgfile)],check=True);arr=np.asarray(Image.open(imgfile).convert('RGB')).copy();imgfile.unlink()
   base=baseline_rgb[engine]
   if arr.shape!=base.shape:sys.exit(f'renderer geometry mismatch {engine} {i}')
   rh,rw=arr.shape[:2];render_owner=np.asarray(Image.fromarray(owner).resize((rw,rh),Image.Resampling.NEAREST));changed=np.any(arr!=base,axis=2);outside=changed&~render_owner;env=nd.binary_dilation(render_owner,iterations=2);rowout['renderer_differences'][engine]={'render_dimensions':[rw,rh],'ownership_mapping':'nearest-neighbour source mask to renderer page dimensions','changed_pixels':int(changed.sum()),'outside_owned_pixels':int(outside.sum()),'outside_two_pixel_envelope_pixels':int((changed&~env).sum())}
  rowout['flags']['renderer_pixels_outside_owned']=any(v['outside_owned_pixels']>0 for v in rowout['renderer_differences'].values())
  rowout['flags']['renderer_pixels_outside_two_pixel_envelope']=any(v['outside_two_pixel_envelope_pixels']>0 for v in rowout['renderer_differences'].values())
  # Six non-overlapping columns, 4× source pixel, then three labelled reading-size strips.
  bx0=max(0,int(row['bbox'][0])-6);by0=max(0,int(row['bbox'][1])-6);bx1=min(w,int(row['bbox'][2])+6);by1=min(h,int(row['bbox'][3])+6);crop=(bx0,by0,bx1,by1);sx0,sy0,sx1,sy1=crop
  over1=source.copy();over2=source.copy();over1[owner]=(over1[owner].astype(np.uint16)*2//5+np.array([0,160,255])*3//5).astype(np.uint8);over2[patch_full]=(over2[patch_full].astype(np.uint16)*2//5+np.array([255,170,0])*3//5).astype(np.uint8)
  delta=np.max(np.abs(trial_rgb.astype(np.int16)-source.astype(np.int16)),axis=2);heat=np.repeat(np.minimum(delta*3,255).astype(np.uint8)[:,:,None],3,axis=2);heat[ghost]=[255,0,0];heat[under]=[0,255,255];heat[foreign]=[255,0,255]
  cols=[source,baseline_rgb['pdfium'],trial_rgb,over1,over2,heat];colnames=['SOURCE','BASELINE #39','SINGLE-GLYPH TRIAL','OWNED MASK (BLUE)','CLIPPED PATCH (AMBER)','DIFF: GHOST RED / UNDER CYAN'];cw=max(190,(sx1-sx0)*4+16);ch=(sy1-sy0)*4+34
  # Bounds cover target word plus its two immediate OCR neighbours, restricted to page.
  nearwords=words[max(0,wi-1):min(len(words),wi+2)];wx0=max(0,min(z['box'][0] for z in nearwords)-8);wy0=max(0,min(z['box'][1] for z in nearwords)-8);wx1=min(w,max(z['box'][2] for z in nearwords)+8);wy1=min(h,max(z['box'][3] for z in nearwords)+8)
  if wy1-wy0>250:wx0=max(0,words[wi]['box'][0]-70);wy0=max(0,words[wi]['box'][1]-25);wx1=min(w,words[wi]['box'][2]+70);wy1=min(h,words[wi]['box'][3]+25)
  strip_w=max(1,round((wx1-wx0)*96/300));strip_h=max(1,round((wy1-wy0)*96/300));canvas=Image.new('RGB',(cw*6,max(ch+3*(strip_h+17)+95,420)),'white');draw=ImageDraw.Draw(canvas)
  for col,(im,label) in enumerate(zip(cols,colnames)):
   draw.text((col*cw+4,5),label,fill='black');canvas.paste(Image.fromarray(im[sy0:sy1,sx0:sx1]).resize(((sx1-sx0)*4,(sy1-sy0)*4),Image.Resampling.NEAREST),(col*cw+4,26))
  yy=ch+5
  for im,label in [(source,'source'),(baseline_rgb['pdfium'],'baseline'),(trial_rgb,'trial')]:
   draw.text((5,yy),label,fill='black');strip=Image.fromarray(im[wy0:wy1,wx0:wx1]).resize((strip_w,strip_h),Image.Resampling.LANCZOS);canvas.paste(strip,(75,yy));yy+=strip_h+17
  lines=[f'proposal {i} | symbol {row["symbol"]} | OCR {row["ocr_unverified"]!r} | identity / decision / reason: pending',f'owned {rowout["owned_mask_pixels"]}; patch {rowout["patch_pixels"]}; outside {rowout["patch_outside_owned_pixels"]}; ghost {rowout["ghost_ink_pixels"]} (max dL {ghost_contrast:.1f}); under {rowout["under_replaced_ink_pixels"]}; foreign {rowout["foreign_ink_pixels"]}',f'boundary n={ring.size}, mean/max dL {rowout["halo_mean_abs_delta_luma"]} / {rowout["halo_max_abs_delta_luma"]}; rendered outside owned PDFium/Poppler/MuPDF '+ '/'.join(str(rowout['renderer_differences'][e]['outside_owned_pixels']) for e in ['pdfium','poppler','mupdf'])]
  for line in lines:draw.text((5,yy),line,fill='black');yy+=15
  panel=L/'review'/f'p1-{i:03}.png';canvas.save(panel);rowout['panel']=str(panel);rowout['panel_sha256']=sha(panel.read_bytes());result.append(rowout);index.append({'proposal':i,'symbol_id':row['symbol'],'path':str(panel),'sha256':rowout['panel_sha256']});print(f'{ordinal}/54 proposal {i} patch={rowout["patch_pixels"]} ghost={rowout["ghost_ink_pixels"]} under={rowout["under_replaced_ink_pixels"]} foreign={rowout["foreign_ink_pixels"]}',flush=True)
 if (L/'ocr-invoked').exists():sys.exit('OCR stub invoked')
 (E/'review-input.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');(E/'review-index.json').write_text(json.dumps(index,indent=2)+'\n');(E/'artwork-validation.json').write_text(json.dumps({'component_count':len(info['artwork']),'verified_bbox_and_pixel_count':len(info['artwork']),'foreground_components':nlabels,'method':'Frozen interior paper luminance; exact distance threshold and 8-connected labels. Every recorded artwork bbox and pixel count verified.'},indent=2)+'\n');print('COMPLETE 54; no review decisions assigned',flush=True)
