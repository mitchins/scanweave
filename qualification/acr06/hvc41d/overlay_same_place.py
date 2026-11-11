"""Test duplicate extraction from an appended marked-content text object on an existing control PDF."""
import pathlib,pikepdf,pypdfium2 as pdfium,subprocess,json,hashlib
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41d';E=R/'hvc41d';base=R/'local/hvc41b/controls/control/white/baseline.pdf'
def extract(p):
 d=pdfium.PdfDocument(str(p));pg=d[0];t=pg.get_textpage();text=t.get_text_range();t.close();pg.close();d.close();pop=subprocess.check_output(['pdftotext','-layout',str(p),'-']).decode();return {'pdfium':text,'poppler':pop}
def create(tag,wrapping):
 p=pikepdf.open(base);pg=p.pages[0];content=wrapping[0]+b'\nq BT /F1 1 Tf 0 0 0 rg 20.391722 0 0 21.12 172.32 480.96 Tm <0001> Tj ET Q\n'+wrapping[1]+b'\n';s=p.make_stream(content);orig=pg.Contents
 pg.Contents=pikepdf.Array([orig,s]);out=L/f'overlay-same-place-{tag}.pdf';p.save(out);p.close();return out
ref=extract(base);out={}
for tag,w in [('artifact',(b'/Artifact BMC',b'EMC')),('empty_actualtext',(b'/Span <</ActualText ()>> BDC',b'EMC'))]:
 p=create(tag,w);v=extract(p);out[tag]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pdfium_equal':v['pdfium']==ref['pdfium'],'poppler_equal':v['poppler']==ref['poppler'],'pdfium_extra':v['pdfium'].replace(ref['pdfium'],''),'poppler_after':v['poppler']}
 print(tag,out[tag]['pdfium_equal'],out[tag]['poppler_equal'],repr(out[tag]['pdfium_extra']))
(E/'overlay-same-place.json').write_text(json.dumps(out,indent=2)+'\n')
