#!/usr/bin/env python3
"""Audit actual P0/P1 PDF text matrices against pristine glyph ink boxes."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import trial

def output_pdf(label,pdf,report_path):
    report=json.loads(report_path.read_text());obs={};occs={}
    for pi,pr in enumerate(report["page_reports"]):
        for ob in pr["reconstruction"]["observations"]:obs[ob["symbol_id"]]=(pi,ob)
        for oc in pr["reconstruction"]["occurrences"]:occs[oc["symbol_id"]]=(pi,oc)
    font,qdf=trial.extract_embedded_font(pdf);order=font.getGlyphOrder();glyf=font["glyf"]
    matrices,gids,_=trial.extracted_occurrence_mappings(qdf,report,obs,occs)
    pages={};rows=[]
    for sid,m in matrices.items():
        pi,oc=occs[sid];_,ob=obs[sid];gid=gids[sid];g=glyf[order[gid]]
        if pi not in pages:pages[pi]=np.asarray(Image.open(trial.BASE/"oracle"/f"page{pi:02}.png").convert("L"))
        src=pages[pi];rec=next(r for r in trial.page_truth(pi)["records"] if r["id"]==sid)
        truth_box=np.asarray(trial.oracle_ink_box(src,rec),float)
        h,w=src.shape;a,b,c,d,e,f=m;pt=trial.PT
        box=np.asarray([(e+a*g.xMin/2048)/pt,h-(f+d*g.yMax/2048)/pt,
                        (e+a*g.xMax/2048)/pt,h-(f+d*g.yMin/2048)/pt])
        # actual box order is x0,y0,x1,y1, as is truth_box
        center_delta=[(box[0]+box[2]-truth_box[0]-truth_box[2])/2,
                      (box[1]+box[3]-truth_box[1]-truth_box[3])/2]
        size_delta=[(box[2]-box[0])-(truth_box[2]-truth_box[0]),
                    (box[3]-box[1])-(truth_box[3]-truth_box[1])]
        inter=max(0,min(box[2],truth_box[2])-max(box[0],truth_box[0]))*max(0,min(box[3],truth_box[3])-max(box[1],truth_box[1]))
        union=(box[2]-box[0])*(box[3]-box[1])+(truth_box[2]-truth_box[0])*(truth_box[3]-truth_box[1])-inter
        tx0,ty0,tx1,ty1=map(float,oc.get("replacement_bbox_px") or ob["bbox_px"])
        rows.append({"id":sid,"page":pi,"unicode":oc["text"],"gid":gid,
                     "actual_pdf_bbox_px":box.tolist(),"pristine_ink_bbox_px":truth_box.tolist(),
                     "replacement_target_px":[tx0,ty0,tx1,ty1],
                     "center_delta_px":center_delta,"size_delta_px":size_delta,
                     "bbox_iou_to_pristine_ink":inter/max(1,union)})
    summary={"label":label,"pdf":str(pdf.relative_to(ROOT)),"mapped_occurrences":len(rows),
      "mean_abs_center_dx_px":float(np.mean([abs(r["center_delta_px"][0]) for r in rows])),
      "mean_abs_center_dy_px":float(np.mean([abs(r["center_delta_px"][1]) for r in rows])),
      "mean_abs_width_error_px":float(np.mean([abs(r["size_delta_px"][0]) for r in rows])),
      "mean_abs_height_error_px":float(np.mean([abs(r["size_delta_px"][1]) for r in rows])),
      "mean_bbox_iou_to_pristine_ink":float(np.mean([r["bbox_iou_to_pristine_ink"] for r in rows]))}
    return summary,rows

def main():
    o=trial.OUT
    p0,rows0=output_pdf("P0",trial.BASE/"output/canonical-experimental.pdf",trial.BASE/"output/report.json")
    p1,rows1=output_pdf("P1",o/"canonical-uniform-300.pdf",o/"canonical-uniform-300-report.json")
    a={r["id"]:r for r in rows0};b={r["id"]:r for r in rows1};ids=sorted(set(a)&set(b))
    p1["paired_occurrences_with_P0"]=len(ids)
    p1["mean_abs_actual_bbox_change_vs_P0_px"]={
      "center_dx":float(np.mean([abs(b[i]["center_delta_px"][0]-a[i]["center_delta_px"][0]) for i in ids])),
      "center_dy":float(np.mean([abs(b[i]["center_delta_px"][1]-a[i]["center_delta_px"][1]) for i in ids])),
      "width":float(np.mean([abs(b[i]["size_delta_px"][0]-a[i]["size_delta_px"][0]) for i in ids])),
      "height":float(np.mean([abs(b[i]["size_delta_px"][1]-a[i]["size_delta_px"][1]) for i in ids]))}
    result={"P0":p0,"P1":p1,"occurrences_P0":rows0,"occurrences_P1":rows1}
    (o/"actual-placement-check.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"P0":p0,"P1":p1},indent=2))
if __name__=="__main__":main()
