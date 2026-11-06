#!/usr/bin/env python3
"""Extract visible Type0 Tj glyph ink bounds from embedded TrueType + text matrices."""
from io import BytesIO
import pikepdf
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

def bounds(pdf_path,page_index,raster_width,raster_height):
    pdf=pikepdf.open(pdf_path); page=pdf.pages[page_index]; media=list(map(float,page.MediaBox)); ph=media[3]-media[1]; sx=raster_width/(media[2]-media[0]); sy=raster_height/ph
    fonts={}
    for name,f in page.Resources.Font.items():
        try:
            desc=f.DescendantFonts[0]; raw=desc.FontDescriptor.FontFile2.read_bytes(); font=TTFont(BytesIO(raw)); gs=font.getGlyphSet(); mapping=desc.CIDToGIDMap.read_bytes(); order=font.getGlyphOrder(); fonts[str(name)]=(font,gs,mapping,order)
        except (AttributeError, KeyError, IndexError): continue
    active=None; mat=None; mode=0; result=[]
    for ins in pikepdf.parse_content_stream(page):
        op=str(ins.operator); args=ins.operands
        if op=='Tf': active=str(args[0])
        elif op=='Tr': mode=int(args[0])
        elif op=='Tm': mat=list(map(float,args))
        elif op=='Tj' and mode not in (3,7) and active in fonts and mat:
            raw=bytes(args[0]); font,gs,mapping,order=fonts[active]; upem=font['head'].unitsPerEm
            if len(raw)!=2: continue
            cid=int.from_bytes(raw,'big'); off=cid*2
            if off+2>len(mapping): continue
            gid=int.from_bytes(mapping[off:off+2],'big')
            if gid>=len(order): continue
            pen=BoundsPen(gs); gs[order[gid]].draw(pen)
            if pen.bounds is None: continue
            x0,y0,x1,y1=pen.bounds; a,b,c,d,e,f=mat
            coords=[(a*x/upem+c*y/upem+e,b*x/upem+d*y/upem+f) for x in (x0,x1) for y in (y0,y1)]
            xs=[v[0]*sx for v in coords]; ys=[(ph-v[1])*sy for v in coords]
            result.append({'cid':cid,'gid':gid,'matrix':mat,'font_bbox':list(pen.bounds),'outline_bbox_px':[min(xs),min(ys),max(xs),max(ys)]})
    return result
