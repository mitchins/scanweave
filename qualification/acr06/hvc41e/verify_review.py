"""Check completeness, frozen scores, clipping, panel hashes and trial PDF semantics."""
import pathlib,json,hashlib,os,subprocess,numpy as np,pypdfium2 as pdfium
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41e';L=R/'local/hvc41e';rows=json.loads((E/'review-input.json').read_text());index=json.loads((E/'review-index.json').read_text());previous=json.loads((R/'hvc41d/p1-preflight-ledger.json').read_text());ids=[x['proposal'] for x in json.loads((R/'hvc41d/p1-visual-review.json').read_text())];assert len(rows)==len(index)==len(ids)==54 and [x['proposal'] for x in rows]==ids;sha=lambda b:hashlib.sha256(b).hexdigest()
baseline=R/'local/ink33r/historical.pdf';base=pdfium.PdfDocument(str(baseline));page=base[0];tp=page.get_textpage();base_text=tp.get_text_range();tp.close();page.close();base.close();popbase=subprocess.check_output(['pdftotext','-f','1','-l','1',str(baseline),'-']);env=os.environ.copy();env['LD_LIBRARY_PATH']='/data/coding/scanweave/tools/dist/lib';valid=[]
for r,idx in zip(rows,index):
 assert r['claude_identity'] is None and r['decision'] is None and r['reason'] is None
 assert r['frozen_validator']==previous[r['proposal']]['font_validation']
 assert r['patch_outside_owned_pixels']==0
 owner=np.asarray(Image.open(r['masks']['owner']['path']))>0;patch=np.asarray(Image.open(r['masks']['patch']['path']))>0;assert not np.any(patch&~owner)
 for mask in r['masks'].values():assert sha(pathlib.Path(mask['path']).read_bytes())==mask['sha256']
 panel=pathlib.Path(r['panel']);assert sha(panel.read_bytes())==r['panel_sha256']==idx['sha256'];trial=pathlib.Path(r['trial_pdf']);assert sha(trial.read_bytes())==r['trial_pdf_sha256'];assert r['baseline_image_streams_unchanged']
 doc=pdfium.PdfDocument(str(trial));page=doc[0];text=page.get_textpage();s=text.get_text_range();text.close();page.close();doc.close();pop=subprocess.check_output(['pdftotext','-f','1','-l','1',str(trial),'-']);q=subprocess.run(['/data/coding/scanweave/tools/dist/bin/qpdf','--check',str(trial)],env=env,capture_output=True,text=True)
 valid.append({'proposal':r['proposal'],'qpdf_exit':q.returncode,'pdfium_text_identical':s==base_text,'poppler_text_identical':pop==popbase})
 if q.returncode or s!=base_text or pop!=popbase:raise SystemExit(f'trial validity or semantics mismatch {r["proposal"]}')
if (L/'ocr-invoked').exists():raise SystemExit('OCR stub was invoked')
summary={'trials':len(rows),'all_patch_masks_subset_owned':True,'all_baseline_images_unchanged':True,'all_decisions_null':True,'all_pdfium_text_identical':True,'all_poppler_text_identical':True,'all_qpdf_pass':True,'review_panel_hashes_verified':len(index),'ocr_stub_not_invoked':True,'per_trial':valid};(E/'review-verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='per_trial'},indent=2))
