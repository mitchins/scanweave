#!/usr/bin/env python3
"""ACR-06 CP2: render ScanWeave/Adobe pages at source geometry and register CamScanner output to the source grid.
Usage: align_render.py <qualification dir> <out dir>"""
import sys, json, hashlib, io
from pathlib import Path
import numpy as np, pikepdf, pypdfium2 as pdfium
from PIL import Image
from skimage.feature import ORB, match_descriptors
from skimage.measure import ransac
from skimage.transform import AffineTransform, warp, rescale

Q = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
SRC = Q/'acr06/local/winvm/share/in/src'; CS = Q/'acr06/local/camscanner/web-out'
PAGES = [  # name, group, page index in group pdfs, source png, camscanner pdf, camscanner page
    ('financial', 'financial', 1, 'financial-annual-021-p01.png', 'financial-annual-021-p01.pdf', 0),
    ('receipt', 'receipts', 5, 'receipt-cord-05-p05.png', 'receipt-cord-05-p05.pdf', 0),
    ('historical', 'historical', 3, 'historical-history-03-p03.png', 'historical-history-03-p03.pdf', 0),
    ('mixed', 'mixed', 0, 'mixed-scan-c03-29-p00.png', 'mixed-scan-c03-29-p00.pdf', 0),
] + [(f'synthetic-p{i}', None, i, f'synthetic300-p{i:02}.png', 'synthetic300-p07.pdf', i) for i in range(8)]
SW = lambda g: Q/f'font04/local/R2a/baseline/{g}-off.pdf'
AD = lambda g: Q/f'pdf_packaging/groups/{g}-adobe.pdf'
SYN_SW = Q/'acr06/local/cp2/synthetic300-scanweave.pdf'; SYN_AD = Q/'clearscan_competitive/300/adobe.pdf'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def render(pdf, idx, w, h):
    doc = pdfium.PdfDocument(str(pdf)); pg = doc[idx]
    im = pg.render(scale=w/pg.get_width()).to_pil().convert('L')
    return np.asarray(im.resize((w, h), Image.LANCZOS) if im.size != (w, h) else im)

def page_bytes(pdf, idx):
    """Single-page extract size, and bytes of image XObjects drawn on that page."""
    src = pikepdf.open(pdf); dst = pikepdf.new(); dst.pages.append(src.pages[idx]); b = io.BytesIO(); dst.save(b, compress_streams=True)
    seen=set(); raster=0
    def walk(res):
        nonlocal raster
        for _, x in (res.get('/XObject') or {}).items():
            if x.objgen in seen: continue
            seen.add(x.objgen)
            if x.get('/Subtype') == '/Image': raster += len(x.read_raw_bytes())
            elif '/Resources' in x: walk(x.Resources)
    walk(src.pages[idx].get('/Resources', {}))
    return len(b.getvalue()), raster

def cs_image(pdf, idx):
    doc = pikepdf.open(pdf); p = doc.pages[idx]
    # FPDF shares one resource dict across pages; the drawn image is named in the content stream.
    name = [o for o in pikepdf.parse_content_stream(p) if str(o.operator) == 'Do'][0].operands[0]
    x = p.Resources.XObject[name]
    return np.asarray(pikepdf.PdfImage(x).as_pil_image().convert('L')), len(x.read_raw_bytes()), str(name)

def register(src, mov):
    f = 0.25
    a, b = rescale(src/255., f, anti_aliasing=True), rescale(mov/255., f, anti_aliasing=True)
    o1, o2 = ORB(n_keypoints=3000, fast_threshold=0.05), ORB(n_keypoints=3000, fast_threshold=0.05)
    o1.detect_and_extract(a); o2.detect_and_extract(b)
    m = match_descriptors(o1.descriptors, o2.descriptors, cross_check=True, max_ratio=0.85)
    s, d = o1.keypoints[m[:,0]][:, ::-1]/f, o2.keypoints[m[:,1]][:, ::-1]/f   # (x,y) in full res
    model, inl = ransac((s, d), AffineTransform, min_samples=3, residual_threshold=3, max_trials=5000, rng=0)
    warped = warp(mov/255., model, output_shape=src.shape, cval=1.0, order=1)  # model maps src->mov coords
    return (warped*255).round().astype(np.uint8), model, int(inl.sum()), len(m)

recs=[]
for name, g, idx, png, cspdf, csidx in PAGES:
    src = np.asarray(Image.open(SRC/png).convert('L')); h, w = src.shape
    sw_pdf, ad_pdf = (SW(g), AD(g)) if g else (SYN_SW, SYN_AD)
    sw, ad = render(sw_pdf, idx, w, h), render(ad_pdf, idx, w, h)
    csraw, csbytes, csname = cs_image(CS/cspdf, csidx)
    cs, model, ninl, nm = register(src, csraw)
    for tag, a in (('source', src), ('scanweave', sw), ('adobe', ad), ('camscanner', cs)):
        Image.fromarray(a).save(OUT/f'{name}-{tag}.png')
    swb, adb = page_bytes(sw_pdf, idx), page_bytes(ad_pdf, idx)
    sc = np.sqrt(abs(np.linalg.det(model.params[:2,:2])))
    recs.append(dict(page=name, source=png, source_px=[w,h], scanweave=dict(pdf=str(sw_pdf.relative_to(Q)), sha256=sha(sw_pdf), page=idx, single_page_bytes=swb[0], raster_bytes=swb[1]),
        adobe=dict(pdf=str(ad_pdf.relative_to(Q)), sha256=sha(ad_pdf), page=idx, single_page_bytes=adb[0], raster_bytes=adb[1]),
        camscanner=dict(pdf=cspdf, sha256=sha(CS/cspdf), page=csidx, image=csname, image_px=list(csraw.shape[::-1]), jpeg_bytes=csbytes,
            file_bytes=(CS/cspdf).stat().st_size, scale_cs_px_per_src_px=round(float(sc),4), rotation_deg=round(float(np.degrees(model.rotation)),3),
            registration_inliers=ninl, matches=nm)))
    print(name, recs[-1]['camscanner']['scale_cs_px_per_src_px'], ninl, '/', nm, flush=True)
(OUT/'pages.json').write_text(json.dumps(recs, indent=1)+'\n')
