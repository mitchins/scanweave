from pathlib import Path
import pikepdf,hashlib,json
b=Path('/data/coding/scanweave/qualification/acr06');source=Path('/data/coding/scanweave/qualification/pdf_packaging/groups/receipts-input.pdf');dest=b/'local/ink37/table-context-control.pdf'
with pikepdf.open(source) as src, pikepdf.Pdf.new() as out:
 for i in (1,2,3,4,5):out.pages.append(src.pages[i])
 out.save(dest,deterministic_id=True)
(b/'ink37/table-context-truth.json').write_text(json.dumps({'kind':'source-derived contextual receipt control, not independent truth','seed':370616,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_pdf_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'source_one_based_pages':[2,3,4,5,6],'target_page':3,'expected_text_fragment':'Chicken'},indent=2)+'\n')
