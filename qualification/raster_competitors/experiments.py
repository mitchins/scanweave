"""Two bounded shadow controls, using history-02 only; never changes product code.

E1: identical OCRmyPDF palette samples represented Indexed versus expanded RGB.
E2: current whole-page fallback at 300 versus 150 DPI Q100/4:4:4.
All copies preserve ScanWeave's font/text operators and page geometry.
"""
import hashlib
import io
import json
import zlib
from pathlib import Path

import numpy as np
import pikepdf
from PIL import Image
from inspect_pdf import inspect
from render_compare import frame, features, sheet

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OUT = BASE/'local/experiments'


def page_copy(path, index):
    pdf = pikepdf.Pdf.new()
    with pikepdf.open(path) as source:
        pdf.pages.append(source.pages[index])
    return pdf


def image_key(pdf):
    images = [(k,v) for k,v in pdf.pages[0].Resources.XObject.items() if v.get('/Subtype')==pikepdf.Name.Image]
    if len(images)!=1:
        raise ValueError('Control requires exactly one raster placement')
    return images[0][0]


def rgb_stream(pdf, image, jpeg=False):
    if jpeg:
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=100, subsampling=0, optimize=True)
        data, codec = buffer.getvalue(), '/DCTDecode'
    else:
        data, codec = zlib.compress(image.tobytes(),9), '/FlateDecode'
    stream = pikepdf.Stream(pdf,data)
    for key,value in {'Type':pikepdf.Name.XObject,'Subtype':pikepdf.Name.Image,
                      'Width':image.width,'Height':image.height,'ColorSpace':pikepdf.Name.DeviceRGB,
                      'BitsPerComponent':8,'Filter':pikepdf.Name(codec)}.items():
        stream['/'+key]=value
    return stream


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    sw = ROOT/'qualification/tonal_raster/collections/historical.pdf'
    o3 = ROOT/'qualification/pdf_packaging/groups/historical-ocrmypdf3.pdf'
    source = ROOT/'qualification/pdf_packaging/groups/historical-input.pdf'
    arms = {}
    for arm in ('baseline-300', 'palette-indexed-300', 'palette-expanded-rgb-300', 'wholepage-150-q100'):
        pdf = page_copy(sw,2)
        key = image_key(pdf)
        original = pdf.pages[0].Resources.XObject[key]
        if arm.startswith('palette'):
            with pikepdf.open(o3) as comparator:
                candidates = [v for v in comparator.pages[2].Resources.XObject.values() if v.get('/Subtype')==pikepdf.Name.Image]
                assert len(candidates)==1
                item = candidates[0]
                assert (int(item.Width),int(item.Height))==(int(original.Width),int(original.Height))
                rgb = pikepdf.PdfImage(item).as_pil_image().convert('RGB')
                replacement = pdf.copy_foreign(item) if arm=='palette-indexed-300' else rgb_stream(pdf,rgb)
        elif arm == 'wholepage-150-q100':
            # Known whole-page fallback: no claimed separation or erasure of text.
            rgb = pikepdf.PdfImage(original).as_pil_image().convert('RGB')
            replacement = rgb_stream(pdf,rgb.resize(((rgb.width+1)//2,(rgb.height+1)//2),Image.Resampling.LANCZOS),jpeg=True)
        else:
            replacement = original
        pdf.pages[0].Resources.XObject[key]=replacement
        target=OUT/(arm+'.pdf')
        pdf.save(target,deterministic_id=True,object_stream_mode=pikepdf.ObjectStreamMode.generate)
        inventory=inspect(target)
        compact={k:inventory[k] for k in ('pdf_bytes','sha256','encoded_stream_bytes','serialized_residual_bytes','images')}
        arms[arm]={'path':str(target),'inventory':compact,'renderers':{}}
    regions = json.loads((BASE/'regions.json').read_text())['history-02']
    for renderer in ('pdfium','poppler'):
        reference = frame(source,2,renderer,300)
        images = {}
        for arm,record in arms.items():
            image=frame(record['path'],0,renderer,300)
            images[arm]=image
            image.save(OUT/f'{arm}-{renderer}.png')
            record['renderers'][renderer]={'source':features(reference,image),'regions':[]}
            for region in regions:
                w,h=reference.size
                box=tuple(round(v*(w if i%2==0 else h))for i,v in enumerate(region['box']))
                record['renderers'][renderer]['regions'].append({'label':region['label'],'source':features(reference.crop(box),image.crop(box))})
        indexed=np.asarray(images['palette-indexed-300'])
        expanded=np.asarray(images['palette-expanded-rgb-300'])
        assert np.array_equal(indexed,expanded), 'Identical palette pixels should render identically within each renderer'
        sheet([reference]+list(images.values()),['source']+list(images),OUT/f'page-{renderer}.png',cell=(300,450))
        for idx,region in enumerate(regions):
            w,h=reference.size
            box=tuple(round(v*(w if i%2==0 else h))for i,v in enumerate(region['box']))
            sheet([reference.crop(box)]+[im.crop(box)for im in images.values()],['source']+list(images),OUT/f'region{idx}-{renderer}.png',cell=(400,350))
    results={'scope':'Two controls; palette encoding/sample reduction distinguished from whole-page resolution loss. No product inference or promotion.', 'arms':arms}
    (BASE/'experiment-results.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    main()
