#!/usr/bin/env python3
"""Audit actual raster ink replacement in the GX ScanWeave output."""
import json, subprocess, tempfile
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"qualification/experiments/m1g/fixture/dpi300"
OUT=ROOT/"qualification/experiments/m1gx/300"

def main():
    pdf=OUT/"canonical-uniform-300.pdf"
    report=json.loads((OUT/"canonical-uniform-300-report.json").read_text())
    obs_by_id={}; occs=[]
    for pi,pr in enumerate(report["page_reports"]):
        for ob in pr["reconstruction"]["observations"]:
            obs_by_id[ob["symbol_id"]]=(pi,ob)
        for oc in pr["reconstruction"]["occurrences"]:
            if oc.get("repaired") or oc.get("reused"):
                found=obs_by_id.get(oc["symbol_id"])
                if found: occs.append((oc["symbol_id"],found[0],found[1]))
    accepted=occs
    result={"pdf_bytes":pdf.stat().st_size,"accepted_occurrences":len(accepted),
            "pages":[],"pdfimages_list":subprocess.run(
                ["pdfimages","-list",str(pdf)],check=True,text=True,
                stdout=subprocess.PIPE).stdout}
    totals={k:0 for k in ("source_dark_lt145","output_dark_lt145","removed_dark_pixels",
                           "added_dark_pixels","changed_pixels","changed_inside_accepted_boxes",
                           "changed_outside_accepted_boxes","source_dark_inside_accepted_boxes",
                           "output_dark_inside_accepted_boxes","source_dark_still_dark_inside_accepted_boxes",
                           "source_dark_still_dark_outside_accepted_boxes","new_dark_inside_accepted_boxes")}
    with tempfile.TemporaryDirectory(prefix="m1gx-background-") as td:
        prefix=str(Path(td)/"page")
        subprocess.run(["pdfimages","-png",str(pdf),prefix],check=True,
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        decoded=sorted(Path(td).glob("page-*.png"))
        if len(decoded)!=8: raise RuntimeError(f"expected 8 page images, got {len(decoded)}")
        for pi,encoded in enumerate(decoded):
            src=np.asarray(Image.open(BASE/"input"/f"page{pi:02}.png").convert("L"))
            out=np.asarray(Image.open(encoded).convert("L"))
            if out.shape!=src.shape: raise RuntimeError(f"page {pi}: decoded raster shape mismatch")
            accepted_mask=np.zeros(src.shape,dtype=bool)
            for sid,p,ob in accepted:
                if p!=pi: continue
                x0,y0,x1,y1=map(lambda v:int(round(v)),ob["bbox_px"])
                accepted_mask[max(0,y0):min(src.shape[0],y1),max(0,x0):min(src.shape[1],x1)]=True
            source_dark=src<145; output_dark=out<145
            removed=source_dark & ~output_dark; added=~source_dark & output_dark
            changed=src!=out
            entry={"page":pi,"width":int(out.shape[1]),"height":int(out.shape[0]),
                   "decoded_sha256":__import__("hashlib").sha256(out.tobytes()).hexdigest(),
                   "source_dark_lt145":int(source_dark.sum()),"output_dark_lt145":int(output_dark.sum()),
                   "removed_dark_pixels":int(removed.sum()),"added_dark_pixels":int(added.sum()),
                   "changed_pixels":int(changed.sum()),
                   "changed_inside_accepted_boxes":int((changed&accepted_mask).sum()),
                   "changed_outside_accepted_boxes":int((changed&~accepted_mask).sum()),
                   "source_dark_inside_accepted_boxes":int((source_dark&accepted_mask).sum()),
                   "output_dark_inside_accepted_boxes":int((output_dark&accepted_mask).sum()),
                   "source_dark_still_dark_inside_accepted_boxes":int((source_dark&output_dark&accepted_mask).sum()),
                   "source_dark_still_dark_outside_accepted_boxes":int((source_dark&output_dark&~accepted_mask).sum()),
                   "new_dark_inside_accepted_boxes":int((added&accepted_mask).sum())}
            result["pages"].append(entry)
            for k in totals: totals[k]+=entry[k]
    result["totals"]=totals
    (OUT/"background-audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"pdf_bytes":result["pdf_bytes"],"accepted_occurrences":result["accepted_occurrences"],"totals":totals},indent=2))

if __name__=="__main__": main()
