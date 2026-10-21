"""Derivative-only paint isolation with ordered tagged replay verification.

The corpus's text modes must be 0 or 3. Isolated components are not claimed
additive RGB arrays: ordered replay retains original clipping/alpha/paint order.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pikepdf
from render_compare import BASE, LOCAL, frame, sheet
from inspect_pdf import PAINT_OPS, TEXT_OPS

SELECTED = ('cord-00','history-01','history-02','history-04','scan-c03-29','scan-linn','annual-111','nara-form-01')


def rewrite(pdf, container, resources, mode, seen, keep_image=None):
    output = []
    text_mode = 0
    stack = []
    for item in pikepdf.parse_content_stream(container):
        if isinstance(item,pikepdf.ContentStreamInlineImage):
            if mode not in ('fonts',) and keep_image is None:
                output.append(item)
            continue
        operands, operator = item
        op = str(operator)
        if op == 'q':
            stack.append(text_mode)
        elif op == 'Q':
            text_mode = stack.pop()
        elif op == 'Tr':
            text_mode = int(operands[0])
            if text_mode not in (0,3):
                raise ValueError('Text clipping/stroking mode requires a different isolation contract')
        if op == 'Do':
            obj=resources.XObject[operands[0]]
            if obj.get('/Subtype')==pikepdf.Name.Form:
                if obj.objgen not in seen:
                    seen.add(obj.objgen)
                    child=rewrite(pdf,obj,obj.get('/Resources',resources),mode,seen,keep_image)
                    obj.write(pikepdf.unparse_content_stream(child))
            elif obj.get('/Subtype')==pikepdf.Name.Image:
                if mode=='fonts' or (keep_image is not None and obj.objgen!=keep_image):
                    continue
        if op in PAINT_OPS and (mode in ('fonts','images') or keep_image is not None):
            output.append(pikepdf.ContentStreamInstruction([],pikepdf.Operator('n')))
            continue
        if op in TEXT_OPS and mode!='fonts' and mode!='recombined':
            output.extend([pikepdf.ContentStreamInstruction([3],pikepdf.Operator('Tr')),item,
                           pikepdf.ContentStreamInstruction([text_mode],pikepdf.Operator('Tr'))])
            continue
        if mode=='recombined' and (op in TEXT_OPS or op in PAINT_OPS or op=='Do'):
            tag='FontPaint' if op in TEXT_OPS else 'OtherPaint'
            output.extend([pikepdf.ContentStreamInstruction([pikepdf.Name('/'+tag)],pikepdf.Operator('BMC')),
                           item,pikepdf.ContentStreamInstruction([],pikepdf.Operator('EMC'))])
        else:
            output.append(item)
    return output


def main():
    inventory=json.loads((BASE/'object-inventory.json').read_text())
    results=[]
    out=LOCAL/'layers';out.mkdir(exist_ok=True,parents=True)
    for document in inventory:
        if document['arm'] not in ('adobe','ocrmypdf3','scanweave','archive'):
            continue
        for index,name in enumerate(document['members']):
            if name not in SELECTED:
                continue
            print(name,document['arm'],flush=True)
            row={'id':name,'arm':document['arm'],'source_pdf':document['path'],'page':index,'derivatives':{},'renderers':{}}
            # Keep whole document context/resources. No source files are written.
            for mode in ('fonts','nonfont','images','recombined'):
                with pikepdf.open(document['path']) as pdf:
                    page=pdf.pages[index]
                    operations=rewrite(pdf,page,page.Resources,mode,set())
                    page.Contents=pikepdf.Stream(pdf,pikepdf.unparse_content_stream(operations))
                    destination=out/f'{name}-{document["arm"]}-{mode}.pdf'
                    pdf.save(destination,deterministic_id=True)
                    row['derivatives'][mode]={'path':str(destination),'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}
            for renderer in ('pdfium','poppler'):
                original=frame(document['path'],index,renderer,150)
                parts={mode:frame(item['path'],index,renderer,150)for mode,item in row['derivatives'].items()}
                exact=bool(np.array_equal(np.asarray(original),np.asarray(parts['recombined'])))
                if not exact:
                    raise ValueError('Ordered replay mismatch: '+name+' '+document['arm']+' '+renderer)
                for mode,image in parts.items():
                    image.save(out/f'{name}-{document["arm"]}-{mode}-{renderer}.png')
                row['renderers'][renderer]={'ordered_replay_pixel_identical':exact}
                sheet([original,parts['fonts'],parts['nonfont'],parts['images']],['complete','font-only','non-font','images-only'],out/f'{name}-{document["arm"]}-{renderer}-sheet.png',cell=(320,460))
            results.append(row)
    (BASE/'layer-results.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    main()
