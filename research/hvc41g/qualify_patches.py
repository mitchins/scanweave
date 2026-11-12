"""Reconstruct and verify the exact emitted source-cell patch stream."""
import hashlib,json,pathlib,sys
import numpy as np,pikepdf
from PIL import Image
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'hvc41f'));from mask_path import mask_polygons
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41g';L=R/'local/hvc41g';sha=lambda b:hashlib.sha256(b).hexdigest();freeze=json.loads((E/'freeze.json').read_text());cand=L/'historical-frozen.pdf';assert sha(cand.read_bytes())==freeze['pdf_sha256'] and (L/'qualification.started').read_text().splitlines()==[freeze['pdf_sha256'],freeze['representation_sha256']];ledger=R/'hvc41e/review-decisions.json';assert sha(ledger.read_bytes())=='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef';rows=[r for r in json.loads(ledger.read_text()) if r['decision']=='accept'];tones={r['proposal']:r for r in json.loads((R/'hvc41f/phase-b-paper-metrics.json').read_text())};expected=['q'];out=[];w,h=1738,2355
with pikepdf.open(cand) as pdf:
 page=pdf.pages[0];pw=float(page.MediaBox[2]);ph=float(page.MediaBox[3]);actual=page.Contents[1].read_bytes()
 for r in rows:
  a,b,c,d=r['reference_box'];m={}
  for key in ('owner','patch'):
   spec=r['masks'][key];p=pathlib.Path(spec['path']);assert sha(p.read_bytes())==spec['sha256'];m[key]=np.asarray(Image.open(p).convert('L'))>0
  foreign=r['foreign_ink_pixels'];art=r['foreign_artwork_pixels'];ocr=r['foreign_other_ocr_pixels'];assert not (m['patch']&~m['owner']).any() and foreign==art==ocr==0
  tone=tones[r['proposal']]['ring_median_rgb'];expected.append(' '.join(f'{z/255:.9f}' for z in tone)+' rg');loops=mask_polygons(m['patch'])
  for loop in loops:
   points=loop[:-1];compressed=[]
   for k,pt in enumerate(points):
    before=points[k-1];after=points[(k+1)%len(points)]
    if (pt[0]-before[0])*(after[1]-pt[1])==(pt[1]-before[1])*(after[0]-pt[0]):continue
    compressed.append(pt)
   for k,(xx,yy) in enumerate(compressed):expected.append(f'{(a+xx)*pw/w:.9f} {ph-(b+yy)*ph/h:.9f} '+('m' if k==0 else 'l'))
   expected.append('h')
  expected.append('f*');out.append({'proposal':r['proposal'],'patch_pixels':int(m['patch'].sum()),'patch_outside_owned':0,'frozen_review_foreign_ink_pixels':foreign,'foreign_other_ocr_pixels':ocr,'foreign_artwork_pixels':art,'tone_rgb':tone})
expected.append('Q');stream=('\n'.join(expected)).encode()
if actual!=stream:sys.exit('emitted patch stream differs from reconstructed exact ownership masks')
(E/'qualification-patches.json').write_text(json.dumps({'pdf_sha256':freeze['pdf_sha256'],'emitted_patch_sha256':sha(actual),'expected_stream_sha256':sha(stream),'exact_stream_match':True,'glyphs':out},indent=2)+'\n');print('verified exact emitted patches',len(out))
