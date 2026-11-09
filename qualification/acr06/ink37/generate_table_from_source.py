from pathlib import Path
from PIL import Image
import hashlib,json
base=Path('/data/coding/scanweave/qualification/acr06');source=base/'local/ink33/renders/receipts/04-source.png';out=base/'local/ink37/table-source-control';out.mkdir(parents=True,exist_ok=True)
im=Image.open(source).convert('RGB');pdf=out/'receipt-photo-p4.pdf';im.save(pdf,resolution=300.0)
manifest={'kind':'source-derived photographic receipt, not synthetic truth','seed':370615,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pixels':list(im.size),'expected_text_fragment':'Chicken'}
(base/'ink37/table-source-control-truth.json').write_text(json.dumps(manifest,indent=2)+'\n')
