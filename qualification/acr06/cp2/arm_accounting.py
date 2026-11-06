#!/usr/bin/env python3
"""ACR-06 CP2: six-arm representation accounting per matched page.
Geometry, text-layer search (PDFium and Poppler), font/raster/vector composition, image filters,
standalone vs attributed bytes. Usage: arm_accounting.py <qualification dir> <out.json>"""
import sys, json, subprocess, hashlib
from pathlib import Path
import pikepdf, pypdfium2 as pdfium
sys.path.insert(0, str(Path(__file__).parent))
Q = Path(sys.argv[1])
PAGES = {  # page: (group, group index, search word, standalone ScanWeave run, CamScanner file)
    'financial': ('financial', 1, 'Schofield', 'sw-annual-021.pdf', 'financial-annual-021-p01.pdf'),
    'receipt': ('receipts', 5, 'TOTAL', 'sw-cord-05.pdf', 'receipt-cord-05-p05.pdf'),
    'historical': ('historical', 3, 'direction', 'sw-history-03.pdf', 'historical-history-03-p03.pdf'),
    'mixed': ('mixed', 0, 'Watson', 'sw-scan-c03-29.pdf', 'mixed-scan-c03-29-p00.pdf'),
}
def attribution(pdf, i):
    out = subprocess.run([sys.executable, '-I', str(Path(__file__).parent/'page_attribution.py'), str(pdf), str(i)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)[str(i)]
def anatomy(pdf, i):
    doc = pikepdf.open(pdf); pg = doc.pages[i]; mb = [float(x) for x in pg.mediabox]
    imgs = []; seen = set()
    def walk(res, depth=0):
        for _, x in (res.get('/XObject') or {}).items():
            if x.objgen in seen: continue
            seen.add(x.objgen)
            if x.get('/Subtype') == '/Image':
                f = x.get('/Filter'); f = [str(v) for v in f] if isinstance(f, pikepdf.Array) else ([str(f)] if f is not None else [])
                imgs.append(dict(w=int(x.Width), h=int(x.Height), bpc=int(x.get('/BitsPerComponent', 1)), cs=str(x.get('/ColorSpace', 'mask')), filter=f,
                                 mask=bool(x.get('/ImageMask', False)), smask='/SMask' in x, bytes=len(x.read_raw_bytes()), eff_dpi=round(int(x.Width)*72/(mb[2]-mb[0]), 1)))
            elif '/Resources' in x: walk(x.Resources, depth+1)
    walk(pg.get('/Resources', {}))
    fonts = []; fseen = set()
    def fwalk(res, where):
        for _, f in (res.get('/Font') or {}).items():
            if f.objgen in fseen: continue
            fseen.add(f.objgen); d = f.DescendantFonts[0] if '/DescendantFonts' in f else f
            fd = d.get('/FontDescriptor'); ff = next((k for k in ('/FontFile', '/FontFile2', '/FontFile3') if fd is not None and k in fd), None)
            sub = fd[ff].get('/Subtype') if ff else None
            fonts.append(dict(where=where, subtype=str(f.get('/Subtype')), descendant=str(d.get('/Subtype')), file=ff, file_subtype=str(sub) if sub is not None else None,
                              name=str(fd.get('/FontName')) if fd is not None else None))
        for _, x in (res.get('/XObject') or {}).items():
            if x.get('/Subtype') == '/Form' and '/Resources' in x: fwalk(x.Resources, 'form')
    fwalk(pg.get('/Resources', {}), 'page')
    ops = pikepdf.parse_content_stream(pg); txt_ops = sum(1 for o in ops if str(o.operator) in ('Tj', 'TJ', "'", '"'))
    invisible = any(str(o.operator) == 'Tr' and int(o.operands[0]) == 3 for o in ops)
    return dict(page_pt=[round(mb[2]-mb[0], 2), round(mb[3]-mb[1], 2)], images=imgs, fonts=fonts, text_show_ops=txt_ops, invisible_text_mode=invisible)
def search(pdf, i, word):
    t = pdfium.PdfDocument(str(pdf))[i].get_textpage().get_text_range()
    p = subprocess.run(['pdftotext', '-f', str(i+1), '-l', str(i+1), str(pdf), '-'], capture_output=True, text=True).stdout
    return dict(pdfium=word.lower() in t.lower(), poppler=word.lower() in p.lower(), pdfium_chars=len(t.strip()), poppler_chars=len(p.strip()))
res = {}
for page, (g, gi, word, sw1, cs) in PAGES.items():
    arms = {
        'scanweave': dict(attributed=(Q/f'font04/local/R2a/baseline/{g}-off.pdf', gi), standalone=(Q/f'acr06/local/cp2/{sw1}', 0)),
        'adobe_xi': dict(attributed=(Q/f'pdf_packaging/groups/{g}-adobe.pdf', gi)),
        'archive_mrc': dict(attributed=(Q/f'pdf_packaging/groups/{g}-archive.pdf', gi)),
        'ocrmypdf_O3': dict(attributed=(Q/f'pdf_packaging/groups/{g}-ocrmypdf3.pdf', gi)),
        'ocrmypdf_O1': dict(attributed=(Q/f'pdf_packaging/groups/{g}-ocrmypdf1.pdf', gi)),
        'camscanner_magic_pro': dict(standalone=(Q/f'acr06/local/camscanner/web-out/{cs}', 0)),
    }
    res[page] = {}
    for arm, src in arms.items():
        pdf, i = src.get('standalone') or src['attributed']
        r = dict(source=str(pdf.relative_to(Q)), page=i, sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(), **anatomy(pdf, i), search_word=word, search=search(pdf, i, word))
        if 'attributed' in src: r['attributed_bytes'] = attribution(*src['attributed']); r['attributed_from'] = str(src['attributed'][0].relative_to(Q))
        if 'standalone' in src: r['standalone_file_bytes'] = src['standalone'][0].stat().st_size
        res[page][arm] = r
        print(page, arm, r.get('standalone_file_bytes'), (r.get('attributed_bytes') or {}).get('total'), r['search'], len(r['images']), sorted({(f['descendant'], f['file'], f['file_subtype'], f['where']) for f in r['fonts']}), flush=True)
Path(sys.argv[2]).write_text(json.dumps(res, indent=1)+'\n')
