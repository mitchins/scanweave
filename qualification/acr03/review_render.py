"""Reproduce full-financial review sheets; fixed source-coordinate windows."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
sys.path.insert(0,'qualification/residual_resolution/local/qualification/raster_competitors')
from render_compare import frame

ROOT=Path('qualification/acr03/local/financial-all-review')
INPUTS={
    'source':'qualification/pdf_packaging/groups/financial-input.pdf',
    'Adobe':'qualification/pdf_packaging/groups/financial-adobe.pdf',
    'ACR01':'qualification/acr01/local/product/financial.pdf',
    'B':'qualification/acr03/local/financial-all-masked/complete.pdf',
}
REGIONS=((.10,.24,.48,.39),(.10,.68,.48,.83),(.76,.63,.97,.92))


def overview(images,destination):
    sheet=Image.new('RGB',(1600,620),'white')
    draw=ImageDraw.Draw(sheet)
    for column,(name,image) in enumerate(images.items()):
        sheet.paste(ImageOps.contain(image,(390,590)),(column*400,25))
        draw.text((column*400,2),name,fill='black')
    sheet.save(destination)


def regions(images,prefix):
    width,height=images['source'].size
    for number,region in enumerate(REGIONS):
        bounds=tuple(round(value*dimension) for value,dimension in zip(region,(width,height,width,height)))
        crops={name:image.crop(bounds) for name,image in images.items()}
        cw,ch=crops['source'].size
        sheet=Image.new('RGB',(cw*len(crops),ch+24),'white')
        draw=ImageDraw.Draw(sheet)
        for column,(name,image) in enumerate(crops.items()):
            sheet.paste(image,(cw*column,24))
            draw.text((cw*column,2),name,fill='black')
        sheet.save(str(prefix)+f'-r{number}.png')


def main():
    ROOT.mkdir(exist_ok=True)
    for page in range(13):
        for renderer in ('pdfium','poppler'):
            images={name:frame(path,page,renderer,300) for name,path in INPUTS.items()}
            prefix=ROOT/f'p{page:02d}-{renderer}'
            overview(images,str(prefix)+'-page.png')
            regions(images,prefix)
            print(page,renderer,flush=True)


if __name__=='__main__':main()
