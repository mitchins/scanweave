#!/usr/bin/env python3
"""Drop-only continuation of the one HVC-41D preflight after visual review."""
import argparse,json,pathlib,sys,hashlib,os,tempfile,numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image
sys.path.insert(0,str(pathlib.Path(__file__).parent));from pdf_font import pattern
from ownership_guard import require_owned,clip_owned,require_contained_bbox
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41d';L=R/'local/hvc41d';sha=lambda b:hashlib.sha256(b).hexdigest();baseline=R/'local/ink33r/historical.pdf';ledger=json.loads((E/'p1-preflight-ledger.json').read_text());review=json.loads((E/'p1-visual-review.json').read_text());chosen=[x for x in review if x['decision']=='accept_for_completed_pdf']
ap=argparse.ArgumentParser();ap.add_argument('--sidecar',type=pathlib.Path,required=True);args=ap.parse_args()
if not args.sidecar.is_file():sys.exit('frozen sidecar missing')
if not (L/'p1-single-run.started').exists():sys.exit('single-run marker missing')
if sha(args.sidecar.read_bytes()) not in (L/'p1-single-run.started').read_text():sys.exit('frozen sidecar differs from preflight')
side=json.loads(args.sidecar.read_text());input=R.parent/'pdf_packaging/groups/historical-input.pdf'
expected=next(x['baseline_sha256'] for x in json.loads((R/'hvc41c/baseline-results.json').read_text()) if x['document']=='historical')
if sha(baseline.read_bytes())!=expected:sys.exit('baseline differs from frozen #39 PDF')
if sha(input.read_bytes())!=side['input_sha256']:sys.exit('input mismatch')
if any(sha(x['hocr'].encode())!=x['hocr_sha256'] for x in side['pages']):sys.exit('hOCR mismatch')
raw=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');w0,h0=raw.size;meta=side['pages'][0]
if [w0,h0]!=[meta['raster_width'],meta['raster_height']]:sys.exit('dimension mismatch')
if sha(f'SWRASTER1\nrgb8\n{w0}\n{h0}\nsrgb\n-\n'.encode()+raw.tobytes())!=meta['pixel_sha256']:sys.exit('pixel mismatch')
noocr=tempfile.TemporaryDirectory(prefix='hvc41d-final-noocr-');stub=pathlib.Path(noocr.name)/'tesseract';stub.write_text('#!/bin/sh\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=noocr.name+':'+os.environ.get('PATH','');os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(args.sidecar)
if any(ledger[x['proposal']]['outcome']!='requires_visual_review' for x in chosen):sys.exit('attempt to add a glyph outside frozen numeric pass set')
if not chosen:
 out=L/'historical-candidate.pdf';out.write_bytes(baseline.read_bytes());assert out.read_bytes()==baseline.read_bytes();sys.exit(0)
source=np.asarray(Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB'));h,w=source.shape[:2];lum=source.astype(float)@np.array([.2126,.7152,.0722]);outlines=json.loads((R/'local/hvc41b/interior/p000001-outlines.json').read_text())['outlines'];units=json.loads((R/'local/hvc41/trial2/historical/p000001.json').read_text())['units'];d=pdfium.PdfDocument(str(L/'p1-font-diagnostic.pdf'));pg=d[0];diagnostic=np.asarray(pg.render(scale=300/72,rev_byteorder=True,fill_color=(255,255,255,255)).to_pil().convert('RGB')).copy();pg.close();d.close();pdf=pikepdf.open(baseline);page=pdf.pages[0];pw=float(page.MediaBox[2]);ph=float(page.MediaBox[3]);groups=[];patchops=['q'];footprints=[]
for v in chosen:
 r=ledger[v['proposal']];a,b,c,d=r['reference_box'];paper=r['admission']['paper_luma'];ink=r['source_ink_luma'];ref=lum[b:d,a:c]<(paper+ink)/2;vec=diagnostic[b:d,a:c];support=np.any(vec<254,axis=2);patch=ref|support
 unit=next((u for u in units if u['symbol']==r['symbol']),None)
 if unit is None:sys.exit('recorded unit ownership is missing')
 if os.environ.get('SCANWEAVE_HVC41E_CLIP_OWNERSHIP')=='1':require_contained_bbox(r['bbox'],unit['bbox'])
 elif list(map(float,unit['bbox']))!=list(map(float,r['bbox'])):sys.exit('recorded unit ownership is mismatched')
 owner=np.zeros((h,w),bool);ux0,uy0,ux1,uy1=map(int,unit['bbox']);owned_crop=np.zeros((unit['crop_h'],unit['crop_w']),bool);owned_crop.flat[unit['mask_indices']]=True;owner[uy0:uy1,ux0:ux1]=owned_crop
 if os.environ.get('SCANWEAVE_HVC41E_CLIP_OWNERSHIP')=='1':
  patch=clip_owned(patch,owner[b:d,a:c])
 require_owned(patch,owner[b:d,a:c])
 if patch[0,:].any() or patch[-1,:].any() or patch[:,0].any() or patch[:,-1].any():sys.exit('font support touches footprint boundary')
 paper_rgb=r['admission']['paper_rgb'];patchops.append(' '.join(str(x/255) for x in paper_rgb)+' rg')
 for y,row in enumerate(patch):
  dif=np.diff(np.pad(row.astype(np.int8),(1,1)));starts=np.where(dif==1)[0];ends=np.where(dif==-1)[0]
  for x0,x1 in zip(starts,ends):patchops.append(f'{(a+x0)*pw/w:.9f} {ph-(b+y+1)*ph/h:.9f} {(x1-x0)*pw/w:.9f} {ph/h:.9f} re')
 patchops.append('f');mask=np.zeros((h,w),np.uint8);mask[b:d,a:c]=patch.astype(np.uint8)*255;maskfile=L/f"p1-footprint-{v['proposal']:03}.png";Image.fromarray(mask).save(maskfile);footprints.append({'proposal':v['proposal'],'pixels':int(patch.sum()),'source_box':r['reference_box'],'mask':str(maskfile),'mask_sha256':sha(maskfile.read_bytes())});groups.append({'outline':outlines[v['proposal']],'fill_rgb':r['fill_rgb']})
patchops.append('Q');original=page.Contents;newres=pikepdf.Dictionary(dict(page.Resources));pats=pikepdf.Dictionary(dict(newres.get('/Pattern',pikepdf.Dictionary())));pats['/Research41D']=pattern(pdf,groups,pw,ph);newres['/Pattern']=pats;page.Resources=newres;patchstream=pdf.make_stream(('\n'.join(patchops)).encode());overlay=pdf.make_stream(f'q /Pattern cs /Research41D scn 0 0 {pw} {ph} re f Q'.encode());page.Contents=pikepdf.Array([original,patchstream,overlay]);out=L/'historical-candidate.pdf';pdf.save(out);pdf.close();(E/'p1-footprints.json').write_text(json.dumps(footprints,indent=2)+'\n');print('candidate',out,'bytes',out.stat().st_size,'sha256',sha(out.read_bytes()),'selected',[x['proposal'] for x in chosen],flush=True)
