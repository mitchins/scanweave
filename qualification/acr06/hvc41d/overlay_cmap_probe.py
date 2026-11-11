"""Native extraction behavior for a separate overlay font with nonsemantic mappings."""
import pathlib,pikepdf,pypdfium2 as pdfium,subprocess,json,hashlib
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41d';E=R/'hvc41d';base=R/'local/hvc41b/controls/control/white/baseline.pdf'
def extract(p):
 d=pdfium.PdfDocument(str(p));pg=d[0];t=pg.get_textpage();s=t.get_text_range();t.close();pg.close();d.close();return s,subprocess.check_output(['pdftotext','-layout',str(p),'-']).decode()
ref=extract(base);out={}
for label,target in [('null','0000'),('bom','FEFF'),('zwsp','200B'),('empty','')]:
 pdf=pikepdf.open(base);pg=pdf.pages[0];font=pikepdf.Dictionary(dict(pg.Resources.Font.F1));cmap=f'''/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n/CMapName /Overlay def\n/CMapType 2 def\n1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n1 beginbfchar\n<0001> <{target}>\nendbfchar\nendcmap\nCMapName currentdict /CMap defineresource pop\nend end'''.encode();font.ToUnicode=pdf.make_stream(cmap);pg.Resources.Font.FOverlay=pdf.make_indirect(font);s=pdf.make_stream(b'/Artifact BMC q BT /FOverlay 1 Tf 0 0 0 rg 20 0 0 20 300 100 Tm <0001> Tj ET Q EMC');pg.Contents=pikepdf.Array([pg.Contents,s]);file=L/f'overlay-cmap-{label}.pdf';pdf.save(file);pdf.close();v=extract(file);out[label]={'pdfium_equal':v[0]==ref[0],'poppler_equal':v[1]==ref[1],'pdfium_delta':v[0].replace(ref[0],''),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()};print(label,out[label],flush=True)
(E/'overlay-cmap-probe.json').write_text(json.dumps(out,indent=2)+'\n')
