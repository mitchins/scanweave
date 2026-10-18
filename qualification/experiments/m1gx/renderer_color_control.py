#!/usr/bin/env python3
"""Compare DeviceGray vs DeviceRGB serialization of the same equal-channel scan."""
import json,re,subprocess,hashlib,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]; BASE=ROOT/"qualification/experiments/m1g/fixture/dpi300"; OUT=ROOT/"qualification/experiments/m1gx/300"
def run(a): return subprocess.run(a,check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT).stdout
def main():
    result={}; renders=OUT/"renders-rgb-control"; renders.mkdir(exist_ok=True)
    import pypdfium2 as pdfium
    for arm,pdf in [("DeviceGray",OUT/"O0-source-searchable.pdf"),("DeviceRGB",OUT/"O0-DeviceRGB-searchable.pdf")]:
        popdir=renders/arm;popdir.mkdir(exist_ok=True)
        run(["pdftoppm","-r","300","-png",str(pdf),str(popdir/"p")])
        doc=pdfium.PdfDocument(str(pdf)); py=[]
        for i in range(len(doc)):
            im=doc[i].render(scale=300/72).to_pil().convert("L")
            if im.size!=(1800,900): im=im.resize((1800,900),Image.Resampling.LANCZOS)
            py.append(np.asarray(im))
        text="".join(doc[i].get_textpage().get_text_range() for i in range(len(doc))); doc.close()
        scores={"poppler_iou":[],"pdfium_iou":[],"poppler_mae_to_input":[],"pdfium_mae_to_input":[]}
        for p in range(8):
            src=np.asarray(Image.open(BASE/"input"/f"page{p:02}.png").convert("L")); truth=np.asarray(Image.open(BASE/"oracle"/f"page{p:02}.png").convert("L"))
            pop=np.asarray(Image.open(popdir/f"p-{p+1}.png").convert("L"));
            if pop.shape!=(900,1800): pop=np.asarray(Image.fromarray(pop).resize((1800,900),Image.Resampling.LANCZOS))
            recs=json.loads((BASE/"oracle"/f"page{p:02}.truth.json").read_text())["records"]
            for rec in recs:
                if not rec["text"].strip(): continue
                pad=4 if ord(rec["text"][0])>127 else 5;x0,y0,x1,y1=map(int,rec["bbox"]);sl=np.s_[y0+pad:y1-pad,x0+pad:x1-pad]
                truthmask=truth[sl]<170
                for key,img in (("poppler",pop),("pdfium",py[p])):
                    m=img[sl]<170; scores[key+"_iou"].append(float((m&truthmask).sum()/max(1,(m|truthmask).sum())))
                    scores[key+"_mae_to_input"].append(float(np.abs(img[sl].astype(np.int16)-src[sl].astype(np.int16)).mean()))
        result[arm]={"pdf_bytes":pdf.stat().st_size,"pdf_sha256":hashlib.sha256(pdf.read_bytes()).hexdigest(),"mean":{k:float(np.mean(v)) for k,v in scores.items()},"poppler_search_chars":len(re.sub(r"\s+","",run(["pdftotext",str(pdf),"-"]))),"pdfium_search_chars":len(re.sub(r"\s+","",text))}
    (OUT/"renderer-color-control.json").write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result,indent=2))
if __name__=="__main__": main()
