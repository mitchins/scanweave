"""Ablate prototype image paints without changing clipping/placement/font operators."""
import pikepdf
from prototype import ROOT, CASES
from anatomy import derivative, atlas
from render_compare import frame


def isolate_images(source,index,destination,paper):
    with pikepdf.open(source) as pdf:
        page=pdf.pages[index]
        operations=[]
        for item in pikepdf.parse_content_stream(page):
            if isinstance(item,pikepdf.ContentStreamInlineImage):
                raise ValueError('Unexpected inline image')
            op=str(item.operator)
            if op=='Do':
                is_paper=str(item.operands[0])=='/Object0'
                if is_paper==paper:
                    operations.append(item)
            elif op not in ('Tj','TJ',"'",'"'):
                operations.append(item)
        page.Contents=pikepdf.Stream(pdf,pikepdf.unparse_content_stream(operations))
        pdf.save(destination,deterministic_id=True,object_stream_mode=pikepdf.ObjectStreamMode.generate)


def main():
    for case,(_,index) in CASES.items():
        for mode in ('crops','masked'):
            folder=ROOT/f'{case}-{mode}'
            if mode=='masked' and case in ('seal','shade'):
                folder=ROOT/'rejected'/folder.name
            source=folder/'complete.pdf'
            for name in ('paper','objects'):
                isolate_images(source,index,folder/f'{name}-only.pdf',name=='paper')
            derivative(source,index,'fonts',folder/'fonts-only.pdf')
            derivative(source,index,'nonfont',folder/'raster-only.pdf')
            for engine in ('pdfium','poppler'):
                images=[frame(str(folder/f'{name}-only.pdf'),index,engine,120) for name in ('paper','objects','fonts')]
                images.append(frame(str(source),index,engine,120))
                atlas(images,['paper','retained objects/ink','visible fonts','complete'],folder/f'{engine}-layers.png')


if __name__=='__main__':main()
