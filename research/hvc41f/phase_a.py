#!/usr/bin/env python3
"""HVC-41F three-glyph A0/A1/A2 diagnostic. Never changes a product PDF."""
import hashlib,json,os,pathlib,subprocess,sys,tempfile
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image,ImageDraw
from scipy import ndimage
from fontTools.svgLib.path import parse_path
from fontTools.pens.boundsPen import BoundsPen
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'hvc41d'))
from pdf_font import pdf_path
from ownership_guard import require_owned
R=pathlib.Path('/data/coding/scanweave/qualification/acr06'); E=R/'hvc41f';L=R/'local/hvc41f';L.mkdir(parents=True,exist_ok=True);E.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_PHASE_A')!='1':sys.exit('research switch required')
ledger=R/'hvc41e/review-decisions.json'; final=R/'local/hvc41e/final/historical-composed.pdf';base=R/'local/ink33r/historical.pdf';sidepath=R/'local/ink33r/historical.pdf.json'
if sha(ledger.read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha(final.read_bytes())!='9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0':sys.exit('frozen input mismatch')
if sha(base.read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b':sys.exit('baseline mismatch')
side=json.loads(sidepath.read_text()); inp=R.parent/'pdf_packaging/groups/historical-input.pdf'
if sha(inp.read_bytes())!=side['input_sha256'] or any(sha(p['hocr'].encode())!=p['hocr_sha256'] for p in side['pages']):sys.exit('OCR sidecar mismatch')
raw=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');w,h=raw.size;meta=side['pages'][0]
if [w,h]!=[meta['raster_width'],meta['raster_height']] or sha(f'SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n'.encode()+raw.tobytes())!=meta['pixel_sha256'] or sha(raw.tobytes())!=meta['native_source']['decoded_rgb_sha256']:sys.exit('source pixel mismatch')
rows=json.loads(ledger.read_text()); accepted={z['proposal']:z for z in rows if z['decision']=='accept'}
if len(accepted)!=38:sys.exit('decision count mismatch')
outline=json.loads((R/'local/hvc41b/interior/p000001-outlines.json').read_text())['outlines']; ids=[243,38,18];runs=[]
with tempfile.TemporaryDirectory(prefix='hvc41f-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract'; marker=L/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(sidepath)
 if marker.exists():sys.exit('OCR marker already exists')
 for i in ids:
  z=accepted[i];trial=pathlib.Path(z['trial_pdf']);
  if sha(trial.read_bytes())!=z['trial_pdf_sha256']:sys.exit('trial hash mismatch')
  ms={}
  for k in ('patch','owner'):
   spec=z['masks'][k];p=pathlib.Path(spec['path']);b=p.read_bytes()
   if sha(b)!=spec['sha256']:sys.exit('mask hash mismatch')
   ms[k]=np.asarray(Image.open(p).convert('L'))>0
  require_owned(ms['patch'],ms['owner']);g=outline[i]
  if g['symbol']!=z['symbol_id']:sys.exit('outline symbol mismatch')
  out=[]
  for variant in ('A0','A1','A2'):
   p=pikepdf.open(trial); page=p.pages[0]; patch=page.Contents[1].read_bytes();pat=page.Resources.Pattern['/Research41E'];f=pat.Resources.Font.FR;proc=f.CharProcs['/g1'];old=proc.read_bytes();pen=BoundsPen(None);parse_path(g['path_svg'],pen);bb=pen.bounds
   if not bb or not old.startswith(b'2048 0 d0 '):sys.exit('unexpected outline')
   if variant=='A1':
    bounds=[int(np.floor(bb[0])),int(np.floor(bb[1])),int(np.ceil(bb[2])),int(np.ceil(bb[3]))];proc.write(('2048 0 '+' '.join(map(str,bounds))+' d1 ').encode()+old[len(b'2048 0 d0 '):]);f.FontBBox=pikepdf.Array(bounds)
   if variant=='A2':
    a,b,c,d,e,fm=g['matrix'];mat=[a/2048,b/2048,c/2048,d/2048,e,fm];colour=' '.join(f'{v/255:.8f}' for v in z['fill_rgb']);pat.write((f'q {colour} rg '+' '.join(str(v) for v in mat)+' cm '+pdf_path(g['path_svg'])+' f Q').encode())
   dest=L/f'{variant}-{i:03}.pdf';p.save(dest);p.close()
   with pikepdf.open(dest) as q:
    if q.pages[0].Contents[1].read_bytes()!=patch:sys.exit('patch changed')
   out.append({'proposal':i,'variant':variant,'path':str(dest),'sha256':sha(dest.read_bytes()),'patch_sha256':sha(patch),'bounds':list(bb)})
  runs.extend(out)
 if marker.exists():sys.exit('OCR invoked')
(E/'phase-a-variants.json').write_text(json.dumps(runs,indent=2)+'\n');print('prepared',len(runs),'variants',flush=True)
