"""Read-only PDF paint ablation. Preserves operators, clips, transforms and ordering.

Unsupported text clipping fails explicitly. Individual image views retain the
actual painted contribution, not an extracted bitmap stretched over the page.
Requires the exact PR14 read-only inspector export described in README.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pikepdf
import pypdfium2
from PIL import Image, ImageDraw

HELPERS = Path('qualification/residual_resolution/local/qualification/raster_competitors')
sys.path.insert(0, str(HELPERS))
from inspect_pdf import PAINT_OPS, TEXT_OPS, inspect  # noqa: E402


def update_text_mode(op, args, rendering, stack):
    if op == 'q':
        stack.append(rendering)
    elif op == 'Q':
        rendering = stack.pop()
    elif op == 'Tr':
        rendering = int(args[0])
        if rendering not in (0, 3):
            raise ValueError('Text stroke/clip mode requires explicit handling')
    return rendering


def include_object(pdf, resources, name, mode, seen):
    obj = resources.XObject[name]
    if obj.get('/Subtype') == pikepdf.Name.Form:
        if obj.objgen not in seen:
            seen.add(obj.objgen)
            obj.write(pikepdf.unparse_content_stream(rewrite(pdf, obj, obj.get('/Resources', resources), mode, seen)))
    elif obj.get('/Subtype') == pikepdf.Name.Image:
        return mode in ('all', 'images', 'nonfont') or mode == 'image:' + ':'.join(map(str, obj.objgen))
    return True


def rewrite(pdf, container, resources, mode, seen):
    result = []
    rendering = 0
    stack = []
    for item in pikepdf.parse_content_stream(container):
        if isinstance(item, pikepdf.ContentStreamInlineImage):
            if mode in ('all', 'images', 'nonfont', 'inline'):
                result.append(item)
            continue
        args, operator = item
        op = str(operator)
        rendering = update_text_mode(op, args, rendering, stack)
        if op == 'Do' and not include_object(pdf, resources, args[0], mode, seen):
            continue
        if op in PAINT_OPS and mode not in ('all', 'paths', 'nonfont'):
            # n ends the path while retaining an already specified W/W* clip.
            result.append(pikepdf.ContentStreamInstruction([], pikepdf.Operator('n')))
            continue
        if op in TEXT_OPS and mode not in ('all', 'fonts'):
            result.extend([pikepdf.ContentStreamInstruction([3], pikepdf.Operator('Tr')), item,
                           pikepdf.ContentStreamInstruction([rendering], pikepdf.Operator('Tr'))])
        else:
            result.append(item)
    return result


def derivative(source, page_index, mode, out):
    with pikepdf.open(source) as pdf:
        page = pdf.pages[page_index]
        page.Contents = pikepdf.Stream(pdf, pikepdf.unparse_content_stream(rewrite(pdf, page, page.Resources, mode, set())))
        pdf.save(out, deterministic_id=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)


def render(path, page, renderer, dpi=120):
    if renderer == 'pdfium':
        doc = pypdfium2.PdfDocument(path)
        bitmap = doc[page].render(scale=dpi / 72)
        image = bitmap.to_pil().convert('RGB').copy()
        doc.close()
        return image
    import tempfile
    with tempfile.TemporaryDirectory(prefix='acr02-render-') as temp:
        prefix = Path(temp) / 'page'
        subprocess.run(['pdftoppm', '-f', str(page + 1), '-l', str(page + 1), '-r', str(dpi), '-singlefile', '-png', str(path), str(prefix)], check=True, capture_output=True)
        return Image.open(prefix.with_suffix('.png')).convert('RGB').copy()


def atlas(images, names, path):
    canvas = Image.new('RGB', (360 * len(images), 490), 'white')
    draw = ImageDraw.Draw(canvas)
    for index, (image, name) in enumerate(zip(images, names)):
        thumb = image.copy()
        thumb.thumbnail((350, 460))
        canvas.paste(thumb, (index * 360, 25))
        draw.text((index * 360 + 4, 5), name, fill='black')
    canvas.save(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--pages', default='0,6,12,18,24,30,35')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    inventory = inspect(args.pdf)
    (args.output / 'inventory.json').write_text(json.dumps(inventory, indent=2) + '\n')
    records = []
    for index in map(int, args.pages.split(',')):
        modes = ['all', 'fonts', 'nonfont', 'images', 'paths']
        if any(obj['page'] == index for obj in inventory['inline_images']):
            modes.append('inline')
        # All directly painted image resources, including recursive Forms, are in inventory.
        for obj in inventory['images'].values():
            if index in obj['referencing_pages'] and obj['resource_role'] == 'painted-image':
                modes.append('image:' + ':'.join(map(str, obj['object'])))
        row = {'page': index, 'views': {}, 'replay': {}}
        for mode in modes:
            output = args.output / f'page-{index}-{mode.replace(":", "-")}.pdf'
            derivative(args.pdf, index, mode, output)
            row['views'][mode] = {'path': str(output), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
        for engine in ('pdfium', 'poppler'):
            images = [render(row['views'][mode]['path'], index, engine) for mode in modes[:5]]
            original = render(args.pdf, index, engine)
            exact = np.array_equal(np.asarray(original), np.asarray(images[0]))
            if not exact:
                raise ValueError(f'Ordered replay differs: {index} {engine}')
            row['replay'][engine] = {'pixel_identical': exact}
            for mode, image in zip(modes[:5], images):
                image.save(args.output / f'page-{index}-{mode}-{engine}.png')
            for mode in modes[5:]:
                render(row['views'][mode]['path'], index, engine).save(args.output / f'page-{index}-{mode.replace(":", "-")}-{engine}.png')
            atlas(images, modes[:5], args.output / f'page-{index}-{engine}.png')
        records.append(row)
        print(index, len(modes), flush=True)
    (args.output / 'layers.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
