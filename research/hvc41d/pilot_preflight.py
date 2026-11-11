#!/usr/bin/env python3
"""One locked HVC-41D p1 preflight: live word admission and completed-font diagnostics.

No source pixels are changed here. The finished PDF, if any, is a later drop-only
continuation of this same run after independent visual review of every glyph.
"""
import argparse,hashlib,json,os,pathlib,sys,tempfile,subprocess,math
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image,ImageDraw
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from pdf_font import pattern
from validator import metrics
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41d';L=R/'local/hvc41d';L.mkdir(parents=True,exist_ok=True);P=L/'p1-panels';P.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'ink33r'));from prepare import chars_from_hocr
p=argparse.ArgumentParser();p.add_argument('--sidecar',type=pathlib.Path,required=True);p.add_argument('--input',type=pathlib.Path,required=True);p.add_argument('--baseline',type=pathlib.Path,required=True);a=p.parse_args()
sha=lambda b:hashlib.sha256(b).hexdigest()
if not a.sidecar.is_file():sys.exit('frozen sidecar missing')
side=json.loads(a.sidecar.read_text());
if sha(a.input.read_bytes())!=side['input_sha256']:sys.exit('source PDF hash mismatch')
for page in side['pages']:
 if sha(page['hocr'].encode())!=page['hocr_sha256']:sys.exit('hOCR hash mismatch')
meta=side['pages'][0];source=np.asarray(Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB'));h,w=source.shape[:2]
if (w,h)!=(meta['raster_width'],meta['raster_height']):sys.exit('raster dimensions mismatch')
head=f'SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n'.encode()
if sha(head+source.tobytes())!=meta['pixel_sha256']:sys.exit('canonical pixel hash mismatch')
if sha(source.tobytes())!=meta['native_source']['decoded_rgb_sha256']:sys.exit('decoded source RGB hash mismatch')
expected=json.loads((R/'hvc41c/baseline-results.json').read_text());item=next(x for x in expected if x['document']=='historical') if isinstance(expected,list) else None
# Compare against the frozen completed #39 output directly, not a new OCR run.
if item is None or sha(a.baseline.read_bytes())!=item['baseline_sha256']:sys.exit('baseline differs from frozen #39 PDF')
freeze=(E/'RULE_FREEZE.md').read_text()
if sha(pathlib.Path(__file__).with_name('validator.py').read_bytes()) not in freeze:sys.exit('frozen validator hash mismatch')
if sha((R/'hvc41c/calibrate.py').read_bytes())!='8fb8d8fc9845d90eafdb8631be0b2b2d8b7317c58f097f8aa596cb03dc91b4b5':sys.exit('frozen admission code hash mismatch')
marker=L/'p1-single-run.started'
try:
 with marker.open('x') as f:f.write('HVC-41D single p1 preflight: '+sha(a.sidecar.read_bytes())+'\n')
except FileExistsError:sys.exit('single historical run already started; do not rerun')
# This path never invokes OCR. A failing stub is first in PATH for every child.
temp=tempfile.TemporaryDirectory(prefix='hvc41d-noocr-');t=pathlib.Path(temp.name);stub=t/'tesseract';hit=L/'forbidden-ocr-invoked';stub.write_text('#!/bin/sh\ntouch "'+str(hit)+'"\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=str(t)+':'+os.environ.get('PATH','');os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(a.sidecar)
if hit.exists():sys.exit('prior OCR stub marker exists')
data=json.loads((R/'local/hvc41b/interior/p000001-outlines.json').read_text());outlines=data['outlines'];arts=data['artwork'];
if len(outlines)!=275:sys.exit('proposal pool is not the frozen 275')
words=[word for line in chars_from_hocr(meta['hocr']) for word in line['words']];lum=source.astype(np.float32)@np.array([.2126,.7152,.0722]);excluded=np.zeros((h,w),bool);protected=[]
for reg in meta.get('protected_regions',[]):
 pts=reg.get('polygon',[]) if isinstance(reg,dict) else []
 protected.append((int(min(p[0] for p in pts)),int(min(p[1] for p in pts)),int(np.ceil(max(p[0] for p in pts))),int(np.ceil(max(p[1] for p in pts)))) if pts else (0,0,w,h))
for box in protected+[z['bbox'] for z in arts]+[z['box'] for z in words]:
 x0,y0,x1,y1=map(int,box);excluded[max(0,y0-1):min(h,y1+1),max(0,x0-1):min(w,x1+1)]=True
excluded[:2]=True;excluded[-2:]=True;excluded[:,:2]=True;excluded[:,-2:]=True
context=[]
for wi,word in enumerate(words):
 x0,y0,x1,y1=map(int,word['box']);x0=max(0,x0);y0=max(0,y0);x1=min(w,x1);y1=min(h,y1);pad=max(4,min(18,round(.35*max(1,y1-y0))));xa=max(0,x0-pad);ya=max(0,y0-pad);xb=min(w,x1+pad);yb=min(h,y1+pad);ring=lum[ya:yb,xa:xb][~excluded[ya:yb,xa:xb]];reason=[];paper=float(np.median(ring)) if len(ring) else None
 if len(ring)<32:reason.append('insufficient_exterior_ring')
 if paper is not None and paper<70:reason.append('dark_surround')
 if len(ring)>=32 and np.percentile(ring,90)-np.percentile(ring,10)>25:reason.append('inconsistent_surround')
 crop=lum[y0:y1,x0:x1];dark=(crop<paper-30) if paper is not None else np.zeros(crop.shape,bool);n=int(dark.sum());fraction=float(dark.mean()) if dark.size else 0
 if n<6:reason.append('insufficient_dark_ink')
 if fraction<.02 or fraction>.75:reason.append('ink_fraction')
 contrast=paper-float(np.median(crop[dark])) if n else None
 if contrast is None or contrast<100:reason.append('low_contrast')
 if any(xa<x1 and xb>x0 and ya<y1 and yb>y0 for xa,ya,xb,yb in protected):reason.append('protected_overlap')
 if any(z['bbox'][0]<x1 and z['bbox'][2]>x0 and z['bbox'][1]<y1 and z['bbox'][3]>y0 for z in arts):reason.append('artwork_bbox_overlap')
 ringrgb=source[ya:yb,xa:xb][~excluded[ya:yb,xa:xb]];context.append({'word_index':wi,'admitted':not reason,'reasons':reason,'paper_luma':paper,'paper_rgb':np.median(ringrgb,axis=0).round().astype(int).tolist() if len(ringrgb) else None,'ring_pixels':len(ring),'contrast':contrast})
allchars=[(wi,ci,cc) for wi,word in enumerate(words) for ci,cc in enumerate(word['chars'])];ledger=[];ready=[]
for ix,o in enumerate(outlines):
 entry={'proposal':ix,'symbol':o['symbol'],'ocr_unverified':o['text'],'bbox':o['bbox'],'outcome':'rejected','reasons':[]}
 try:wi=int(o['span'][1:]);ci=int(o['symbol'].split('s')[-1]);word=words[wi];char=word['chars'][ci];ctx=context[wi]
 except (ValueError,IndexError,KeyError):entry['reasons'].append('unmapped_OCR_symbol');ledger.append(entry);continue
 entry['word_index']=wi;entry['char_box']=char['box'];entry['admission']=ctx
 if not ctx['admitted']:entry['reasons']+=['word_'+x for x in ctx['reasons']];ledger.append(entry);continue
 x0,y0,x1,y1=map(int,char['box']);box=(max(0,x0-3),max(0,y0-3),min(w,x1+3),min(h,y1+3));xa,ya,xb,yb=box
 if o['text']!=char['text']:entry['reasons'].append('symbol_text_mismatch')
 if any(j!=wi or k!=ci for j,k,c in allchars if c['box'][0]<xb and c['box'][2]>xa and c['box'][1]<yb and c['box'][3]>ya):entry['reasons'].append('neighbour_intersects_footprint')
 if o['bbox'][0]<xa or o['bbox'][1]<ya or o['bbox'][2]>xb or o['bbox'][3]>yb:entry['reasons'].append('proposal_exceeds_padded_reference')
 yl=lum[ya:yb,xa:xb];dark=yl<ctx['paper_luma']-30
 if not dark.any():entry['reasons'].append('no_source_ink')
 if entry['reasons']:ledger.append(entry);continue
 ink_luma=float(np.median(yl[dark]));ref=yl<(ctx['paper_luma']+ink_luma)/2
 if ref[0,:].any() or ref[-1,:].any() or ref[:,0].any() or ref[:,-1].any():entry['reasons'].append('reference_touches_crop_boundary');ledger.append(entry);continue
 rgb=np.median(source[ya:yb,xa:xb][dark],axis=0).round().astype(int).tolist();fill_luma=float(np.array(rgb)@np.array([.2126,.7152,.0722]));entry.update({'reference_box':list(box),'source_ink_luma':ink_luma,'fill_rgb':rgb,'fill_error':abs(fill_luma-ink_luma),'reference_pixels':int(ref.sum()),'outcome':'awaiting_completed_font'});ready.append({'outline':o,'fill_rgb':rgb,'reference':ref,'entry':entry});ledger.append(entry)
(E/'p1-admission.json').write_text(json.dumps(context,indent=2)+'\n');print('word admitted',sum(x['admitted'] for x in context),'/',len(context),'outline diagnostic candidates',len(ready),flush=True)
if len(ready)>255:sys.exit('isolated Type3 font exceeds 255 glyph capacity')
if ready:
 base=pikepdf.open(a.baseline);pw=float(base.pages[0].MediaBox[2]);ph=float(base.pages[0].MediaBox[3]);base.close();pdf=pikepdf.Pdf.new();page=pdf.add_blank_page(page_size=(pw,ph));pat=pattern(pdf,ready,pw,ph);page.Resources=pikepdf.Dictionary(Pattern=pikepdf.Dictionary(Research=pat));page.Contents=pdf.make_stream(f'q /Pattern cs /Research scn 0 0 {pw} {ph} re f Q'.encode());diag=L/'p1-font-diagnostic.pdf';pdf.save(diag);pdf.close()
 d=pdfium.PdfDocument(str(diag));pg=d[0];arr=np.asarray(pg.render(scale=300/72,rev_byteorder=True,fill_color=(255,255,255,255)).to_pil().convert('RGB'));pg.close();d.close()
 if arr.shape[:2]!=(h,w):sys.exit(f'diagnostic geometry mismatch: {arr.shape[:2]} vs {(h,w)}')
 baseline=pdfium.PdfDocument(str(a.baseline));pg=baseline[0];basearr=np.asarray(pg.render(scale=300/72,rev_byteorder=True).to_pil().convert('RGB')).copy();pg.close();baseline.close();index=[]
 for g in ready:
  ent=g['entry'];xa,ya,xb,yb=ent['reference_box'];fontlum=arr[ya:yb,xa:xb].astype(float)@np.array([.2126,.7152,.0722]);fl=float(np.array(g['fill_rgb'])@np.array([.2126,.7152,.0722]));vmask=fontlum<(255+fl)/2;m=metrics(g['reference'],vmask,ent['fill_error']);u=int((g['reference']|vmask).sum());m['iou']=float((g['reference']&vmask).sum()/u) if u else None;ent['font_validation']=m;ent['outcome']='requires_visual_review' if m['pass'] else 'rejected';
  if not m['pass']:ent['reasons'].append('frozen_completed_font_validator')
  # Consistent separated columns: 80px minimum per image, with source context above enlarged crop.
  imgs=[Image.fromarray(source[ya:yb,xa:xb]),Image.fromarray(basearr[ya:yb,xa:xb]),Image.fromarray(arr[ya:yb,xa:xb]),Image.fromarray((g['reference']*255).astype('uint8')).convert('RGB')];cw=max(100,max(x.width for x in imgs)*4+16);ch=max(x.height for x in imgs);sheet=Image.new('RGB',(cw*4,(ch+20)*4),'white');draw=ImageDraw.Draw(sheet)
  for k,(im,label) in enumerate(zip(imgs,['source','baseline','font diagnostic','source mask'])):
   im=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST);sheet.paste(im,(k*cw,80));draw.text((k*cw+2,4),label,fill='black')
  f=P/f"p1-{ent['proposal']:03}.png";sheet.save(f);ent['panel']=str(f);ent['panel_sha256']=sha(f.read_bytes());index.append({'proposal':ent['proposal'],'path':str(f),'sha256':ent['panel_sha256']})
 (E/'p1-panel-index.json').write_text(json.dumps(index,indent=2)+'\n')
(E/'p1-preflight-ledger.json').write_text(json.dumps(ledger,indent=2,ensure_ascii=False)+'\n')
if hit.exists():sys.exit('forbidden OCR stub invoked')
print('finished; frozen validator passed',sum(x['outcome']=='requires_visual_review' for x in ledger),'of',len(ledger),flush=True)
