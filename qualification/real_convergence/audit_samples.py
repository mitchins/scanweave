"""Actual decoded native samples, outside the accepted vector occurrence bounds.
Bounds are audit limits only; the converter does not erase OCR rectangles.
"""
import json
from pathlib import Path
import pikepdf,numpy as np
B=Path(__file__).resolve().parent;P=B.parent/'pdf_packaging';out=[]
for id in ['cord-00','cord-05','history-02','history-03','scan-linn','nara-form-01','nara-form-02']:
 path=B/'outputs'/f'{id}.pdf';r=json.loads(Path(str(path)+'.json').read_text())['conversion']['page_reports'][0];src=pikepdf.open(P/'real/input'/f'{id}.pdf');pdf=pikepdf.open(path);original=np.asarray(pikepdf.PdfImage(next(iter(src.pages[0].Resources.XObject.values()))).as_pil_image().convert('RGB'));allowed=np.zeros(original.shape[:2],dtype=bool);obs={o['symbol_id']:o for o in r['reconstruction']['observations']};visible=[o for o in r['occurrences'] if o['owner'].startswith('visible')]
 for o in visible:
  if o['symbol_id'] not in obs:continue
  x0,y0,x1,y1=obs[o['symbol_id']]['bbox_px'];allowed[max(0,int(y0)-3):min(original.shape[0],int(y1)+3),max(0,int(x0)-3):min(original.shape[1],int(x1)+3)]=True
 record={'id':id,'vectors':len(visible),'patch_count':len(r['patches']),'native_patches':0,'changed_native_samples_pixels':0,'changes_outside_vector_bboxes_plus_3px':0,'skipped_reduced_paper_patches':0}
 for i,patch in enumerate(r['patches']):
  if patch['compact_background']:record['skipped_reduced_paper_patches']+=1;continue
  im=pdf.pages[0].Resources.XObject['/Im'+str(i)];decoded=np.asarray(pikepdf.PdfImage(im).as_pil_image().convert('RGB'));x0,y0,x1,y1=map(int,patch['bbox_px']);crop=original[y0:y1,x0:x1];assert crop.shape==decoded.shape,(id,i,crop.shape,decoded.shape);diff=np.any(crop!=decoded,axis=2);record['native_patches']+=1;record['changed_native_samples_pixels']+=int(diff.sum());record['changes_outside_vector_bboxes_plus_3px']+=int((diff&~allowed[y0:y1,x0:x1]).sum())
 assert record['changes_outside_vector_bboxes_plus_3px']==0,record
 if not visible:assert record['changed_native_samples_pixels']==0
 out.append(record);print(record,flush=True)
(B/'retained-sample-audit.json').write_text(json.dumps(out,indent=2))
