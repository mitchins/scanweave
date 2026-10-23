"""Serial replay of the process-parallel scorecard, at fixed physical grids."""
from pathlib import Path
import io,json,os
import numpy as np,pikepdf,pypdfium2 as pdfium
from fontTools.ttLib import TTFont
from qualification.font04 import class_metrics as cm
from qualification.font04.metrics import inspect,sha

def main():
    root=Path('qualification/font04/local');path=root/'financial-B2prime-transport.pdf';art=Path(str(path)+'.font04');ref=root/'financial-B2-P-initial.pdf.font04';snapshot=json.loads((art/'source.json').read_text());rows=snapshot['rows'];plan=json.loads((art/'plan.json').read_text());assigned={a['member'] for a in plan['assignments']};cached=np.load(ref/'class-crops.npz');new=np.load(art/'class-crops.npz');fonts={}
    for name,p in [('default',root/'financial-default.pdf'),('candidate',path)]:
        with pikepdf.open(p) as pdf:fonts[name]=TTFont(io.BytesIO(next(iter(pdf.pages[0].Resources.Font.values())).DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()))
    docs={'candidate':pdfium.PdfDocument(art/'class-isolated-candidate.pdf')};base=cm.bind(snapshot,inspect(root/'financial-default.pdf'));bound=cm.bind(snapshot,inspect(path));cm._ROW_CONTEXT=(art,cached,assigned,docs,fonts,base,bound,path);checks=[]
    for i in [0,28,75,277,488,716,1128,1233,1405,1529,2000,2500,2997,3110,3422,3500]:
        records,crops=cm._measure_row(rows[i]);deltas={key:float(np.max(np.abs(value-new[key]))) for key,value in crops.items()};assert all(v==0 for v in deltas.values()),(i,deltas);checks.append(dict(member=i,max_abs_difference=max(deltas.values()),arrays=len(deltas)))
    for d in docs.values():d.close()
    out=dict(serial_parallel_exact=True,pdf_sha256=sha(path),members=checks,reason='Each worker opens its own PDFium file handles after fork; source/default caches are materialized before fork.',discarded_failure='An initial parallel probe inherited seekable PDFium files and produced false missing glyphs; all affected measurements discarded and rerun.')
    Path('qualification/font04/b2prime-measurement-equivalence.json').write_text(json.dumps(out,indent=2)+'\n');print('serial/parallel exact',len(checks))

if __name__=='__main__':main()
