"""ACR03 fixed-case object-crop trial. No product code or authoring truth in inference."""
import argparse
import hashlib
import io
import json
import shutil
import sys
import time
import zlib
from pathlib import Path
from contextlib import nullcontext

import numpy as np
import pikepdf
from PIL import Image
from scipy import ndimage as ndi
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

ROOT = Path('qualification/acr03/local')
REFERENCE = ROOT / 'reference/qualification/acr02'
sys.path.insert(0, str(REFERENCE))
from anatomy import derivative, rewrite
from render_compare import frame

CASES = {
    'logo': ('controlled', 0), 'annotation': ('controlled', 3),
    'seal': ('historical', 4), 'financial': ('financial', 10), 'shade': ('historical', 2),
}


def paths(group):
    if group == 'controlled':
        return Path('qualification/acr02/local/prototype-input.pdf'), Path('qualification/acr02/local/prototype-acr01.pdf')
    return Path(f'qualification/pdf_packaging/groups/{group}-input.pdf'), Path(f'qualification/acr01/local/product/{group}.pdf')


def paper_and_chroma(source):
    lum = source @ np.array([.2126, .7152, .0722], dtype=np.float32)
    light = lum >= np.percentile(lum, 65)
    paper_color = np.median(source[light], axis=0)
    paper_lum = float(paper_color @ np.array([.2126, .7152, .0722]))
    hue = paper_color / max(paper_lum, 1)
    # Neutral ink on coloured paper lies on the paper-to-neutral chroma
    # segment. Do not mistake grey antialiasing or black type for coloured art.
    centered = source - source.mean(axis=2)[:, :, None]
    paper_chroma = paper_color - paper_color.mean()
    amount = np.clip((centered * paper_chroma).sum(axis=2) / max(float((paper_chroma**2).sum()), 1), 0, 1.5)
    chroma = np.max(np.abs(centered - amount[:, :, None] * paper_chroma), axis=2) > 18
    h, w = lum.shape
    cell = 64
    values = np.full(((h + cell - 1) // cell, (w + cell - 1) // cell), np.nan, dtype=np.float32)
    for y in range(values.shape[0]):
        for x in range(values.shape[1]):
            a = lum[y*cell:(y+1)*cell, x*cell:(x+1)*cell]
            valid = ~chroma[y*cell:(y+1)*cell, x*cell:(x+1)*cell]
            if valid.mean() >= .15:
                value = np.percentile(a[valid], 90)
                if value >= paper_lum * .4:
                    values[y, x] = value
    unknown = ~np.isfinite(values)
    if unknown.all():
        raise ValueError('No supported paper samples')
    nearest = ndi.distance_transform_edt(unknown, return_distances=False, return_indices=True)
    filled = values[tuple(nearest)]
    smooth = ndi.gaussian_filter(filled, 1)
    low = Image.fromarray(smooth, 'F').resize((w, h), Image.Resampling.BILINEAR)
    paper = np.clip(np.asarray(low)[:, :, None] * hue, 0, 255)
    uncertainty = np.asarray(Image.fromarray(unknown).resize((w, h), Image.Resampling.NEAREST))
    return paper, chroma, uncertainty


def boxes(mask, grow=(3, 9), minimum=1):
    grouped = ndi.binary_dilation(mask, structure=np.ones(grow, dtype=bool))
    labels, _ = ndi.label(grouped)
    result = []
    for i, region in enumerate(ndi.find_objects(labels), 1):
        if region is None:
            continue
        yy, xx = region
        if np.count_nonzero(mask[yy, xx]) >= minimum:
            result.append([max(0, xx.start-2), max(0, yy.start-2), min(mask.shape[1], xx.stop+2), min(mask.shape[0], yy.stop+2)])
    return result


def font_boxes(pdf, page, width, height):
    font_cache = {}
    mode, size, name = 0, 1., None
    tm = [1., 0., 0., 1., 0., 0.]
    result = []
    for index, item in enumerate(pikepdf.parse_content_stream(page)):
        if isinstance(item, pikepdf.ContentStreamInlineImage):
            continue
        args, operator = item
        op = str(operator)
        if op == 'Tr':
            mode = int(args[0])
        elif op == 'Tf':
            name, size = args[0], float(args[1])
        elif op == 'Tm':
            tm = list(map(float, args))
        elif op == 'Tj' and mode == 0:
            if name not in font_cache:
                descriptor = page.Resources.Font[name].DescendantFonts[0]
                font = TTFont(io.BytesIO(descriptor.FontDescriptor.FontFile2.read_bytes()))
                mapping = descriptor.get('/CIDToGIDMap')
                font_cache[name] = (font, mapping.read_bytes() if isinstance(mapping, pikepdf.Stream) else None)
            font, mapping = font_cache[name]
            raw = bytes(args[0])
            if len(raw) != 2 or tm[1] != 0 or tm[2] != 0:
                raise ValueError('Prototype expects one CID per unrotated visible show')
            cid = int.from_bytes(raw, 'big')
            gid = int.from_bytes(mapping[cid*2:cid*2+2], 'big') if mapping is not None else cid
            glyphs = font.getGlyphSet()
            pen = BoundsPen(glyphs)
            glyphs[font.getGlyphOrder()[gid]].draw(pen)
            if pen.bounds is None:
                continue
            x0, y0, x1, y1 = pen.bounds
            units = font['head'].unitsPerEm
            pw, ph = float(page.MediaBox[2]), float(page.MediaBox[3])
            pixel = 72 / 300
            box = [(tm[4]+x0/units*tm[0]*size)/pixel,
                   (ph-(tm[5]+y1/units*tm[3]*size))/pixel,
                   (tm[4]+x1/units*tm[0]*size)/pixel,
                   (ph-(tm[5]+y0/units*tm[3]*size))/pixel]
            result.append((index, box))
    return result


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def compound_ownership(regions, glyphs, w, h):
    hidden = set()
    changed = True
    while changed:
        changed = False
        for rect in regions:
            for index, glyph in glyphs:
                if overlaps(rect, glyph):
                    hidden.add(index)
                    expanded = [max(0, min(rect[0], int(np.floor(glyph[0])))), max(0, min(rect[1], int(np.floor(glyph[1])))),
                                min(w, max(rect[2], int(np.ceil(glyph[2])))), min(h, max(rect[3], int(np.ceil(glyph[3]))))]
                    if expanded != rect:
                        rect[:] = expanded
                        changed = True
    return hidden


def retained_text(pdf, page, hidden):
    # Normal ScanWeave pages have no Forms/annotations/rotation; fail rather
    # than mutating shared Form resources or changing annotation paint order.
    if page.get('/Annots') or int(page.get('/Rotate', 0)) != 0:
        raise ValueError('Unsupported page annotations/rotation')
    if any(o.get('/Subtype') == pikepdf.Name.Form for o in page.Resources.XObject.values()):
        raise ValueError('Prototype does not rewrite shared Forms')
    operations = rewrite(pdf, page, page.Resources, 'fonts', set())
    # rewrite preserves each non-inline operator slot except image Do removals,
    # so select original text-show indices by a separate show ordinal below.
    hidden_ordinals = set()
    ordinal = 0
    for index, item in enumerate(pikepdf.parse_content_stream(page)):
        if isinstance(item, pikepdf.ContentStreamInlineImage):
            continue
        if str(item.operator) == 'Tj':
            if index in hidden:
                hidden_ordinals.add(ordinal)
            ordinal += 1
    result, ordinal = [], 0
    for item in operations:
        if str(item.operator) == 'Tj':
            if ordinal in hidden_ordinals:
                result.extend([pikepdf.ContentStreamInstruction([3], pikepdf.Operator('Tr')), item,
                               pikepdf.ContentStreamInstruction([0], pikepdf.Operator('Tr'))])
            else:
                result.append(item)
            ordinal += 1
        else:
            result.append(item)
    return pikepdf.unparse_content_stream(result)


def image_object(pdf, image, quality, force_lossless=False):
    rgb = np.asarray(image.convert('RGB'))
    gray = bool(np.all(rgb[:, :, 0] == rgb[:, :, 1]) and np.all(rgb[:, :, 1] == rgb[:, :, 2]))
    im = image.convert('L' if gray else 'RGB')
    samples = np.asarray(im)
    flat = samples.reshape(im.height, -1)
    up = (flat - np.vstack([np.zeros((1, flat.shape[1]), dtype=np.uint8), flat[:-1]])).astype(np.uint8)
    predicted = np.column_stack([np.full(im.height, 2, dtype=np.uint8), up]).tobytes()
    lossless = zlib.compress(predicted, 6)
    buffer = io.BytesIO()
    im.save(buffer, format='JPEG', quality=quality, subsampling=0)
    jpeg = buffer.getvalue()
    use_jpeg = not force_lossless and len(jpeg) < len(lossless)
    obj = pikepdf.Stream(pdf, jpeg if use_jpeg else lossless)
    obj.Type = pikepdf.Name.XObject
    obj.Subtype = pikepdf.Name.Image
    obj.Width, obj.Height = im.size
    obj.ColorSpace = pikepdf.Name.DeviceGray if gray else pikepdf.Name.DeviceRGB
    obj.BitsPerComponent = 8
    obj.Filter = pikepdf.Name.DCTDecode if use_jpeg else pikepdf.Name.FlateDecode
    if not use_jpeg:
        obj.DecodeParms = pikepdf.Dictionary(Predictor=15, Colors=1 if gray else 3, BitsPerComponent=8, Columns=im.width)
    return obj


def masked_object(pdf, image, support, paper):
    samples = np.asarray(image).copy()
    samples[~support] = paper[~support]
    obj = image_object(pdf, Image.fromarray(samples), 95)
    data = zlib.compress(np.packbits(support, axis=1, bitorder='big').tobytes(), 6)
    mask = pikepdf.Stream(pdf, data)
    mask.Type=pikepdf.Name.XObject;mask.Subtype=pikepdf.Name.Image
    mask.Width=image.width;mask.Height=image.height
    mask.ColorSpace=pikepdf.Name.DeviceGray;mask.BitsPerComponent=1
    mask.Filter=pikepdf.Name.FlateDecode
    obj.SMask=mask
    return obj, len(data)


def sparse_tiles(mask, size=512):
    result=[]
    h,w=mask.shape
    for y in range(0,h,size):
        for x in range(0,w,size):
            yy,xx=np.nonzero(mask[y:y+size,x:x+size])
            if len(xx):
                result.append([x+int(xx.min()),y+int(yy.min()),x+int(xx.max())+1,y+int(yy.max())+1])
    return result


def oracle_mask(case, source):
    # Project authored mask through the same page geometry, including renderer
    # sampling phase; never resize/align a candidate to improve its score.
    if case == 'logo':
        authored = np.asarray(Image.open('qualification/acr02/local/sources/flat-logo-white.png').convert('RGB'))
        paper = np.asarray(Image.open('qualification/acr02/local/sources/flat-logo-white-paper.png').convert('RGB'))
        mask = np.any(authored != paper, axis=2)
        support = np.zeros(mask.shape, bool)
        support[140:440, 1040:1420] = True
        mask &= support
    elif case == 'annotation':
        authored = np.asarray(Image.open('qualification/acr02/local/sources/statement-annotation.png').convert('RGB'))
        plain = np.asarray(Image.open('qualification/acr02/local/sources/statement-white.png').convert('RGB'))
        mask = np.any(authored != plain, axis=2)
    else:
        raise ValueError('Oracle only permitted on authored controlled fixtures')
    destination = ROOT / f'{case}-authoring-mask.pdf'
    pdf = pikepdf.new()
    page = pdf.add_blank_page(page_size=(360,432))
    obj = pikepdf.Stream(pdf,zlib.compress((np.uint8(mask)*255).tobytes(),6))
    obj.Type=pikepdf.Name.XObject;obj.Subtype=pikepdf.Name.Image
    obj.Width=1500;obj.Height=1800;obj.BitsPerComponent=8
    obj.ColorSpace=pikepdf.Name.DeviceGray;obj.Filter=pikepdf.Name.FlateDecode
    page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Mask=obj))
    page.Contents=pikepdf.Stream(pdf,b'q 360 0 0 432 0 0 cm /Mask Do Q')
    pdf.save(destination,deterministic_id=True)
    rendered=np.asarray(frame(str(destination),0,'pdfium',300))[:,:,0]>0
    if rendered.shape != source.shape[:2]:
        raise ValueError('Authoring mask projection geometry mismatch')
    return rendered


def build(case, oracle=False, representation="crops", shared=None, page_index=None, emit_rejected=False):
    group, index = CASES[case]
    if page_index is not None:
        index = page_index
    source_path, baseline = paths(group)
    folder = ROOT / (case + '-' + representation + ('-oracle' if oracle else ''))
    if emit_rejected:
        folder = ROOT / 'rejected' / folder.name
    if page_index is not None:
        folder = folder / f'page-{index:02d}'
    folder.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    source = np.asarray(frame(str(source_path), index, 'pdfium', 300), dtype=np.float32)
    derivative(baseline, index, 'nonfont', folder / 'residual.pdf')
    residual = np.asarray(frame(str(folder / 'residual.pdf'), index, 'pdfium', 300), dtype=np.float32)
    if source.shape != residual.shape:
        raise ValueError('Source/residual physical canvases differ')
    h, w = source.shape[:2]
    paper, chroma, unknown = paper_and_chroma(source)
    object_mask = oracle_mask(case, source) if oracle else chroma
    object_mask = ndi.binary_fill_holes(ndi.binary_closing(object_mask, iterations=2))
    objects = boxes(object_mask, (13, 13), 4)
    with (nullcontext(shared) if shared is not None else pikepdf.open(baseline)) as pdf:
        page = pdf.pages[index]
        media=list(map(float,page.MediaBox))
        if media[:2] != [0.,0.] or list(page.get('/CropBox',page.MediaBox)) != list(page.MediaBox) or float(page.get('/UserUnit',1)) != 1:
            raise ValueError('Prototype requires zero-origin default-unit MediaBox equal to CropBox')
        glyphs = font_boxes(pdf, page, w, h)
        hidden = compound_ownership(objects, glyphs, w, h)
        original_mask = (paper - source).mean(axis=2) > 6
        residual_mask = (paper - residual).mean(axis=2) > 6
        fine = ndi.binary_dilation(original_mask, iterations=2) & residual_mask
        fine |= unknown
        for x0, y0, x1, y1 in objects:
            fine[y0:y1, x0:x1] = False
        unknown_outside = unknown.copy()
        for x0, y0, x1, y1 in objects:
            unknown_outside[y0:y1, x0:x1] = False
        eligible = not bool(unknown_outside.any())
        if representation == 'masked' and not eligible and not emit_rejected:
            out = folder / 'complete.pdf'
            if shared is None:
                shutil.copyfile(baseline, out)
            row = {"page": index, "fallback": "unsupported_paper", "unknown_outside_pixels": int(unknown_outside.sum()),
                   "source_sha256":hashlib.sha256(source_path.read_bytes()).hexdigest(),
                   "baseline_sha256":hashlib.sha256(baseline.read_bytes()).hexdigest(),
                   "prototype_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "pdf_bytes":out.stat().st_size if shared is None else None}
            (folder / "result.json").write_text(json.dumps(row, indent=2)+"\n")
            print(row,flush=True)
            return row
        native = boxes(fine)
        protected_fine = ndi.binary_dilation(fine, iterations=2)
        if representation == "masked":
            native = sparse_tiles(protected_fine)
        Image.fromarray(np.uint8(object_mask)*255).save(folder / 'object-mask.png')
        Image.fromarray(np.uint8(fine)*255).save(folder / 'retained-ink-mask.png')
        plate = Image.fromarray(np.uint8(np.round(paper))).resize((max(1,w//2),max(1,h//2)),Image.Resampling.LANCZOS)
        plate.save(folder / 'paper.png')
        protected_objects = ndi.binary_dilation(original_mask | chroma | unknown, iterations=2)
        streams, costs = [], []
        source_image = Image.fromarray(np.uint8(source))
        residual_image = Image.fromarray(np.uint8(residual))
        resources = page.Resources.XObject
        pw, ph = float(page.MediaBox[2]), float(page.MediaBox[3])
        for k, (rect, samples, role) in enumerate([([0,0,w,h],plate,'paper')] + [(r,residual_image.crop(r),'retained-ink') for r in native] + [(r,source_image.crop(r),'compound-object') for r in objects]):
            mask_bytes = 0
            if representation == 'masked' and role != 'paper':
                x0,y0,x1,y1 = rect
                support = protected_fine[y0:y1,x0:x1]
                if role == 'compound-object':
                    support = protected_objects[y0:y1,x0:x1]
                obj,mask_bytes = masked_object(pdf,samples,support,np.uint8(np.round(paper[y0:y1,x0:x1])))
            else:
                obj = image_object(pdf, samples, 95 if role != 'paper' else 85)
            name = f'/Object{k}'
            resources[name] = obj
            x0,y0,x1,y1 = rect
            if role == 'paper':
                matrix = [pw,0,0,ph,0,0]
            else:
                pixel = 72 / 300
                matrix = [(x1-x0)*pixel,0,0,(y1-y0)*pixel,x0*pixel,ph-y1*pixel]
            streams.append(('q '+' '.join(map(str,matrix))+f' cm {name} Do Q\n').encode())
            costs.append({'role':role,'box':rect,'pixels':list(samples.size),'bytes':len(obj.read_raw_bytes()),'mask_bytes':mask_bytes,'filter':str(obj.Filter)})
        text = retained_text(pdf,page,hidden)
        page.Contents = pikepdf.Stream(pdf,b''.join(streams)+text)
        pdf.remove_unreferenced_resources()
        out = folder / 'complete.pdf'
        if shared is None:
            pdf.save(out,deterministic_id=True,object_stream_mode=pikepdf.ObjectStreamMode.generate)
    row = {'case':case,'oracle':oracle,'representation':representation,
           'source_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),
           'baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),
           'prototype_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'protected_mask_sha256':hashlib.sha256(protected_fine.tobytes()).hexdigest(),
           'object_mask_sha256':hashlib.sha256(object_mask.tobytes()).hexdigest(),'source':str(source_path),'baseline':str(baseline),'page':index,
           'baseline_bytes':baseline.stat().st_size,'pdf_bytes':out.stat().st_size if shared is None else None,'sha256':hashlib.sha256(out.read_bytes()).hexdigest() if shared is None else None,
           'paper_eligible':eligible,'rejected_diagnostic':emit_rejected,'unknown_outside_pixels':int(unknown_outside.sum()),
           'objects':len(objects),'retained_ink_crops':len(native),'font_shows_transferred_to_raster':len(hidden),
           'resources':costs,'seconds':time.monotonic()-started,'unknown_fraction':float(unknown.mean())}
    (folder/'result.json').write_text(json.dumps(row,indent=2)+'\n')
    print({k:v for k,v in row.items() if k!='resources'},flush=True)
    return row


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',choices=tuple(CASES),default='financial')
    parser.add_argument('--financial-all',action='store_true')
    parser.add_argument('--historical-controls',action='store_true')
    parser.add_argument('--oracle',action='store_true')
    parser.add_argument('--emit-rejected',action='store_true',help='Save an explicitly rejected diagnostic, never a qualified output')
    parser.add_argument('--representation',choices=('crops','masked'),default='crops')
    args=parser.parse_args()
    if args.historical_controls:
        _, baseline = paths('historical')
        folder = ROOT / 'historical-fallback'
        folder.mkdir(parents=True, exist_ok=True)
        with pikepdf.open(baseline) as document:
            rows=[build(case, representation='masked', shared=document) for case in ('seal','shade')]
            if all('fallback' in row for row in rows):
                shutil.copyfile(baseline,folder/'complete.pdf')
            else:
                document.save(folder/'complete.pdf',deterministic_id=True,object_stream_mode=pikepdf.ObjectStreamMode.generate)
        (folder/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
    elif args.financial_all:
        _, baseline = paths('financial')
        folder = ROOT / 'financial-all-masked'
        folder.mkdir(parents=True, exist_ok=True)
        with pikepdf.open(baseline) as document:
            rows = [build('financial', representation='masked', shared=document, page_index=i) for i in range(len(document.pages))]
            document.save(folder / 'complete.pdf', deterministic_id=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
        (folder / 'results.json').write_text(json.dumps(rows, indent=2)+'\n')
        print({'baseline_bytes':baseline.stat().st_size,'pdf_bytes':(folder/'complete.pdf').stat().st_size},flush=True)
    else:
        build(args.case,args.oracle,args.representation,emit_rejected=args.emit_rejected)
