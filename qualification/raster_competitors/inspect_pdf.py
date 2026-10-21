"""Read-only PDF paint/resource inventory. No inference of semantic bytes by area.

Coordinates are PDF user space, before page rotation. Clip paths are recorded,
not reduced to bounding rectangles. Form recursion preserves inherited state.
"""
import copy
import hashlib
import io
import json
import math
import zlib
from pathlib import Path

import pikepdf
from PIL import Image

IDENTITY = [1., 0., 0., 1., 0., 0.]
PATH_OPS = {'m', 'l', 'c', 'v', 'y', 'h', 're'}
PAINT_OPS = {'S', 's', 'f', 'F', 'f*', 'B', 'B*', 'b', 'b*'}
TEXT_OPS = {'Tj', 'TJ', "'", '"'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def plain(value):
    if isinstance(value, pikepdf.String):
        return {'pdf_string_hex': bytes(value).hex()}
    if isinstance(value, pikepdf.Stream):
        return {'object': list(value.objgen)}
    if isinstance(value, (pikepdf.Array, list, tuple)):
        return [plain(x) for x in value]
    if isinstance(value, pikepdf.Dictionary):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    return str(value)


def matrix(a, b):
    """Apply b in local space, then a in parent space (PDF cm)."""
    return [a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1],
            a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3],
            a[0]*b[4]+a[2]*b[5]+a[4], a[1]*b[4]+a[3]*b[5]+a[5]]


def stream_metadata(obj):
    raw = obj.read_raw_bytes()
    record = {'object': list(obj.objgen), 'encoded_bytes': len(raw),
              'encoded_sha256': digest(raw), 'filter': plain(obj.get('/Filter')),
              'decode_parameters': plain(obj.get('/DecodeParms'))}
    for key in ('Width', 'Height', 'BitsPerComponent', 'ColorSpace', 'Decode',
                'ImageMask', 'Mask', 'SMask', 'Interpolate', 'Intent'):
        record[key] = plain(obj.get('/'+key))
    try:
        im = pikepdf.PdfImage(obj).as_pil_image()
        record['decoded_samples'] = {'mode': im.mode, 'sha256': digest(im.tobytes())}
        colours = im.convert('RGB').getcolors(maxcolors=256)
        record['exact_rgb_colours_up_to_256'] = len(colours) if colours is not None else None
    except (pikepdf.PdfError, ValueError, NotImplementedError, OSError) as exc:
        record['decode_unavailable'] = str(exc)
    jpeg_raw = raw
    filters = obj.get('/Filter')
    if isinstance(filters, pikepdf.Array) and list(map(str, filters)) == ['/FlateDecode', '/DCTDecode']:
        jpeg_raw = zlib.decompress(raw)
    if jpeg_raw[:2] == b'\xff\xd8':
        with Image.open(io.BytesIO(jpeg_raw)) as jpg:
            record['jpeg'] = {'layers': jpg.layer,
                              'quantization': jpg.quantization,
                              'mode': jpg.mode, 'size': list(jpg.size),
                              'declared_density': {k: plain(jpg.info[k]) for k in ('dpi','jfif_unit','jfif_density') if k in jpg.info}}
    return record


class Inspector:
    def __init__(self, pdf):
        self.pdf = pdf
        self.images = {}
        self.pages = []
        self.font_uses = {}
        self.errors = []
        self.inline = []
        self.fonts = {}

    def image(self, obj, page, role='painted-image'):
        key = str(obj.objgen)
        if key not in self.images:
            self.images[key] = stream_metadata(obj)
            self.images[key].update(referencing_pages=[], resource_role=role)
        if page not in self.images[key]['referencing_pages']:
            self.images[key]['referencing_pages'].append(page)
        for mask in ('/SMask', '/Mask'):
            child = obj.get(mask)
            if isinstance(child, pikepdf.Stream):
                child_key = self.image(child, page, mask)
                self.images[child_key].setdefault('selected_parents', []).append({'image': key, 'mask_key': mask})
        return key

    def walk(self, container, resources, state, page, graph, ancestry):
        stack = []
        path = []
        pending_clip = None
        for instruction in pikepdf.parse_content_stream(container):
            if isinstance(instruction, pikepdf.ContentStreamInlineImage):
                image = instruction.iimage
                raw = image.read_raw_bytes()
                sx, sy = math.hypot(*state['ctm'][:2]), math.hypot(*state['ctm'][2:4])
                unit = float(self.pdf.pages[page].get('/UserUnit', 1))
                entry = {'kind': 'inline-image', 'inline_id': len(self.inline), 'page': page,
                         'dictionary': plain(image.obj), 'payload_bytes_in_decoded_content': len(raw),
                         'payload_sha256': digest(raw), 'state': copy.deepcopy(state),
                         'effective_dpi': [image.width*72/(sx*unit) if sx else None, image.height*72/(sy*unit) if sy else None],
                         'serialized_bytes': None, 'classification': 'inline-stencil' if image.image_mask else 'mixed-inline-raster'}
                self.inline.append(entry)
                graph.append(entry)
                continue
            operands, operator = instruction
            op = str(operator)
            if op == 'q':
                stack.append(copy.deepcopy(state))
            elif op == 'Q':
                if not stack:
                    raise ValueError('unbalanced graphics-state stack')
                state = stack.pop()
            elif op == 'cm':
                state['ctm'] = matrix(state['ctm'], list(map(float, operands)))
            elif op == 'gs':
                ext = resources.get('/ExtGState', {}).get(operands[0], {})
                for key in ('/ca', '/CA', '/BM', '/SMask', '/AIS'):
                    if key in ext:
                        state['transparency'][key] = plain(ext[key])
            elif op in ('g', 'G', 'rg', 'RG', 'k', 'K', 'cs', 'CS', 'sc', 'SC', 'scn', 'SCN', 'w', 'J', 'j', 'M', 'd', 'ri'):
                state['graphics'][op] = plain(list(operands))
            elif op in PATH_OPS:
                path.append({'op': op, 'args': plain(list(operands)), 'ctm': state['ctm'][:]})
            elif op in ('W', 'W*'):
                pending_clip = op
            elif op in PAINT_OPS or op == 'n':
                if op != 'n':
                    graph.append({'kind': 'non-font-vector', 'paint': op, 'path': path[:],
                                  'state': copy.deepcopy(state)})
                if pending_clip:
                    state['clips'].append({'rule': pending_clip, 'path': path[:]})
                path = []
                pending_clip = None
            elif op == 'Tf':
                state['font'] = str(operands[0])
                graph.append({'kind': 'text-state', 'operator': op, 'arguments': plain(list(operands))})
            elif op == 'Tr':
                state['text_render_mode'] = int(operands[0])
                graph.append({'kind': 'text-state', 'operator': op, 'arguments': plain(list(operands))})
            elif op in TEXT_OPS:
                font = resources.get('/Font', {}).get(state.get('font'))
                key = ('direct:'+digest(json.dumps(plain(font),sort_keys=True).encode()) if font is not None and font.objgen == (0,0) else str(font.objgen) if font is not None else 'unknown')
                mode = state['text_render_mode']
                self.font_uses.setdefault(key, set()).add(mode)
                if font is not None:
                    self.fonts[key] = plain(font)
                graph.append({'kind': 'text', 'font_object': key, 'render_mode': mode,
                              'operator': op, 'arguments': plain(list(operands)), 'state': copy.deepcopy(state)})
            elif op in ('BT', 'ET', 'Tm', 'Td', 'TD', 'T*', 'Tc', 'Tw', 'Tz', 'TL', 'Ts'):
                graph.append({'kind': 'text-state', 'operator': op, 'arguments': plain(list(operands))})
                if op == 'ET' and state['text_render_mode'] >= 4:
                    state['clips'].append({'text_clip': 'see preceding text operations'})
            elif op == 'sh':
                graph.append({'kind': 'shading', 'name': str(operands[0]),
                              'state': copy.deepcopy(state)})
            elif op == 'Do':
                obj = resources.get('/XObject', {})[operands[0]]
                subtype = str(obj.get('/Subtype'))
                if subtype == '/Form':
                    if obj.objgen in ancestry:
                        raise ValueError('cyclic Form XObject')
                    local = copy.deepcopy(state)
                    local['ctm'] = matrix(state['ctm'], list(map(float, obj.get('/Matrix', IDENTITY))))
                    local['clips'].append({'form_bbox': plain(obj.get('/BBox')),
                                           'ctm': local['ctm'][:]})
                    children = []
                    graph.append({'kind': 'form', 'object': list(obj.objgen),
                                  'group': plain(obj.get('/Group')), 'children': children})
                    self.walk(obj, obj.get('/Resources', resources), local, page,
                              children, ancestry | {obj.objgen})
                elif subtype == '/Image':
                    key = self.image(obj, page)
                    ctm = state['ctm']
                    sx, sy = math.hypot(*ctm[:2]), math.hypot(*ctm[2:4])
                    unit = float(self.pdf.pages[page].get('/UserUnit', 1))
                    graph.append({'kind': 'image', 'resource': key,
                                  'effective_dpi': [float(obj.Width)*72/(sx*unit) if sx else None,
                                                    float(obj.Height)*72/(sy*unit) if sy else None],
                                  'state': copy.deepcopy(state),
                                  'classification': 'stencil' if obj.get('/ImageMask', False)
                                  else 'mixed-raster-content-unclassified'})
                else:
                    graph.append({'kind': 'unknown-xobject', 'subtype': subtype})

    def run(self):
        for index, page in enumerate(self.pdf.pages):
            state = {'ctm': IDENTITY[:], 'clips': [], 'transparency': {},
                     'text_render_mode': 0, 'font': None, 'graphics': {}}
            graph = []
            self.walk(page, page.Resources, state, index, graph, set())
            self.pages.append({'page': index, 'MediaBox': plain(page.MediaBox),
                               'CropBox': plain(page.get('/CropBox', page.MediaBox)),
                               'Rotate': plain(page.get('/Rotate', 0)),
                               'UserUnit': plain(page.get('/UserUnit', 1)), 'paint_graph': graph})
        return {'pages': self.pages, 'images': self.images,
                'inline_images': self.inline, 'fonts': self.fonts, 'font_render_modes': {k: sorted(v) for k, v in self.font_uses.items()}}


def pack_states(result):
    """Intern repeated forensic state, preserving an explicit graph reference."""
    states = {}
    def visit(graph):
        for node in graph:
            if isinstance(node.get('state'), dict):
                state = node.pop('state')
                key = digest(json.dumps(state, sort_keys=True).encode())
                states[key] = state
                node['state_ref'] = key
            visit(node.get('children', []))
    for page in result['pages']:
        visit(page['paint_graph'])
    result['graphics_states'] = states
    return result


def inspect(path):
    with pikepdf.open(path) as pdf:
        result = Inspector(pdf).run()
        font_streams = set()
        for obj in pdf.objects:
            if isinstance(obj, pikepdf.Dictionary):
                for key in ('/FontFile', '/FontFile2', '/FontFile3'):
                    if key in obj:
                        font_streams.add(obj[key].objgen)
                if obj.get('/Subtype') == pikepdf.Name.Type3:
                    font_streams.update(v.objgen for v in obj.get('/CharProcs', {}).values())
        totals = {'image': 0, 'font_program': 0, 'other_stream': 0}
        for obj in pdf.objects:
            if not isinstance(obj, pikepdf.Stream):
                continue
            category = ('image' if obj.get('/Subtype') == pikepdf.Name.Image else
                        'font_program' if obj.objgen in font_streams else 'other_stream')
            totals[category] += len(obj.read_raw_bytes())
        profiles = {}
        for obj in pdf.objects:
            if isinstance(obj, pikepdf.Stream) and '/N' in obj and '/Alternate' in obj:
                profiles[str(obj.objgen)] = {'N': int(obj.N), 'Alternate': plain(obj.Alternate),
                                             'encoded_bytes': len(obj.read_raw_bytes()), 'decoded_sha256': digest(obj.read_bytes())}
        result['colour_profiles'] = profiles
        size = Path(path).stat().st_size
        result.update(path=str(path), sha256=digest(Path(path).read_bytes()),
                      pdf_bytes=size, encoded_stream_bytes=totals,
                      serialized_residual_bytes=size-sum(totals.values()),
                      unique_encoded_image_hashes=len({i['encoded_sha256'] for i in result['images'].values()}),
                      unique_decoded_image_hashes=len({i['decoded_samples']['sha256'] for i in result['images'].values() if 'decoded_samples' in i}))
        return pack_states(result)
