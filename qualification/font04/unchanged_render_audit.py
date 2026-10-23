"""Validate cached unchanged-glyph measurements against actual emitted fonts."""
from pathlib import Path
import collections,io,json,multiprocessing
import numpy as np,pikepdf,pypdfium2 as pdfium
from fontTools.ttLib import TTFont
from qualification.font04 import class_metrics as cm
from qualification.font04.metrics import inspect,sha
BASE=Path('qualification/font04');ROOT=BASE/'local'

def readfont(path):
    with pikepdf.open(path) as pdf:return TTFont(io.BytesIO(next(iter(pdf.pages[0].Resources.Font.values())).DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()))

def main():
    reference=ROOT/'financial-B2-P-initial.pdf.font04';snapshot=json.loads((reference/'source.json').read_text());rows=snapshot['rows'];base=inspect(ROOT/'financial-default.pdf');basebound=cm.bind(snapshot,base);basefont=readfont(ROOT/'financial-default.pdf');oldorder=basefont.getGlyphOrder();result={}
    for point in json.loads((BASE/'b2prime-points.json').read_text())['points']:
        path=Path(point['pdf']);art=Path(str(path)+'.font04');plan=json.loads((art/'plan.json').read_text());assigned={a['member'] for a in plan['assignments']};bound=cm.bind(snapshot,inspect(path));font=readfont(path);order=font.getGlyphOrder();unchanged=[r for r in rows if r['index'] not in assigned];assert font['head'].unitsPerEm==basefont['head'].unitsPerEm
        for r in unchanged:
            i=r['index'];assert font['hmtx'][order[bound[i]['gid']]]==basefont['hmtx'][oldorder[basebound[i]['gid']]]
        for table in ['cvt ','prep','fpgm','gasp']:
            assert (table in font)==(table in basefont)
            if table in font:assert font.getTableData(table)==basefont.getTableData(table)
        chosen=set()
        for char in ['A','E',',','e','1','0','s','I']:
            rr=[r['index'] for r in unchanged if r['character']==char];chosen.update(rr[:1]+rr[-1:])
        byresource=collections.defaultdict(list)
        for r in unchanged:byresource[bound[r['index']]['font']].append(r['index'])
        chosen.update(min(v) for v in byresource.values());chosen.update(i for i in [1233,3422] if i not in assigned)
        with np.load(reference/'class-crops.npz') as arrays:
            cached={key:arrays[key] for i in chosen for key in [*(f'{i}-{e}-{n}' for e in ['analytic','pdfium','poppler'] for n in ['source','default']),f'{i}-direct-default']}
        docs={'candidate':pdfium.PdfDocument(art/'class-isolated-candidate.pdf')};cm._ROW_CONTEXT=(art,cached,set(chosen),docs,dict(default=basefont,candidate=font),basebound,bound,path);checks=[]
        with multiprocessing.get_context('fork').Pool(4,initializer=cm._init_measure_worker) as pool:
            for rr,crops in pool.imap(cm._measure_row,[rows[i] for i in sorted(chosen)],chunksize=2):
                i=rr[0]['member'];deltas={e:float(np.max(np.abs(crops[f'{i}-{e}-candidate']-cached[f'{i}-{e}-default']))) for e in ['analytic','direct','pdfium','poppler']};assert all(v==0 for v in deltas.values()),(point['label'],i,deltas);checks.append(dict(member=i,max_abs_difference=deltas))
        for doc in docs.values():doc.close()
        result[point['label']]=dict(pdf_sha256=sha(path),all_unsubstituted_hmtx_and_units_exact=True,unsubstituted_checked=len(unchanged),all_font_hinting_tables_exact=True,native_and_direct_replay=checks,all_replayed_arrays_exact=True);print('Unchanged render reuse exact',point['label'],len(checks),flush=True)
    (BASE/'b2prime-unchanged-render-reuse.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
