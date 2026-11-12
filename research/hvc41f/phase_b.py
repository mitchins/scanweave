#!/usr/bin/env python3
"""Local decoded-background paper matching, metrics on 38 and isolated PDFs on three."""
import hashlib,json,os,pathlib,sys,tempfile
import numpy as np,pikepdf
from PIL import Image
from scipy import ndimage as nd
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'hvc41d'))
from ownership_guard import require_owned
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_PHASE_B')!='1':sys.exit('research switch required')
ledger=R/'hvc41e/review-decisions.json';base=R/'local/ink33r/historical.pdf';side=R/'local/ink33r/historical.pdf.json'
if sha(ledger.read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha(base.read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b' or sha((R/'local/hvc41e/final/historical-composed.pdf').read_bytes())!='9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0':sys.exit('frozen hash mismatch')
s=json.loads(side.read_text());src=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');w,h=src.size
if sha((R.parent/'pdf_packaging/groups/historical-input.pdf').read_bytes())!=s['input_sha256'] or any(sha(x['hocr'].encode())!=x['hocr_sha256'] for x in s['pages']) or [w,h]!=[s['pages'][0]['raster_width'],s['pages'][0]['raster_height']] or sha(f'SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n'.encode()+src.tobytes())!=s['pages'][0]['pixel_sha256']:sys.exit('locked OCR or source mismatch')
with tempfile.TemporaryDirectory(prefix='hvc41f-b-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=L/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(side)
 with pikepdf.open(base) as p:
  image=pikepdf.PdfImage(p.pages[0].Resources.XObject['/Im0']).as_pil_image().convert('RGB');background=np.asarray(image.resize((w,h),Image.Resampling.BILINEAR)).copy()
 ref=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0;wt=np.array([.2126,.7152,.0722]);lum=background@wt;rows=[x for x in json.loads(ledger.read_text()) if x['decision']=='accept'];assert len(rows)==38
 result=[]
 for r in rows:
  i=r['proposal'];a,b,c,d=r['reference_box'];maps={}
  for k in ('owner','patch'):
   spec=r['masks'][k];p=pathlib.Path(spec['path']);raw=p.read_bytes()
   if sha(raw)!=spec['sha256']:sys.exit('ownership mask hash mismatch')
   maps[k]=np.asarray(Image.open(p).convert('L'))>0
  require_owned(maps['patch'],maps['owner']);x0=max(0,a-16);y0=max(0,b-16);x1=min(w,c+16);y1=min(h,d+16);local_bg=background[y0:y1,x0:x1];local_lum=lum[y0:y1,x0:x1];local_ref=ref[y0:y1,x0:x1];patch=np.zeros(local_lum.shape,bool);patch[b-y0:d-y0,a-x0:c-x0]=maps['patch'];owner=np.zeros(local_lum.shape,bool);owner[b-y0:d-y0,a-x0:c-x0]=maps['owner']
  # The background itself, not raw source, supplies paper tone. Exclude reference ink,
  # the owner, and low-luminance neighbours; use the bright half of the 12px annulus.
  annulus=nd.binary_dilation(patch,iterations=12)&~nd.binary_dilation(patch,iterations=1)&~local_ref&~owner
  vals=local_lum[annulus]
  if len(vals)<8:sys.exit('insufficient local paper evidence')
  ring=annulus&(local_lum>=np.percentile(vals,50)); tone=np.median(local_bg[ring],axis=0);_,indices=nd.distance_transform_edt(~ring,return_indices=True);nearest=local_bg[indices[0],indices[1]];B2=nearest[b-y0:d-y0,a-x0:c-x0].copy(); mask=maps['patch'];near_lum=(nearest@wt)[patch];paper0=float(np.array(r['paper_fill_rgb'])@wt);paper1=float(tone@wt)
  entry={'proposal':i,'symbol_id':r['symbol_id'],'ring_pixels':int(ring.sum()),'ring_median_rgb':tone.tolist(),'baseline_paper_fill_rgb':r['paper_fill_rgb'],'owned_pixels':int(maps['owner'].sum()),'patch_pixels':int(mask.sum()),'patch_outside_owner':int((mask&~maps['owner']).sum()),'B0_vs_nearest_ring_mean_abs_dL':float(np.abs(near_lum-paper0).mean()),'B1_vs_nearest_ring_mean_abs_dL':float(np.abs(near_lum-paper1).mean()),'B2_vs_nearest_ring_mean_abs_dL':0.0,'method':'nearest valid local decoded-background ring samples, source pixel space'};result.append(entry)
  if i not in (243,38,18):continue
  for variant in ('B1','B2'):
   path=L/f'A3-{i:03}.pdf';p=pikepdf.open(path);page=p.pages[0];pw=float(page.MediaBox[2]);ph=float(page.MediaBox[3]);old=page.Contents[1].read_bytes().decode()
   if variant=='B1':
    lines=old.splitlines();assert lines[0]=='q' and lines[1].endswith(' rg');lines[1]=' '.join(f'{x/255:.9f}' for x in tone)+' rg';page.Contents[1].write('\n'.join(lines).encode())
   else:
    mw,mh=c-a,d-b;alpha=p.make_stream((mask.astype(np.uint8)*255).tobytes());alpha.Type=pikepdf.Name.XObject;alpha.Subtype=pikepdf.Name.Image;alpha.Width=mw;alpha.Height=mh;alpha.ColorSpace=pikepdf.Name.DeviceGray;alpha.BitsPerComponent=8
    im=p.make_stream(B2.tobytes());im.Type=pikepdf.Name.XObject;im.Subtype=pikepdf.Name.Image;im.Width=mw;im.Height=mh;im.ColorSpace=pikepdf.Name.DeviceRGB;im.BitsPerComponent=8;im.SMask=alpha;page.Resources.XObject['/ResearchPatchB2']=im
    page.Contents[1].write(f'q {(c-a)*pw/w:.9f} 0 0 {(d-b)*ph/h:.9f} {a*pw/w:.9f} {ph-d*ph/h:.9f} cm /ResearchPatchB2 Do Q'.encode())
   dest=L/f'{variant}-{i:03}.pdf';p.save(dest);p.close()
   if variant=='B2':
    with pikepdf.open(dest) as chk:
     im=chk.pages[0].Resources.XObject['/ResearchPatchB2'];assert im.SMask.read_bytes()==(mask.astype(np.uint8)*255).tobytes()
   entry[variant+'_pdf_sha256']=sha(dest.read_bytes())
 if marker.exists():sys.exit('OCR invoked')
(E/'phase-b-paper-metrics.json').write_text(json.dumps(result,indent=2)+'\n');print('paper metrics',len(result),'isolated variants',6,flush=True)
