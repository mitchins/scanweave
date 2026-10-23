"""Independent physical PDF coordinates -> sampled frame -> bbox -> SFNT -> PDF.

The source is an analytic rectangle in known PDF points. Its native pixel-area
coverage and global pixel-centre sampler are independently established. The
production source_frame chooses an INTEGER crop. A frozen vector rectangle in
that crop isolates coordinate transport from contour-fitting error. The actual
embedded TrueType program, anchor/span mapping and analytic PDF render are tested.
"""
import json
from pathlib import Path
import numpy as np
import pikepdf
import pypdfium2 as pdfium
from scipy import ndimage
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from qualification.font04.planner import source_frame,crop_request,frame_bbox
from qualification.font04.causal import glyph_matrix
from qualification.font04.metrics import operands
from qualification.font04.pdf_helpers import font_resource


def coverage(rect):
    x,y,xx,yy=rect;edges=np.arange(96)
    return np.clip(np.minimum(edges[:,None]+1,yy)-np.maximum(edges[:,None],y),0,1)*np.clip(np.minimum(edges[None,:]+1,xx)-np.maximum(edges[None,:],x),0,1)

def font(path,cases):
    builder=FontBuilder(2048,isTTF=True);order=['.notdef']+[f'g{i}' for i in range(len(cases))];builder.setupGlyphOrder(order);glyphs={};widths={};pen=TTGlyphPen(None);glyphs['.notdef']=pen.glyph();widths['.notdef']=(0,0)
    for i,c in enumerate(cases):
        w,h=c['size'];x,y,xx,yy=c['local_rectangle'];pen=TTGlyphPen(None)
        points=[(x,h-y),(xx,h-y),(xx,h-yy),(x,h-yy)]
        pen.moveTo(tuple(round(v*256) for v in points[0]))
        for point in points[1:]:pen.lineTo(tuple(round(v*256) for v in point))
        pen.closePath();glyphs[f'g{i}']=pen.glyph();widths[f'g{i}']=(round(w*256+256),min(point[0] for point in glyphs[f'g{i}'].coordinates))
    builder.setupGlyf(glyphs);builder.setupHorizontalMetrics(widths);builder.setupHorizontalHeader(ascent=10000,descent=-1000);builder.setupCharacterMap({ord('e'):'g0'});builder.setupNameTable(dict(familyName='FONT04Physical',styleName='Regular',uniqueFontIdentifier='FONT04Physical',fullName='FONT04Physical',psName='FONT04Physical'));builder.setupOS2(sTypoAscender=10000,sTypoDescender=-1000,usWinAscent=10000,usWinDescent=1000);builder.setupPost();builder.setupMaxp();builder.font['head'].created=2082844800;builder.font['head'].modified=2082844800;builder.font.recalcTimestamp=False;builder.save(path)

def main():
    root=Path('qualification/font04/local/coordinate-roundtrip');root.mkdir(parents=True,exist_ok=True);records=[];sampler_errors=[]
    for dpi in (200,300,600):
        cases=[]
        for xheight in (8.,16.,26.,48.):
            for ox in (0.,.25,.5,.75):
                for oy in (0.,.25,.5,.75):
                    physical=np.array([(24+ox)*72/dpi,(24+oy)*72/dpi,(24+ox+.625*xheight)*72/dpi,(24+oy+xheight)*72/dpi]);rect=physical*dpi/72;cov=coverage(rect);gray=np.round((1-cov)*255);owned=cov>.5;x,y=np.floor(rect[:2]).astype(int);xx,yy=np.ceil(rect[2:]).astype(int)
                    source=dict(bbox=[int(x),int(y),int(xx),int(yy)],ocr_bbox=rect.tolist(),width=int(xx-x),height=int(yy-y),mask=owned[y:yy,x:xx].ravel().tolist(),halo=gray[y-2:yy+2,x-2:xx+2].ravel().tolist())
                    row=dict(source=source,paper=[255,255,255],line_units=[dict(text='e',bbox=rect.tolist())]);field,f=source_frame(row)
                    expected=dict(cx=(rect[0]+rect[2])/2,baseline=rect[3],xheight=xheight,scale=32/xheight)
                    assert all(abs(f[k]-v)<1e-10 for k,v in expected.items())
                    # Independent world pixel-centre convention: native index n
                    # is physical n+.5. No crop-local +1.5 inverse is reused.
                    distance=ndimage.distance_transform_edt(~owned);foreign=(255-gray>60)&~owned;fd=ndimage.distance_transform_edt(~foreign) if foreign.any() else np.full(gray.shape,100.);evidence=(255-gray)/255*((distance<=1.5)&(distance<fd));cy,cx=np.mgrid[:64,:64]
                    independent=ndimage.map_coordinates(evidence,[expected['baseline']+(cy-48)/expected['scale']-.5,expected['cx']+(cx-32)/expected['scale']-.5],order=1,mode='constant',prefilter=False)
                    sampler_error=float(np.abs(independent-field).max());assert sampler_error<1e-10;sampler_errors.append(sampler_error)
                    request,origin=crop_request('physical','e',field);w,h=request['width'],request['height']
                    # Vector edges come from the known physical outline, not a
                    # reverse application of frame_bbox or a fitted centroid.
                    true=np.array([32+(rect[0]-expected['cx'])*expected['scale'],48+(rect[1]-expected['baseline'])*expected['scale'],32+(rect[2]-expected['cx'])*expected['scale'],48+(rect[3]-expected['baseline'])*expected['scale']])
                    local=true-np.array([origin[0]-.5,origin[1]-.5,origin[0]-.5,origin[1]-.5]);cases.append(dict(xheight=xheight,offset=[ox,oy],physical=physical,origin=origin,size=[w,h],frame=f,local_rectangle=local,sampler_error=sampler_error))
        fontpath=root/f'{dpi}.ttf';font(fontpath,cases);pdf=pikepdf.Pdf.new();truth=pikepdf.Pdf.new();outlines=[dict(gid=i+1,character='e') for i in range(len(cases))];resource=font_resource(pdf,fontpath,outlines);resource.DescendantFonts[0].FontDescriptor.FontBBox=[-1024,-1024,16384,16384]
        for i,c in enumerate(cases):
            x,y,xx,yy=c['physical'];page=truth.add_blank_page(page_size=(96*72/dpi,96*72/dpi));page.Contents=truth.make_stream(f'0 g {x:.12f} {96*72/dpi-yy:.12f} {xx-x:.12f} {yy-y:.12f} re f\n'.encode())
            fixed=np.array(frame_bbox(c['frame'],c['origin'],c['size']));old=fixed+.5/c['frame']['scale'];w,h=c['size'];o=dict(span=[w*256,h*256],anchor=[0,0,w*256,h*256])
            for arm,bbox in [('fixed',fixed),('old',old)]:
                page=pdf.add_blank_page(page_size=(96*72/dpi,96*72/dpi));page.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F=resource));m=glyph_matrix(dict(dpi=dpi,page_height=96*72/dpi),o,bbox);page.Contents=pdf.make_stream(('BT 0 g /F 1 Tf '+' '.join(map(str,operands(m)))+f' Tm <{i+1:04x}> Tj ET\n').encode())
        path=root/f'{dpi}.pdf';pdf.save(path,deterministic_id=True);truth.save(root/f'{dpi}-physical-source.pdf',deterministic_id=True);doc=pdfium.PdfDocument(path)
        for i,c in enumerate(cases):
            for j,arm in enumerate(['fixed','old']):
                page=doc[i*2+j];bitmap=page.render(scale=dpi*32/72,grayscale=True);ink=1-np.asarray(bitmap.to_pil().convert('L'),float)/255;cy,cx=ndimage.center_of_mass(ink);observed=np.array([cx+.5,cy+.5])/32;physical=c['physical'];expected=np.array([(physical[0]+physical[2])/2,(physical[1]+physical[3])/2])*dpi/72;delta=observed-expected
                records.append(dict(dpi=dpi,xheight=c['xheight'],offset=c['offset'],arm=arm,centroid_dx_dy=delta.tolist(),predicted_old=.5*c['xheight']/32,crop_origin=c['origin'],sampler_error=c['sampler_error']));bitmap.close();page.close()
        doc.close()
    fixed=[r for r in records if r['arm']=='fixed'];old=[r for r in records if r['arm']=='old'];assert all(max(map(abs,r['centroid_dx_dy']))<.05 for r in fixed);assert all(max(abs(v-r['predicted_old']) for v in r['centroid_dx_dy'])<.05 for r in old);assert all(min(r['centroid_dx_dy'])>.05 for r in old)
    result=dict(cells_per_arm=len(fixed),maximum_fixed_offset=max(max(map(abs,r['centroid_dx_dy'])) for r in fixed),maximum_independent_sampler_error=max(sampler_errors),records=records,scope='Independent physical PDF rectangles, native area coverage, production source_frame and integer crop, embedded SFNT outline, production anchor/span glyph matrix, 32x analytic centroid; tracing error isolated.')
    Path('qualification/font04/coordinate-roundtrip.json').write_text(json.dumps(result,indent=2)+'\n');print(result['cells_per_arm'],result['maximum_fixed_offset'],result['maximum_independent_sampler_error'])

if __name__=='__main__':main()
