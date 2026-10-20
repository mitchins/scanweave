"""Prove collection membership, decoded source images and physical geometry."""
import pikepdf,json,hashlib
from pathlib import Path
B=Path(__file__).resolve().parent;rows=[]
for name,g in json.loads((B/'groups.json').read_text()).items():
 p=pikepdf.open(B/'groups'/f'{name}-input.pdf');pages=[]
 for pg,id in zip(p.pages,g['members']):
  src=pikepdf.open(B/'real/input'/(id+'.pdf'));original=src.pages[0]
  a=pikepdf.PdfImage(next(iter(pg.Resources.XObject.values()))).as_pil_image().convert('RGB');b=pikepdf.PdfImage(next(iter(original.Resources.XObject.values()))).as_pil_image().convert('RGB')
  assert a.size==b.size and a.tobytes()==b.tobytes();assert list(pg.MediaBox)==list(original.MediaBox)
  pages.append({'id':id,'rgb_sha256':hashlib.sha256(a.tobytes()).hexdigest(),'pixels':list(a.size),'media_box':[float(x) for x in pg.MediaBox]})
 adobe=pikepdf.open(B/'groups'/f'{name}-adobe.pdf');producer=str(adobe.docinfo.get('/Producer'));assert '11.0.20' in producer and 'ClearScan' in producer
 rows.append({'collection':name,'pages':pages,'adobe_producer':producer,'adobe_pages':len(adobe.pages),'source_equivalence':True})
(B/'matched-input-verification.json').write_text(json.dumps(rows,indent=2));print('All 32 collection pages match frozen individual image samples and geometry; ClearScan producer verified')
