#!/usr/bin/env python3
"""Compare candidate PDFs under Poppler and PDFium at physical DPI."""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
import pypdfium2 as pdfium

def pil_gray(path): return np.asarray(Image.open(path).convert("RGB"))
def render_pdfium(path, dpi, outdir):
    doc=pdfium.PdfDocument(str(path)); pages=[]
    for i,page in enumerate(doc):
        image=page.render(scale=dpi/72).to_pil().convert("RGB")
        output=outdir/f"pdfium-{i+1:02}.png"
        image.save(output); pages.append(output)
        image.close()
    doc.close(); return pages
def render_poppler(path,dpi,outdir):
    prefix=str(outdir/"poppler")
    subprocess.run(["pdftoppm","-png","-r",str(dpi),str(path),prefix],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    files=sorted(outdir.glob("poppler-*.png"))
    return files
def cmp_files(path_a,path_b):
    with Image.open(path_a) as image_a, Image.open(path_b) as image_b:
        a=np.asarray(image_a.convert("RGB")); b=np.asarray(image_b.convert("RGB"))
    if a.shape != b.shape: return {"shape_a":a.shape,"shape_b":b.shape,"same_shape":False}
    delta=np.abs(a.astype(np.int16)-b.astype(np.int16))
    return {"same_shape":True,"pixel_identical":bool(np.array_equal(a,b)),"changed_pixels":int(np.any(delta!=0,axis=2).sum()),"mae":float(delta.mean()),"max_delta":int(delta.max())}

def main():
    dpi=int(sys.argv[1]); baseline=Path(sys.argv[2]); candidate=Path(sys.argv[3]); root=Path(sys.argv[4]); root.mkdir(parents=True,exist_ok=True)
    results={"dpi":dpi,"baseline":str(baseline),"candidate":str(candidate),"renderers":{}}
    for name,fn in (("poppler",render_poppler),("pdfium",render_pdfium)):
        a_dir=root/name/"baseline"; b_dir=root/name/"candidate"; a_dir.mkdir(parents=True,exist_ok=True); b_dir.mkdir(parents=True,exist_ok=True)
        a=fn(baseline,dpi,a_dir); b=fn(candidate,dpi,b_dir)
        if len(a) != len(b):
            raise ValueError(f"page count mismatch: {len(a)} vs {len(b)}")
        results["renderers"][name]=[cmp_files(x,y) for x,y in zip(a,b)]
    print(json.dumps(results,indent=2))

if __name__=="__main__": main()
