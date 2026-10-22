"""Temporary recomposition of existing ScanWeave PDF residuals, preserving fonts/text.

Not a product path. Local illumination and coverage are estimated from the actual
emitted non-font raster, never the evaluator's paired paper or source text.
"""
import argparse
import io
import json
import time
import zlib
from pathlib import Path

import numpy as np
import pikepdf
from PIL import Image
from scipy.ndimage import gaussian_filter, maximum_filter

from anatomy import derivative, render, rewrite


def encoded_image(pdf, image, jpeg=False):
    if jpeg:
        stream = io.BytesIO()
        image.convert('RGB').save(stream, format='JPEG', quality=85, subsampling=0)
        data = stream.getvalue()
    else:
        samples = np.asarray(image)
        if samples.ndim == 2:
            raw = np.column_stack([np.full(image.height, 2, dtype=np.uint8), (samples - np.vstack([np.zeros((1,image.width),dtype=np.uint8),samples[:-1]])).astype(np.uint8)]).tobytes()
        else:
            raw = image.tobytes()
        data = zlib.compress(raw, 6)
    obj = pikepdf.Stream(pdf, data)
    obj.Type = pikepdf.Name.XObject
    obj.Subtype = pikepdf.Name.Image
    obj.Width, obj.Height = image.size
    obj.BitsPerComponent = 8
    if image.mode == 'P':
        obj.ColorSpace = pikepdf.Array([pikepdf.Name.Indexed, pikepdf.Name.DeviceRGB, 15, pikepdf.String(bytes(image.getpalette()[:48]))])
    else:
        obj.ColorSpace = pikepdf.Name.DeviceGray if image.mode == 'L' else pikepdf.Name.DeviceRGB
    if not jpeg and image.mode in ('L', 'P'):
        obj.DecodeParms = pikepdf.Dictionary(Predictor=15, Colors=1, BitsPerComponent=8, Columns=image.width)
    obj.Filter = pikepdf.Name.DCTDecode if jpeg else pikepdf.Name.FlateDecode
    return obj


def layers(image, coverage_levels):
    source = np.asarray(image, dtype=np.float32)
    # Opening the darkness field estimates paper across printed strokes. A broad
    # photo remains a broad object: this is a known limitation tested explicitly.
    paper = np.stack([gaussian_filter(maximum_filter(source[:, :, c], size=31), 8) for c in range(3)], axis=2)
    alpha = np.clip(np.max((paper - source) / np.maximum(paper, 1), axis=2), 0, 1)
    # Keep weak supported coverage rather than thresholding small marks away.
    foreground = (source - (1 - alpha[:, :, None]) * paper) / np.maximum(alpha[:, :, None], 1 / 255)
    foreground = np.uint8(np.clip(foreground, 0, 255))
    background = Image.fromarray(np.uint8(np.clip(paper, 0, 255))).resize((max(1, image.width // 4), max(1, image.height // 4)), Image.Resampling.LANCZOS)
    # Foreground colour is low-frequency; native coverage carries sharp geometry.
    weight = gaussian_filter(alpha, 2)
    color = np.stack([gaussian_filter(foreground[:, :, c] * alpha, 2) / np.maximum(weight, 1e-6) for c in range(3)], axis=2)
    color = Image.fromarray(np.uint8(np.clip(color, 0, 255))).resize((max(1, image.width // 2), max(1, image.height // 2)), Image.Resampling.LANCZOS)
    if coverage_levels == 16:
        # A bounded tonal approximation removes very weak paper grain; not a
        # declaration that all weak source marks are semantically disposable.
        alpha = np.round(alpha * 15) / 15
    mask = Image.fromarray(np.uint8(np.round(alpha * 255)), 'L')
    return background, color, mask


def validate_page(page):
    """This shadow path is deliberately limited to normal ScanWeave pages."""
    if int(page.get('/Rotate', 0)) % 360:
        raise ValueError('Prototype does not support rotated page coordinates')
    if list(page.get('/CropBox', page.MediaBox)) != list(page.MediaBox):
        raise ValueError('Prototype requires CropBox equal to MediaBox')
    if page.get('/Annots'):
        raise ValueError('Prototype does not recompose PDF annotations')
    objects = page.Resources.get('/XObject', {})
    if any(obj.get('/Subtype') == pikepdf.Name.Form for obj in objects.values()):
        raise ValueError('Prototype rejects shared/nested Form resources')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--pages', default='6,16,24,28')
    parser.add_argument('--foreground', choices=('jpeg', 'indexed16'), default='jpeg')
    parser.add_argument('--coverage-levels', type=int, choices=(16, 256), default=256)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with pikepdf.open(args.source) as pdf:
        for index in map(int, args.pages.split(',')):
            validate_page(pdf.pages[index])
            started = time.monotonic()
            residual_pdf = args.out.with_name(f'{args.out.stem}-p{index}-residual.pdf')
            derivative(args.source, index, 'nonfont', residual_pdf)
            image = render(residual_pdf, index, 'pdfium', 300)
            background, foreground, mask = layers(image, args.coverage_levels)
            bg = encoded_image(pdf, background, True)
            if args.foreground == 'indexed16':
                foreground = foreground.quantize(colors=16, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
            fg = encoded_image(pdf, foreground, args.foreground == 'jpeg')
            smask = encoded_image(pdf, mask)
            fg.SMask = smask
            form = pikepdf.Stream(pdf, b'q /Paper Do /Content Do Q')
            form.Type = pikepdf.Name.XObject
            form.Subtype = pikepdf.Name.Form
            form.BBox = pikepdf.Array([0, 0, 1, 1])
            form.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Paper=bg, Content=fg))
            page = pdf.pages[index]
            ops = rewrite(pdf, page, page.Resources, 'fonts', set())
            box = list(map(float, page.MediaBox))
            page.Resources.XObject['/ACR02'] = form
            prefix = f'q {box[2]-box[0]} 0 0 {box[3]-box[1]} {box[0]} {box[1]} cm /ACR02 Do Q\n'.encode()
            page.Contents = pikepdf.Stream(pdf, prefix + pikepdf.unparse_content_stream(ops))
            rows.append({'page': index, 'background': [background.width, background.height],
                         'foreground_color': list(foreground.size), 'coverage': list(mask.size),
                         'bytes': {'background': len(bg.read_raw_bytes()), 'foreground': len(fg.read_raw_bytes()), 'mask': len(smask.read_raw_bytes())},
                         'seconds': time.monotonic() - started})
            print(rows[-1], flush=True)
        pdf.remove_unreferenced_resources()
        pdf.save(args.out, deterministic_id=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
    args.out.with_suffix('.json').write_text(json.dumps({'source': str(args.source), 'output': str(args.out), 'coverage_levels': args.coverage_levels, 'foreground_encoding': args.foreground, 'paper_dpi': 75, 'foreground_dpi': 150, 'coverage_dpi': 300, 'pdf_bytes': args.out.stat().st_size, 'pages': rows}, indent=2) + '\n')


if __name__ == '__main__':
    main()
