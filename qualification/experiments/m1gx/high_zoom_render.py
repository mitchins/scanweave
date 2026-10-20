#!/usr/bin/env python3
"""Render selected GX glyph crops at 2400 DPI with PDFium (800% at 300 DPI)."""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import pypdfium2 as pdfium

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"qualification/experiments/m1g/fixture/dpi300"
OUT=ROOT/"qualification/experiments/m1gx/300"
ARMS=["O0-source-searchable","O1-oracle-outline-placement","O2-reconstructed-oracle-placement",
      "O3-oracle-identity-current-placement","O4-current-m1g","O5-pipeline-uniform-300"]
PDFS={a:(OUT/"canonical-uniform-300.pdf" if a.startswith("O5") else OUT/f"{a}.pdf") for a in ARMS}

def main():
    m=json.loads((OUT/"gx_metrics.json").read_text())["arms"]["O4-current-m1g"]["occurrences"]
    best=max(m,key=lambda x:x["poppler_delta_vs_rendered_raster"])
    worst=min(m,key=lambda x:x["poppler_delta_vs_rendered_raster"])
    selections=[best,worst]
    truth_items=[]
    for score in selections:
        sid=score["id"];p=int(sid[1:3]);truth=json.loads((BASE/"oracle"/f"page{p:02}.truth.json").read_text())
        rec=next(x for x in truth["records"] if x["id"]==sid);pad=3
        x0,y0,x1,y1=map(int,rec["bbox"]);x0=max(0,x0-pad);y0=max(0,y0-pad);x1+=pad;y1+=pad
        crop_pt=72/300
        w,h=1800,900
        crop=(x0*crop_pt,(h-y1)*crop_pt,(w-x1)*crop_pt,y0*crop_pt)
        columns=[]
        for name,path in (("raw scan",BASE/"input"/f"page{p:02}.png"),("pristine",BASE/"oracle"/f"page{p:02}.png")):
            im=Image.open(path).convert("L").crop((x0,y0,x1,y1))
            columns.append((name,im.resize((im.width*8,im.height*8),Image.Resampling.NEAREST)))
        for arm in ARMS:
            doc=pdfium.PdfDocument(str(PDFS[arm]));page=doc[p]
            im=page.render(scale=2400/72,crop=crop,grayscale=True).to_pil().convert("L")
            doc.close();columns.append((arm,im))
        truth_items.append((sid,rec["text"],score,columns))
    tilew=max(im.width for _,_,_,cols in truth_items for _,im in cols)
    tileh=max(im.height for _,_,_,cols in truth_items for _,im in cols)
    h=sum(30+tileh+4 for _ in truth_items);w=tilew*8
    canvas=Image.new("RGB",(w,h),"white");draw=ImageDraw.Draw(canvas);y=0
    for sid,ch,score,cols in truth_items:
        draw.text((0,y),f"{sid} {ch!r}: M1-G vs O0 ΔIoU Poppler {score['poppler_delta_vs_rendered_raster']:+.3f}, PDFium {score['pdfium_delta_vs_rendered_raster']:+.3f}",fill="black");y+=22
        for j,(name,im) in enumerate(cols):
            xx=j*tilew;draw.text((xx,y),name,fill="black");canvas.paste(im.convert("RGB"),(xx,y+15))
        y+=tileh+30
    path=OUT/"examples-best-and-worst-2400dpi.pdfium.png";canvas.save(path)
    print(json.dumps({"file":str(path),"best":best["id"],"worst":worst["id"],"size_px":canvas.size},indent=2))

if __name__=="__main__":main()
