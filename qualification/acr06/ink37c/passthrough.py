import json,hashlib,pikepdf
from pathlib import Path
root=Path('/data/coding/scanweave/qualification/acr06'); rows=[]
for d,n in [('historical',2),('historical',5),('receipts',4)]:
 src=Path('/data/coding/scanweave/qualification/pdf_packaging/groups')/f'{d}-input.pdf';p=pikepdf.open(src);page=p.pages[n-1];objs=[o for o in page.Resources.XObject.values() if str(o.get('/Subtype'))=='/Image']; assert len(objs)==1;o=objs[0]
 side=json.load(open(root/'local/ink37/owner37'/f'{d}.pdf.json'))['pages'][n-1];prov=side['native_source'];digest=hashlib.sha256(o.read_raw_bytes()).hexdigest();assert digest==prov['encoded_sha256']
 b=pikepdf.open(root/'local/ink37/owner37'/f'{d}.pdf');a=b.pages[n-1].Resources.XObject['/Im0']
 rows.append({'document':d,'page':n,'source_filter':str(o.Filter),'source_encoded_bytes':len(o.read_raw_bytes()),'source_encoded_sha256':digest,'canonical_rgb_sha256':prov['decoded_rgb_sha256'],'source_import':side['raster_import'],'baseline_image_bytes':len(a.read_raw_bytes()),'source_passthrough_saves_bytes_vs_baseline':len(o.read_raw_bytes())<len(a.read_raw_bytes())});b.close();p.close()
(root/'ink37c/passthrough.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:print(r)
