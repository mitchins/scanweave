"""Source-core and diagnostic-font overlap; not a verified coverage claim."""
import json,pathlib,numpy as np,pypdfium2 as pdfium
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41d';L=R/'local/hvc41d';rows=json.loads((E/'p1-preflight-ledger.json').read_text());src=np.asarray(Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB'));wt=np.array([.2126,.7152,.0722]);d=pdfium.PdfDocument(str(L/'p1-font-diagnostic.pdf'));p=d[0];vec=np.asarray(p.render(scale=300/72,rev_byteorder=True).to_pil().convert('RGB'));out=[]
for x in rows:
 if x['outcome']!='requires_visual_review':continue
 a,b,c,f=x['reference_box'];paper=x['admission']['paper_luma'];ink=x['source_ink_luma'];ref=src[b:f,a:c].astype(float)@wt<(paper+ink)/2;vl=vec[b:f,a:c].astype(float)@wt;fm=vl<(255+np.array(x['fill_rgb'])@wt)/2;out.append({'proposal':x['proposal'],'char_ocr_unverified':x['ocr_unverified'],'ref_pixels':int(ref.sum()),'ref_uncovered':int((ref&~fm).sum()),'font_extra':int((fm&~ref).sum())})
(E/'p1-coverage-diagnostic.json').write_text(json.dumps(out,indent=2)+'\n')
