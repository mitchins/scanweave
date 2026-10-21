"""Isolate actual image XObjects while retaining their source clips and masks."""
import json
from pathlib import Path
import pikepdf
from layers import rewrite
from render_compare import BASE, LOCAL, frame, sheet

SELECTED = ((2, 'history-02'), (4, 'history-04'))


def main():
    records=json.loads((BASE/'object-inventory.json').read_text())
    out=LOCAL/'components';out.mkdir(parents=True,exist_ok=True)
    results=[]
    for record in records:
        if record['arm'] not in ('adobe','archive') or record['collection']!='historical':
            continue
        for index,name in SELECTED:
            with pikepdf.open(record['path']) as source:
                images=[(k,o.objgen)for k,o in source.pages[index].Resources.XObject.items() if o.get('/Subtype')==pikepdf.Name.Image]
            for resource,objgen in images:
                key=resource.lstrip('/')
                path=out/f'{name}-{record["arm"]}-{key}.pdf'
                with pikepdf.open(record['path']) as pdf:
                    page=pdf.pages[index]
                    operations=rewrite(pdf,page,page.Resources,'images',set(),keep_image=objgen)
                    page.Contents=pikepdf.Stream(pdf,pikepdf.unparse_content_stream(operations))
                    pdf.save(path,deterministic_id=True)
                    obj=pdf.get_object(objgen)
                    if '/SMask' in obj:
                        mask=pikepdf.PdfImage(obj.SMask).as_pil_image()
                        mask.save(out/f'{name}-{record["arm"]}-{key}-smask.png')
                for renderer in ('pdfium','poppler'):
                    image=frame(path,index,renderer,150)
                    image.save(out/f'{name}-{record["arm"]}-{key}-{renderer}.png')
                results.append({'id':name,'arm':record['arm'],'object':list(objgen),'resource':resource,'path':str(path)})
    (BASE/'component-results.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    main()
