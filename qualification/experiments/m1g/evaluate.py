#!/usr/bin/env python3
"""Independent M1-G rendered-PDF measurements (oracle is never passed to CLI)."""
import hashlib, json, subprocess, sys, re
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent/"fixture"

def run(a): return subprocess.run(a,check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT).stdout
def mask(a): return a < 170
def iou(a,b):
    x,y=mask(a),mask(b); u=np.logical_or(x,y).sum()
    return float(np.logical_and(x,y).sum()/max(1,u))

def main():
    dpi=int(sys.argv[1]); d=BASE/f"dpi{dpi}"; inp=d/"input"; out=d/"output"
    pdf=out/"canonical-experimental.pdf"; report=json.loads((out/"report.json").read_text())
    manifest=json.loads((inp/"document.json").read_text())
    render=out/"poppler"; render.mkdir(exist_ok=True)
    run(["pdftoppm","-r",str(dpi),"-png",str(pdf),str(render/"page")])
    import pypdfium2 as pdfium
    doc=pdfium.PdfDocument(str(pdf))
    semantic={"expected":"","pdf_text":"","pdfium_text":""}
    semantic["pdfium_text"]="".join(doc[i].get_textpage().get_text_range() for i in range(len(doc)))
    py_dir=out/"pdfium"; py_dir.mkdir(exist_ok=True); pyimages=[]
    for i in range(len(doc)):
        pim=doc[i].render(scale=dpi/72).to_pil().convert("L")
        pim.save(py_dir/f"page-{i+1}.png"); pyimages.append(np.asarray(pim))
    doc.close()
    per_char={}; total=0; replaced=0
    for pidx,p in enumerate(manifest["pages"]):
        page_no=pidx+1
        arr=np.asarray(Image.open(render/f"page-{page_no}.png").convert("L"))
        pyarr=pyimages[pidx]
        src=np.asarray(Image.open(inp/f"page{pidx:02}.png").convert("L"))
        truth=np.asarray(Image.open(d/"oracle"/(f"page{pidx:02}.png")).convert("L"))
        rec=report["page_reports"][pidx]["reconstruction"]["occurrences"]
        repl={x["symbol_id"]:bool(x["repaired"] or x["reused"]) for x in rec}
        for r in json.loads((d/"oracle"/f"page{pidx:02}.truth.json").read_text())["records"]:
            x0,y0,x1,y1=[int(v) for v in r["bbox"]]; pad=4
            sl=(slice(max(0,y0-pad),min(arr.shape[0],y1+pad)),slice(max(0,x0-pad),min(arr.shape[1],x1+pad)))
            before=iou(src[sl],truth[sl]); after=iou(arr[sl],truth[sl]); pyafter=iou(pyarr[sl],truth[sl]); c=r["text"]
            z=per_char.setdefault(c,{"n":0,"source_iou":0.0,"output_iou":0.0,"pdfium_output_iou":0.0,"replaced":0,"replaced_source_iou":0.0,"replaced_output_iou":0.0,"replaced_pdfium_output_iou":0.0})
            z["n"]+=1; z["source_iou"]+=before; z["output_iou"]+=after;z["pdfium_output_iou"]+=pyafter
            if repl.get(r["id"],False):
                z["replaced"]+=1;z["replaced_source_iou"]+=before;z["replaced_output_iou"]+=after;z["replaced_pdfium_output_iou"]+=pyafter
            total+=1; replaced+=int(repl.get(r["id"],False))
    for z in per_char.values():
        n=z["n"]; z["source_iou"]/=n;z["output_iou"]/=n;z["pdfium_output_iou"]/=n
        if z["replaced"]:
            n=z["replaced"];z["replaced_source_iou"]/=n;z["replaced_output_iou"]/=n;z["replaced_pdfium_output_iou"]/=n
    semantic["pdf_text"]=run(["pdftotext",str(pdf),"-"])
    source_expected="".join(r["text"] for pidx,p in enumerate(manifest["pages"]) for r in
        json.loads((d/"oracle"/f"page{pidx:02}.truth.json").read_text())["records"])
    ocr_expected="".join(s["text"] for p in manifest["pages"] for s in json.loads((inp/p["ocr_page_path"]).read_text())["spans"])
    semantic["expected"]=ocr_expected
    norm=lambda s:re.sub(r"\s+","",s)
    result={"dpi":dpi,"pdf_sha256":hashlib.sha256(pdf.read_bytes()).hexdigest(),"pdf_bytes":pdf.stat().st_size,
      "pages":len(manifest["pages"]),"occurrences":total,"replaced_occurrences":replaced,
      "replacement_fraction":replaced/max(1,total),"per_character":per_char,
      "search_expected_chars":len(semantic["expected"]),"search_extracted_chars":len(semantic["pdf_text"]),
      "poppler_search_matches":norm(semantic["expected"])==norm(semantic["pdf_text"]),
      "pdfium_search_matches":norm(semantic["expected"])==norm(semantic["pdfium_text"]),
      "source_unicode_mismatches_from_supplied_ocr":sum(a!=b for a,b in zip(norm(source_expected),norm(ocr_expected))),
      "source_unicode_expected_chars":len(norm(source_expected)),
      "stage_timings":report["stage_timings"],"candidate_sizes":[{k:c[k] for k in ("name","pdf_bytes","font_bytes","raster_encoded_bytes","image_xobjects","image_references")} for c in report["candidates"]]}
    (out/"evaluation.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
