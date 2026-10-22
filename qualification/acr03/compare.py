"""Fixed physical-coordinate ACR03 sheets and pixel diagnostics, no registration."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

from prototype import ROOT, CASES, paths
from anatomy import atlas, derivative
from render_compare import frame, features

REGIONS = {'logo': [(1040,140,1420,440)], 'annotation': [(90,800,1060,1030)],
           'seal': [(.12,.70,.88,.92)], 'financial': [(.12,.70,.88,.92),(.78,.64,.97,.91)],
           'shade': [(.00,.00,.28,.25),(.07,.13,.90,.50)]}


def binding(case):
    group, index = CASES[case]
    source, baseline = paths(group)
    if group == 'controlled':
        return source, Path('qualification/acr02/local/prototype-adobe.pdf'), baseline, Path('qualification/acr02/local/prototype-controlled-indexed.pdf'), index
    acr2 = 'financial-full13-indexed16.pdf' if group=='financial' else 'history-indexed16.pdf'
    return source, Path(f'qualification/pdf_packaging/groups/{group}-adobe.pdf'), baseline, Path('qualification/acr02/local')/acr2, index


def main():
    rows=[]
    for case in CASES:
        source,adobe,baseline,acr2,index=binding(case)
        candidate=ROOT/(case+'-crops')/'complete.pdf'
        folder=ROOT/'comparison'/case;folder.mkdir(parents=True,exist_ok=True)
        names=['source','Adobe XI','ACR01','ACR02','ACR03 crops','ACR03 masked tiles']
        masked=ROOT/(case+'-masked')/'complete.pdf'
        if case in ('seal','shade'):
            masked=ROOT/'rejected'/(case+'-masked')/'complete.pdf'
            names[-1]+=' (rejected)'
        inputs=[source,adobe,baseline,acr2,candidate,masked]
        if case in ('logo','annotation'):
            inputs.append(ROOT/(case+'-crops-oracle')/'complete.pdf');names.append('oracle objects')
        for engine in ('pdfium','poppler'):
            images=[frame(str(path),index,engine,300) for path in inputs]
            atlas(images,names,folder/f'{engine}-page.png')
            for number,region in enumerate(REGIONS[case]):
                rect=region
                if max(region)<=1:
                    rect=tuple(round(c*(images[0].width if j%2==0 else images[0].height)) for j,c in enumerate(region))
                crops=[im.crop(rect) for im in images]
                canvas=Image.new('RGB',(crops[0].width*len(crops),crops[0].height+25),'white');d=ImageDraw.Draw(canvas)
                for i,crop in enumerate(crops):
                    canvas.paste(crop,(i*crop.width,25));d.text((i*crop.width,3),names[i],fill='black')
                canvas.save(folder/f'{engine}-r{number}.png')
                rows.append({'case':case,'renderer':engine,'region':number,'source_pixels_300dpi':rect,
                             'metrics':{name:features(crops[0],im) for name,im in zip(names[1:],crops[1:])}})
        # Reuse original clipping/font semantics for inspection derivatives.
        for mode in ('fonts','nonfont'):
            derivative(candidate,index,mode,folder/f'{mode}.pdf')
    (ROOT/'region-results.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':main()
