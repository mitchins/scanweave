#!/usr/bin/env python3
"""Compare current ScanWeave with the frozen Adobe XI outputs on matched scans."""
import hashlib, json, re, subprocess
from pathlib import Path
import numpy as np
from PIL import Image
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / "qualification/competitors/adobe_xi"
OUT = ROOT / "qualification/clearscan_product"

def run(*cmd):
    return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(s): return re.sub(r"\s+", "", s)
def iou(a,b):
    aa,bb=a<170,b<170; u=np.logical_or(aa,bb).sum()
    return float(np.logical_and(aa,bb).sum()/max(1,u))

def main():
    result={"schema":"clearscan-frozen-adobe-paired-v1","runs":[]}
    for dpi in (300,600):
        base=COMP/"inputs"/f"dpi{dpi}"
        manifest=json.loads((base/"document.json").read_text())
        oracle=json.loads((COMP/"oracle"/f"dpi{dpi}"/"manifest.json").read_text())
        arms={"adobe_xi":COMP/"results"/f"dpi{dpi}"/"adobe-clearscan-run1.pdf",
              "scanweave_current":OUT/f"adobe_{dpi}"/"clearscan.pdf"}
        run_dir=OUT/f"adobe_{dpi}"/"comparison"; run_dir.mkdir(parents=True,exist_ok=True)
        sources=[]; truths=[]; truth_records=[]; expected=[]
        for i,page in enumerate(manifest["pages"]):
            src=base/manifest["sources"][next(j for j,s in enumerate(manifest["sources"]) if s["source_id"]==page["source_id"])]["asset_path"]
            sources.append(np.asarray(Image.open(src).convert("L")))
            truth_doc=json.loads((COMP/"oracle"/f"dpi{dpi}"/f"page{i+1}-truth.json").read_text())
            truths.append(np.asarray(Image.open(COMP/"oracle"/f"dpi{dpi}"/f"page{i+1}-pristine.png").convert("L")))
            truth_records.append(truth_doc["glyphs"])
            ocr=json.loads((base/page["ocr_page_path"]).read_text())
            expected.extend(s["text"] for s in ocr["spans"])
        expected_text=norm("".join(expected))
        for name,pdf in arms.items():
            arm_out=run_dir/name; pop_dir=arm_out/"poppler"; pop_dir.mkdir(parents=True,exist_ok=True)
            run("pdftoppm","-r",str(dpi),"-png",str(pdf),str(pop_dir/"page"))
            pop=[np.asarray(Image.open(pop_dir/f"page-{i+1}.png").convert("L"))[:sources[i].shape[0],:sources[i].shape[1]] for i in range(len(sources))]
            doc=pdfium.PdfDocument(str(pdf)); page_count=len(doc); py=[]; pytext=""
            for i in range(page_count):
                page=doc[i]; im=page.render(scale=dpi/72).to_pil().convert("L")
                arr=np.asarray(im)[:sources[i].shape[0],:sources[i].shape[1]]; py.append(arr)
                im.save(arm_out/f"pdfium-page-{i+1}.png")
                pytext+=page.get_textpage().get_text_range()
            doc.close()
            # Raw content order matches this fixture's source OCR reading order;
            # Poppler's default geometric layout can reorder adjacent runs.
            poptext=run("pdftotext","-raw",str(pdf),"-")
            fonts=run("pdffonts",str(pdf)); images=run("pdfimages","-list",str(pdf)); info=run("pdfinfo",str(pdf))
            glyph_scores={"source":[],"poppler":[],"pdfium":[]}
            for pi, records in enumerate(truth_records):
                for g in records:
                    x0,y0,x1,y1=map(int,g["bbox"]); sl=(slice(y0,y1),slice(x0,x1))
                    glyph_scores["source"].append(iou(sources[pi][sl],truths[pi][sl]))
                    glyph_scores["poppler"].append(iou(pop[pi][sl],truths[pi][sl]))
                    glyph_scores["pdfium"].append(iou(py[pi][sl],truths[pi][sl]))
            fields={}
            for line in info.splitlines():
                if ":" in line:
                    k,v=line.split(":",1); fields[k.strip()]=v.strip()
            run_result={"dpi":dpi,"arm":name,"pdf":str(pdf.relative_to(ROOT)),"sha256":sha(pdf),"bytes":pdf.stat().st_size,
                "pages":page_count,"pdfinfo":fields,
                "font_rows":[x for x in fonts.splitlines()[2:] if x.strip() and not x.startswith("---")],
                "image_list_rows":len([x for x in images.splitlines()[2:] if x.strip() and not x.startswith("---")]),
                "image_list":images,
                "text":{"expected_nonspace_chars":len(expected_text),"poppler_nonspace_chars":len(norm(poptext)),"pdfium_nonspace_chars":len(norm(pytext)),
                        "poppler_matches_known_ocr":norm(poptext)==expected_text,"pdfium_matches_known_ocr":norm(pytext)==expected_text},
                "mean_glyph_iou_vs_pristine":{k:float(np.mean(v)) for k,v in glyph_scores.items()},
                "mean_page_mae_vs_pristine":{"poppler":float(np.mean([np.abs(pop[i].astype(np.int16)-truths[i]).mean() for i in range(3)])),
                                               "pdfium":float(np.mean([np.abs(py[i].astype(np.int16)-truths[i]).mean() for i in range(3)]))}}
            result["runs"].append(run_result)
            print(json.dumps({k:v for k,v in run_result.items() if k!="image_list"},indent=2))
    (OUT/"frozen_adobe_comparison.json").write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__": main()
