"""Physical-coordinate regression: independent PDF rectangles through frame inverse.

Rectangles are defined in PDF points first. Their exact outline edges are encoded
in canvas centre coordinates (edge + .5), independent of the inverse under test.
PDFium at 32x measures emitted physical centroids against those original points.
This isolates coordinate conventions from tracing/threshold/registration error.
"""
import json
from pathlib import Path
import numpy as np
import pikepdf
import pypdfium2 as pdfium
from scipy import ndimage
from qualification.font04.planner import frame_bbox


def main():
    root=Path('qualification/font04/local/coordinate-roundtrip');root.mkdir(parents=True,exist_ok=True)
    records=[]
    for dpi in (200,300,600):
        pdf=pikepdf.Pdf.new();cells=[]
        for xheight in (8.,16.,26.,48.):
            for ox in (0.,.25,.5,.75):
                for oy in (0.,.25,.5,.75):
                    # Ground truth is physical PDF points; y is top-down here.
                    physical=np.array([(24+ox)*72/dpi,(24+oy)*72/dpi,
                                       (24+ox+.625*xheight)*72/dpi,
                                       (24+oy+xheight)*72/dpi])
                    pixel=physical*dpi/72
                    frame=dict(cx=32.,baseline=80.,scale=32/xheight)
                    origin=((pixel[0]-frame['cx'])*frame['scale']+32+.5,
                            (pixel[1]-frame['baseline'])*frame['scale']+48+.5)
                    size=((pixel[2]-pixel[0])*frame['scale'],(pixel[3]-pixel[1])*frame['scale'])
                    fixed=np.array(frame_bbox(frame,origin,size))*72/dpi
                    old=fixed+.5/frame['scale']*72/dpi
                    for arm,b in [('fixed',fixed),('old',old)]:
                        page=pdf.add_blank_page(page_size=(96*72/dpi,96*72/dpi));x,y,xx,yy=b
                        page.Contents=pdf.make_stream(f'0 g {x:.12f} {96*72/dpi-yy:.12f} {xx-x:.12f} {yy-y:.12f} re f\n'.encode())
                        cells.append((xheight,ox,oy,arm,physical))
        path=root/f'{dpi}.pdf';pdf.save(path,deterministic_id=True)
        doc=pdfium.PdfDocument(path)
        for i,(xh,ox,oy,arm,physical) in enumerate(cells):
            page=doc[i];bitmap=page.render(scale=dpi*32/72,grayscale=True)
            ink=1-np.asarray(bitmap.to_pil(),float)/255
            cy,cx=ndimage.center_of_mass(ink)
            observed=np.array([cx+.5,cy+.5])/32
            expected=np.array([(physical[0]+physical[2])/2,(physical[1]+physical[3])/2])*dpi/72
            delta=observed-expected
            records.append(dict(dpi=dpi,xheight=xh,offset=[ox,oy],arm=arm,centroid_dx_dy=delta.tolist(),predicted_old=.5*xh/32))
            bitmap.close();page.close()
        doc.close()
    fixed=[r for r in records if r['arm']=='fixed'];old=[r for r in records if r['arm']=='old']
    assert all(max(abs(v) for v in r['centroid_dx_dy'])<.05 for r in fixed)
    assert all(max(abs(v-r['predicted_old']) for v in r['centroid_dx_dy'])<.05 for r in old)
    assert all(min(r['centroid_dx_dy'])>.05 for r in old)
    result=dict(cells_per_arm=len(fixed),maximum_fixed_offset=max(max(map(abs,r['centroid_dx_dy'])) for r in fixed),records=records,
                scope='coordinate inverse isolated from reconstruction; physical PDF rectangle outlines, 32x analytic centroid')
    Path('qualification/font04/coordinate-roundtrip.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['cells_per_arm'],result['maximum_fixed_offset'])

if __name__=='__main__':main()
