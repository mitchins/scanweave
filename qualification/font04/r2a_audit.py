"""R2a development-corpus transport checks. Explicit paths only; no holdout IO."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess

import pikepdf
import pypdfium2 as pdfium
from fontTools.ttLib import TTFont

from qualification.font04.metrics import inspect, sha
from qualification.font04.qualify_r1 import raster_signature

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'qualification/font04/local'


def command(args):
    env = dict(os.environ, LD_LIBRARY_PATH=str(LOCAL/'mupdf-tools/usr/lib/x86_64-linux-gnu')+':'+str(ROOT/'tools/dist/lib'))
    result = subprocess.run(list(map(str, args)), capture_output=True, env=env)
    if result.returncode:
        raise RuntimeError((args, result.returncode, result.stderr.decode(errors='replace')))
    return result.stdout


def extraction(path):
    result = {}
    for mode, flags in [('default', []), ('layout', ['-layout']), ('raw', ['-raw'])]:
        result['Poppler_'+mode] = sha_bytes(command(['pdftotext', *flags, path, '-']))
    doc = pdfium.PdfDocument(path)
    texts = []
    for page in doc:
        text = page.get_textpage()
        texts.append(text.get_text_range())
        text.close()
        page.close()
    doc.close()
    result['PDFium'] = sha_bytes(json.dumps(texts, ensure_ascii=False).encode())
    result['MuPDF'] = sha_bytes(command([LOCAL/'mupdf-tools/usr/bin/mutool', 'draw', '-q', '-F', 'txt', '-o', '-', path]))
    return result


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def fonts(path):
    result = {}
    with pikepdf.open(path) as pdf:
        for page in pdf.pages:
            for font in page.Resources.Font.values():
                if str(font.Subtype) != '/Type0':
                    continue
                stream = font.DescendantFonts[0].FontDescriptor.FontFile2
                data = stream.read_bytes()
                result[sha_bytes(data)] = (data, len(stream.read_raw_bytes()))
    return result


def audit(default, candidate, directory):
    directory.mkdir(parents=True, exist_ok=True)
    inv = [inspect(p) for p in (default, candidate)]
    text = [extraction(p) for p in (default, candidate)]
    equal = {engine: text[0][engine] == text[1][engine] for engine in text[0]}
    checks = []
    for path in (default, candidate):
        qpdf = command([ROOT/'tools/dist/bin/qpdf', '--check', path]).decode()
        ots = []
        for digest, (data, encoded) in fonts(path).items():
            dest = directory / (digest+'.ttf')
            dest.write_bytes(data)
            result = command([ROOT/'tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize', dest, str(dest)+'.sanitized']).decode()
            ots.append(dict(sha256=digest, encoded_bytes=encoded, decoded_bytes=len(data), result=result))
        checks.append(dict(pdf=str(path), sha256=sha(path), qpdf=qpdf, OTS=ots))
    geometry = lambda i: [(d['page'], d['cid'], d['character'], d['matrix'], d['invisible']) for d in i['users']]
    raster_equal = raster_signature(default) == raster_signature(candidate)
    font_bytes = [sum(size for _, size in fonts(p).values()) for p in (default, candidate)]
    result = dict(default_sha256=sha(default), candidate_sha256=sha(candidate), extraction=text,
                  text_equal_to_default=equal, checks=checks, raster_equal=raster_equal,
                  text_geometry_equal=geometry(inv[0]) == geometry(inv[1]),
                  font_bytes=font_bytes, visible_draws=[len(i['draws']) for i in inv])
    result['pass'] = all(equal.values()) and raster_equal and result['text_geometry_equal'] and font_bytes[1] <= font_bytes[0]
    (directory/'audit.json').write_text(json.dumps(result, indent=2)+'\n')
    if not result['pass']:
        raise RuntimeError('STOP: concrete corpus transport/extraction/font-growth failure: '+str(directory/'audit.json'))
    return result


if __name__ == '__main__':
    import sys
    audit(*map(Path, sys.argv[1:]))
