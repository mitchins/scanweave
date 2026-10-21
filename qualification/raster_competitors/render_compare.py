"""Fixed-coordinate source-relative comparisons; no pristine references or crop alignment."""
import hashlib
import io
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pikepdf
import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageOps
from scipy import ndimage

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
ARMS = ('input', 'adobe', 'ocrmypdf1', 'ocrmypdf3', 'archive', 'scanweave')
DISPLAY = ('input', 'adobe', 'ocrmypdf3', 'scanweave')
LOCAL = BASE/'local'


RENDER_CONTRACT = 'mediabox-original-clip-v1'


def media_canvas_copy(path, index):
    """Preserve visible CropBox as a clip, align both engines to MediaBox.

    Keep full document resources/output intents. No source bytes are written.
    Annotations need their own clipping contract and are rejected if present.
    """
    with pikepdf.open(path) as pdf:
        page=pdf.pages[index]
        media=page.MediaBox
        crop=page.get('/CropBox',media)
        if list(map(float,crop))==list(map(float,media)):
            return None
        if page.get('/Annots'):
            raise ValueError('Nonstandard CropBox with annotations needs explicit rendering support')
        left,bottom,right,top=crop
        clip=f'q {left} {bottom} {right-left} {top-bottom} re W n\n'.encode()
        contents=page.get('/Contents',[])
        streams=list(contents) if isinstance(contents,pikepdf.Array) else [contents]
        page.Contents=pikepdf.Array([pikepdf.Stream(pdf,clip),*streams,pikepdf.Stream(pdf,b'\nQ')])
        page.CropBox=pikepdf.Array(media)
        buffer=io.BytesIO()
        pdf.save(buffer,deterministic_id=True)
        return buffer.getvalue()


def frame(path, index, renderer, dpi):
    payload=media_canvas_copy(path,index)
    if renderer == 'pdfium':
        with pdfium.PdfDocument(payload if payload is not None else str(path)) as doc:
            page = doc[index]
            return page.render(scale=dpi/72).to_pil().convert('RGB')
    with tempfile.TemporaryDirectory() as temp:
        stem = Path(temp)/'page'
        source=Path(path)
        if payload is not None:
            source=Path(temp)/'clipped-media-canvas.pdf'
            source.write_bytes(payload)
        subprocess.run(['pdftoppm', '-f', str(index+1), '-l', str(index+1),
                        '-singlefile', '-r', str(dpi), '-png', str(source), str(stem)],
                       check=True, capture_output=True, timeout=180)
        return Image.open(stem.with_suffix('.png')).convert('RGB')


def features(source, candidate):
    a, b = np.asarray(source).astype(np.float32), np.asarray(candidate).astype(np.float32)
    geometry = {'source_shape':list(a.shape), 'candidate_shape':list(b.shape),
                'equal_canvas':a.shape == b.shape, 'contract':'shared top-left physical coordinates; no resize or alignment'}
    h,w=min(a.shape[0],b.shape[0]),min(a.shape[1],b.shape[1])
    geometry['compared_overlap_pixels']=h*w
    geometry['uncompared_source_pixels']=int(a.shape[0]*a.shape[1]-h*w)
    geometry['uncompared_output_pixels']=int(b.shape[0]*b.shape[1]-h*w)
    a,b=a[:h,:w],b[:h,:w]
    ga, gb = a @ np.array([.2126,.7152,.0722]), b @ np.array([.2126,.7152,.0722])
    edge_error = sum(float(np.abs(np.diff(ga,axis=k)-np.diff(gb,axis=k)).mean()) for k in (0,1))/2
    metrics = {'geometry':geometry, 'mae':float(np.abs(a-b).mean()), 'max_channel_error':float(np.abs(a-b).max()),
               'gradient_mae': edge_error, 'mean_rgb_shift': (b-a).mean(axis=(0,1)).tolist(),
               'source_local_contrast_std': float(ga.std()), 'output_local_contrast_std':float(gb.std())}
    for name, sign in (('dark',1),('light',-1)):
        base, out = sign*ga, sign*gb
        surround = ndimage.maximum_filter(base, size=5)
        out_surround = ndimage.maximum_filter(out, size=5)
        # Local 5x5 contrast witnesses, not semantic foreground labels.
        contrast = surround-base
        retained = out_surround-out
        marked = contrast >= 12
        metrics[name+'_contrast_witnesses'] = int(marked.sum())
        metrics[name+'_contrast_witnesses_below_half'] = int((marked & (retained < contrast*.5)).sum())
        mask = marked & (base < ndimage.uniform_filter(base,size=15)-8)
        other = (retained >= 12) & (out < ndimage.uniform_filter(out,size=15)-8)
        metrics[name+'_local_components_source'] = int(ndimage.label(mask)[1])
        metrics[name+'_local_components_output'] = int(ndimage.label(other)[1])
    return metrics


def render_cached(path, index, renderer, dpi, name, source_sha256):
    target = LOCAL/'renders'/f'{name}-{source_sha256}-p{index}-{renderer}-{dpi}-{RENDER_CONTRACT}.png'
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        return Image.open(target).convert('RGB')
    image = frame(path,index,renderer,dpi)
    image.save(target)
    return image


def sheet(images, labels, destination, cell=(300,420)):
    canvas = Image.new('RGB',(cell[0]*len(images),cell[1]),'#ddd')
    draw = ImageDraw.Draw(canvas)
    for i,(im,label) in enumerate(zip(images,labels)):
        thumb = ImageOps.contain(im,(cell[0]-8,cell[1]-30))
        canvas.paste(thumb,(i*cell[0]+4,26))
        draw.text((i*cell[0]+4,5),label,fill='black')
    destination.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(destination)


def main():
    inventory = json.loads((BASE/'object-inventory.json').read_text())
    docs = {(d['collection'],d['arm']):d for d in inventory}
    regions = json.loads((BASE/'regions.json').read_text())
    results = {'contract':'MediaBox canvas with original CropBox preserved as explicit clip in derivative only; 100 DPI pages / 300 DPI regions; fixed source physical coordinates, no candidate alignment', 'pages':[], 'regions':[]}
    for collection in dict.fromkeys(d['collection'] for d in inventory):
        members = docs[(collection,'input')]['members']
        for index,name in enumerate(members):
            print(name,flush=True)
            for renderer in ('pdfium','poppler'):
                images = {arm:render_cached(docs[(collection,arm)]['path'],index,renderer,100,f'{name}-{arm}',docs[(collection,arm)]['sha256']) for arm in ARMS}
                for arm,image in images.items():
                    results['pages'].append({'id':name,'arm':arm,'renderer':renderer,'dpi':100,
                                             'metrics':features(images['input'],image)})
                sheet([images[a] for a in DISPLAY],list(DISPLAY),LOCAL/'sheets'/f'{name}-{renderer}-page.png')
                if name not in regions:
                    continue
                detailed = {arm:render_cached(docs[(collection,arm)]['path'],index,renderer,300,f'{name}-{arm}',docs[(collection,arm)]['sha256']) for arm in DISPLAY}
                # Crop every arm using source dimensions, never fit to candidate content.
                width,height = detailed['input'].size
                for rid,region in enumerate(regions[name]):
                    box = tuple(round(v*(width if k%2==0 else height)) for k,v in enumerate(region['box']))
                    crops = {arm:im.crop(box) for arm,im in detailed.items()}
                    for arm,image in crops.items():
                        results['regions'].append({'id':name,'region':rid,'class':region['class'],'label':region['label'],
                                                   'box_300dpi':box,'arm':arm,'renderer':renderer,'metrics':features(crops['input'],image)})
                    sheet([crops[a] for a in DISPLAY],list(DISPLAY),LOCAL/'sheets'/f'{name}-{renderer}-region{rid}.png',cell=(440,330))
    (BASE/'region-results.json').write_text(json.dumps(results,indent=2)+'\n')
    artifacts = [{'path':str(p.relative_to(BASE)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes':p.stat().st_size} for p in sorted((LOCAL/'sheets').glob('*.png'))]
    (BASE/'render-manifest.json').write_text(json.dumps(artifacts,indent=2)+'\n')


if __name__ == '__main__':
    main()
