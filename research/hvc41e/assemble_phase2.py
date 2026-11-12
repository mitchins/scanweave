#!/usr/bin/env python3
"""One HVC-41E composed p1 PDF from the frozen, independently reviewed ledger."""
import argparse,hashlib,json,os,pathlib,sys,tempfile
import numpy as np,pikepdf
from PIL import Image
HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent/'hvc41d'))
from ownership_guard import require_owned,require_contained_bbox
from pdf_font import pattern
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41e';L=R/'local/hvc41e/final';L.mkdir(parents=True,exist_ok=True);sha=lambda b:hashlib.sha256(b).hexdigest();expected_ledger='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef';ap=argparse.ArgumentParser();ap.add_argument('--sidecar',type=pathlib.Path,required=True);args=ap.parse_args()
if os.environ.get('SCANWEAVE_HVC41E_CLIP_OWNERSHIP')!='1':sys.exit('ownership clipping switch required')
ledgerfile=E/'review-decisions.json'
if not ledgerfile.is_file() or sha(ledgerfile.read_bytes())!=expected_ledger:sys.exit('frozen review ledger hash mismatch')
ledger=json.loads(ledgerfile.read_text());accept=[r for r in ledger if r['decision']=='accept'];reject=[r for r in ledger if r['decision']=='reject']
if len(ledger)!=54 or len(accept)!=38 or len(reject)!=16 or len({r['proposal'] for r in ledger})!=54:sys.exit('frozen review decisions invalid')
if not args.sidecar.is_file():sys.exit('frozen OCR sidecar required')
side=json.loads(args.sidecar.read_text());input=R.parent/'pdf_packaging/groups/historical-input.pdf';baseline=R/'local/ink33r/historical.pdf';expected=next(x['baseline_sha256'] for x in json.loads((R/'hvc41c/baseline-results.json').read_text()) if x['document']=='historical')
if sha(input.read_bytes())!=side['input_sha256'] or sha(baseline.read_bytes())!=expected:sys.exit('frozen input or baseline hash mismatch')
if any(sha(x['hocr'].encode())!=x['hocr_sha256'] for x in side['pages']):sys.exit('hOCR mismatch')
source=np.asarray(Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB'));h,w=source.shape[:2];meta=side['pages'][0]
if [w,h]!=[meta['raster_width'],meta['raster_height']]:sys.exit('source dimensions mismatch')
if sha(f'SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n'.encode()+source.tobytes())!=meta['pixel_sha256'] or sha(source.tobytes())!=meta['native_source']['decoded_rgb_sha256']:sys.exit('source pixel hash mismatch')
freeze=(R/'hvc41d/RULE_FREEZE.md').read_text()
if sha((HERE.parent/'hvc41d/validator.py').read_bytes()) not in freeze:sys.exit('frozen validator mismatch')
preflight=json.loads((E/'review-input.json').read_text());pre={x['proposal']:x for x in preflight};outlines=json.loads((R/'local/hvc41b/interior/p000001-outlines.json').read_text())['outlines'];units={x['symbol']:x for x in json.loads((R/'local/hvc41/trial2/historical/p000001.json').read_text())['units']}
if {x['proposal'] for x in preflight}!={x['proposal'] for x in ledger}:sys.exit('review proposal pool differs from frozen phase 1')
prepared=[]
for r in accept:
 p=pre[r['proposal']]
 for key in ('symbol_id','reference_box','masks','fill_rgb','paper_fill_rgb','frozen_validator'):
  if r[key]!=p[key]:sys.exit(f'frozen phase 1 field mismatch {r["proposal"]}: {key}')
 if not r['frozen_validator']['pass']:sys.exit('accepted proposal lacks frozen validator pass')
 u=units.get(r['symbol_id'])
 if u is None:sys.exit('owner missing')
 require_contained_bbox(r['source_box'],u['bbox']);x0,y0,x1,y1=r['reference_box'];owner=np.zeros((h,w),bool);ux,uy,ux1,uy1=map(int,u['bbox']);crop=np.zeros((u['crop_h'],u['crop_w']),bool);crop.flat[u['mask_indices']]=True;owner[uy:uy1,ux:ux1]=crop
 maps={}
 for k in ('owner','patch','vector'):
  spec=r['masks'][k];path=pathlib.Path(spec['path']);raw=path.read_bytes()
  if sha(raw)!=spec['sha256']:sys.exit(f'mask hash mismatch {r["proposal"]}: {k}')
  maps[k]=np.asarray(Image.open(path).convert('L'))>0
 if not np.array_equal(maps['owner'],owner[y0:y1,x0:x1]):sys.exit(f'owner mask changed {r["proposal"]}')
 require_owned(maps['patch'],maps['owner'])
 if int(maps['patch'].sum())!=r['patch_pixels'] or (maps['patch']&~maps['owner']).any():sys.exit('patch count or ownership mismatch')
 o=outlines[r['proposal']]
 if o['symbol']!=r['symbol_id']:sys.exit('outline symbol mismatch')
 prepared.append({'row':r,'outline':o,'patch':maps['patch']})
marker=L/'phase2-assembly.started'
try:
 with marker.open('x') as f:f.write(expected_ledger+'\n')
except FileExistsError:sys.exit('phase 2 assembly already started; refuse a second assembly')
with tempfile.TemporaryDirectory(prefix='hvc41e-phase2-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';stub.write_text('#!/bin/sh\ntouch "'+str(L/'ocr-invoked')+'"\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ.get('PATH','');os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(args.sidecar)
 if (L/'ocr-invoked').exists():sys.exit('forbidden OCR marker exists')
 pdf=pikepdf.open(baseline);page=pdf.pages[0];pw=float(page.MediaBox[2]);ph=float(page.MediaBox[3]);original=page.Contents;ops=['q'];groups=[]
 for z in prepared:
  r=z['row'];patch=z['patch'];a,b,c,d=r['reference_box'];ops.append(' '.join(str(v/255) for v in r['paper_fill_rgb'])+' rg')
  for y,line in enumerate(patch):
   diff=np.diff(np.pad(line.astype(np.int8),(1,1)));starts=np.where(diff==1)[0];ends=np.where(diff==-1)[0]
   for x0,x1 in zip(starts,ends):ops.append(f'{(a+x0)*pw/w:.9f} {ph-(b+y+1)*ph/h:.9f} {(x1-x0)*pw/w:.9f} {ph/h:.9f} re')
  ops.append('f');groups.append({'outline':z['outline'],'fill_rgb':r['fill_rgb']})
 ops.append('Q');resources=pikepdf.Dictionary(dict(page.Resources));pats=pikepdf.Dictionary(dict(resources.get('/Pattern',pikepdf.Dictionary())));pats['/Research41E']=pattern(pdf,groups,pw,ph);resources['/Pattern']=pats;page.Resources=resources;patchbytes=('\n'.join(ops)).encode();overlaybytes=f'q /Pattern cs /Research41E scn 0 0 {pw} {ph} re f Q'.encode();page.Contents=pikepdf.Array([original,pdf.make_stream(patchbytes),pdf.make_stream(overlaybytes)]);out=L/'historical-composed.pdf';pdf.save(out);pdf.close()
 if (L/'ocr-invoked').exists():sys.exit('forbidden OCR marker exists')
 result={'ledger_sha256':expected_ledger,'accepted_proposals':[x['proposal'] for x in accept],'rejected_proposals':[x['proposal'] for x in reject],'candidate_pdf':str(out),'candidate_sha256':sha(out.read_bytes()),'candidate_bytes':out.stat().st_size,'baseline_sha256':expected,'baseline_bytes':baseline.stat().st_size,'patch_stream_decoded_bytes':len(patchbytes),'overlay_invocation_decoded_bytes':len(overlaybytes),'ocr_stub_not_invoked':True};(E/'assembly.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
