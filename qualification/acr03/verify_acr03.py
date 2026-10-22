"""Read-only semantic/resource checks for the fixed ACR03 prototype outputs."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pikepdf
import pypdfium2 as pdfium

from prototype import CASES, ROOT, paths
sys.path.append(str(Path(__file__).resolve().parents[1]))
from tools_env import qpdf_bin, qpdf_env
from render_compare import frame


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect(path):
    with pikepdf.open(path) as pdf:
        images, fonts, unicode = {}, {}, {}
        encoded_fonts, contents = {}, {}
        text_operations = []
        for page in pdf.pages:
            streams=page.Contents if isinstance(page.Contents,pikepdf.Array) else [page.Contents]
            for stream in streams:
                contents[stream.objgen]=len(stream.read_raw_bytes())
            operations = []
            for item in pikepdf.parse_content_stream(page):
                if isinstance(item, pikepdf.ContentStreamInlineImage):
                    continue
                if str(item.operator) in ('Tj', 'TJ', 'Tm', 'Tf', 'BDC', 'EMC'):
                    operations.append(pikepdf.unparse_content_stream([item]))
            text_operations.append(digest(b'\n'.join(operations)))
            for font in page.Resources.Font.values():
                if '/ToUnicode' in font:
                    unicode[digest(font.ToUnicode.read_bytes())] = len(font.ToUnicode.read_bytes())
                for descendant in font.get('/DescendantFonts', []):
                    descriptor = descendant.get('/FontDescriptor')
                    if descriptor:
                        for key in ('/FontFile', '/FontFile2', '/FontFile3'):
                            if key in descriptor:
                                data = descriptor[key].read_bytes()
                                fonts[digest(data)] = len(data)
                                stream=descriptor[key]
                                encoded_fonts[stream.objgen]=len(stream.read_raw_bytes())
            for image in page.Resources.XObject.values():
                if image.get('/Subtype') != pikepdf.Name.Image:
                    raise ValueError('Fixed prototype unexpected Form')
                for role, obj in [('image',image),('mask',image.get('/SMask'))]:
                    if obj is not None:
                        images[obj.objgen] = {'role':role,'bytes':len(obj.read_raw_bytes()),'filter':str(obj.get('/Filter'))}
        boxes = [[list(p.MediaBox),list(p.get('/CropBox',p.MediaBox))] for p in pdf.pages]
    doc = pdfium.PdfDocument(str(path))
    native = []
    for page in doc:
        textpage = page.get_textpage()
        native.append(textpage.get_text_bounded())
        textpage.close()
        page.close()
    doc.close()
    poppler = subprocess.run(['pdftotext','-layout',str(path),'-'],check=True,capture_output=True).stdout
    return {'pdf_bytes':path.stat().st_size,'sha256':digest(path.read_bytes()),
            'encoded_font_program_bytes':sum(encoded_fonts.values()),'content_stream_bytes':sum(contents.values()),
            'font_programs':fonts,'unicode_maps':unicode,'text_operators':text_operations,
            'page_boxes':boxes,'pdfium_text_sha256':digest('\f'.join(native).encode()),
            'poppler_text_sha256':digest(poppler),'resources':list(images.values())}


def main():
    checked=[]
    for case in CASES:
        group,_ = CASES[case]
        baseline = inspect(paths(group)[1])
        for mode in ['crops','masked'] + (['crops-oracle'] if case in ('logo','annotation') else []):
            path=ROOT/f'{case}-{mode}'/'complete.pdf'
            actual=inspect(path)
            equality={key:baseline[key]==actual[key] for key in ('font_programs','unicode_maps','text_operators','page_boxes','pdfium_text_sha256','poppler_text_sha256')}
            checked.append({'case':case,'mode':mode,'path':str(path),'equality':equality,'accounting':actual})
    baseline=inspect(paths('financial')[1])
    path=ROOT/'financial-all-masked/complete.pdf'
    actual=inspect(path)
    checked.append({'case':'financial-all','path':str(path),'equality':{key:baseline[key]==actual[key] for key in ('font_programs','unicode_maps','text_operators','page_boxes','pdfium_text_sha256','poppler_text_sha256')},'accounting':actual})
    fallback=ROOT/'historical-fallback/complete.pdf'
    if digest(fallback.read_bytes()) != digest(paths('historical')[1].read_bytes()):
        raise SystemExit('Historical fallback differs from frozen baseline')
    frozen=json.loads(Path('qualification/acr01/local/frozen-hashes.json').read_text())
    hashes=[{'path':row['path'],'unchanged':digest(Path(row['path']).read_bytes())==row['sha256']} for row in frozen]
    pdf_checks=[]
    for row in checked:
        run=subprocess.run([qpdf_bin(),'--check',row['path']],env=qpdf_env(),capture_output=True,text=True,check=True)
        pdf_checks.append({'path':row['path'],'exit':run.returncode})
    control=ROOT/'financial-save-control.pdf'
    control_data=inspect(control)
    control_equality={key:baseline[key]==control_data[key] for key in ('font_programs','unicode_maps','text_operators','page_boxes','pdfium_text_sha256','poppler_text_sha256')}
    render_equality={engine:digest(frame(str(paths('financial')[1]),10,engine,300).tobytes())==digest(frame(str(control),10,engine,300).tobytes()) for engine in ('pdfium','poppler')}
    if not all(control_equality.values()) or not all(render_equality.values()):
        raise SystemExit('Save-only control changed semantics/render')
    result={'checks':checked,'frozen_hashes':hashes,'qpdf':pdf_checks,'save_control_equality':control_equality,'save_control_page10_render_equality':render_equality}
    (ROOT/'verification.json').write_text(json.dumps(result,indent=2,default=float)+'\n')
    if not all(all(row['equality'].values()) for row in checked) or not all(row['unchanged'] for row in hashes):
        raise SystemExit('Verification mismatch: see local/verification.json')
    print(f'{len(checked)} prototype PDFs: font programs, ToUnicode, text placement/show operators, geometry, PDFium and Poppler text equal. {len(hashes)} frozen hashes unchanged.')


if __name__=='__main__':
    main()
