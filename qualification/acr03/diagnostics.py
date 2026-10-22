"""Fixed source-selected defect and representation diagnostics. Read-only inputs."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from prototype import ROOT, CASES, paths, frame, paper_and_chroma, boxes


def main():
    rows=[]
    for case,(group,index) in CASES.items():
        source=np.asarray(frame(str(paths(group)[0]),index,'pdfium',300),dtype=np.float32)
        paper,chroma,unknown=paper_and_chroma(source)
        objects=boxes(ndi.binary_fill_holes(ndi.binary_closing(chroma,iterations=2)),(13,13),4)
        outside=unknown.copy()
        for x0,y0,x1,y1 in objects:
            outside[y0:y1,x0:x1]=False
        # Audit the actual retained support saved by the prototype, not OCR boxes.
        folder=ROOT/f'{case}-masked'
        if case in ('seal','shade'):
            folder=ROOT/'rejected'/f'{case}-masked'
        fine=np.asarray(Image.open(folder/'retained-ink-mask.png'))>0
        support=ndi.binary_dilation(fine,iterations=2)
        row={'case':case,'source_dimensions':list(source.shape[:2][::-1]),
             'unknown_paper_pixels':int(unknown.sum()),'unknown_outside_initial_colour_boxes':int(outside.sum()),
             'retained_ink_area_fraction':float(fine.mean()),'dilated_support_fraction':float(support.mean()),
             'paper_mean_rgb':paper.mean(axis=(0,1)).tolist()}
        if case=='logo':
            x,y=1230,270
            row['acr02_counterexample']={'x':x,'y':y,'source_rgb':source[y,x].tolist(),'new_paper_rgb':paper[y,x].tolist(),
                                        'source_chromatic_object':bool(chroma[y,x]),'old_mask_coverage':0,
                                        'old_paper_rgb':[20,85,149]}
        rows.append(row)
    full=[]
    for folder in sorted((ROOT/'financial-masked').glob('page-*')):
        result=json.loads((folder/'result.json').read_text())
        if 'fallback' in result:
            full.append(result);continue
        fine=np.asarray(Image.open(folder/'retained-ink-mask.png'))>0
        result['retained_ink_area_fraction']=float(fine.mean())
        result['dilated_support_fraction']=float(ndi.binary_dilation(fine,iterations=2).mean())
        full.append(result)
    output={'fixed_cases':rows,'financial_pages':full}
    (ROOT/'diagnostics.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(rows,indent=2))


if __name__=='__main__':main()
