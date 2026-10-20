#!/usr/bin/env python3
"""Compare emitted M1-G and uniform placement boxes to pristine ink bounds."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import trial

def summarize(rows,key):
    a=np.asarray([r[key] for r in rows],dtype=float)
    iou_key="current_iou" if key=="current_error" else "uniform_iou"
    return {"n":int(len(rows)),"mean_abs_center_dx_px":float(np.abs(a[:,0]).mean()),
            "mean_abs_center_dy_px":float(np.abs(a[:,1]).mean()),
            "mean_abs_width_error_px":float(np.abs(a[:,2]).mean()),
            "mean_abs_height_error_px":float(np.abs(a[:,3]).mean()),
            "mean_iou_of_boxes":float(np.mean([r[iou_key] for r in rows]))}

def main():
    report=json.loads((trial.BASE/"output/report.json").read_text())
    obs={};occs={}
    for pi,pr in enumerate(report["page_reports"]):
        for ob in pr["reconstruction"]["observations"]: obs[ob["symbol_id"]]=(pi,ob)
        for oc in pr["reconstruction"]["occurrences"]: occs[oc["symbol_id"]]=(pi,oc)
    font,qdf=trial.extract_embedded_font(trial.BASE/"output/canonical-experimental.pdf")
    glyph_order=font.getGlyphOrder();glyf=font["glyf"]
    matrices,gids,proto_gids=trial.extracted_occurrence_mappings(qdf,report,obs,occs)
    rows=[]; outline_hashes=set(); oracle_pages={}
    for sid,m in matrices.items():
        pi,oc=occs[sid]; _,ob=obs[sid]; gid=gids[sid]; g=glyf[glyph_order[gid]]
        dw,dh,ops=trial.form_definition(font.getGlyphSet(),glyph_order[gid],g)
        outline_hashes.add(trial.hashlib.sha256((f"{dw}:{dh}:"+ops).encode()).hexdigest())
        truth=trial.page_truth(pi); rec=next(r for r in truth["records"] if r["id"]==sid)
        if pi not in oracle_pages:
            oracle_pages[pi]=np.asarray(Image.open(trial.BASE/"oracle"/f"page{pi:02}.png").convert("L"))
        src=oracle_pages[pi]
        truth_box=np.asarray(trial.oracle_ink_box(src,rec),float)
        h=src.shape[0]; a,b,c,d,e,f=m; pt=trial.PT
        current=np.asarray([e+a*g.xMin/2048,e+a*g.xMax/2048,
                            h-(f+d*g.yMax/2048)/pt,h-(f+d*g.yMin/2048)/pt],float)
        current[[0,1]]/=pt
        current_box=np.asarray([current[0],current[2],current[1],current[3]])
        target=oc.get("replacement_bbox_px") or ob["bbox_px"]
        tx0,ty0,tx1,ty1=map(float,target);dw=max(1,float(g.xMax-g.xMin));dh=max(1,float(g.yMax-g.yMin))
        scale=min((tx1-tx0)/dw,(ty1-ty0)/dh)
        fw,fh=dw*scale,dh*scale
        uniform=np.asarray([tx0+((tx1-tx0)-fw)/2,ty1-fh,tx0+((tx1-tx0)+fw)/2,ty1],float)
        def row(box,tag):
            dx=((box[0]+box[2])-(truth_box[0]+truth_box[2]))/2
            dy=((box[1]+box[3])-(truth_box[1]+truth_box[3]))/2
            we=(box[2]-box[0])-(truth_box[2]-truth_box[0]);he=(box[3]-box[1])-(truth_box[3]-truth_box[1])
            inter=max(0,min(box[2],truth_box[2])-max(box[0],truth_box[0]))*max(0,min(box[3],truth_box[3])-max(box[1],truth_box[1]))
            union=(box[2]-box[0])*(box[3]-box[1])+(truth_box[2]-truth_box[0])*(truth_box[3]-truth_box[1])-inter
            return [dx,dy,we,he],inter/max(1,union)
        cur,ci=row(current_box,"current");uni,ui=row(uniform,"uniform")
        rows.append({"symbol_id":sid,"page":pi,"unicode":oc["text"],"gid":gid,
                     "prototype_id":oc.get("prototype_id"),"source_bbox_px":list(map(float,ob["bbox_px"])),
                     "replacement_bbox_px":list(map(float,target)),"pristine_ink_bbox_px":truth_box.tolist(),
                     "current_pdf_bbox_px":current_box.tolist(),"uniform_pdf_bbox_px":uniform.tolist(),
                     "current_error":cur,"current_iou":ci,"uniform_error":uni,"uniform_iou":ui})
    result={"matched_occurrences":len(rows),"distinct_mapped_gids":len(set(r["gid"] for r in rows)),
            "distinct_outline_shapes":len(outline_hashes),
            "current":summarize(rows,"current_error"),"uniform":summarize(rows,"uniform_error"),"occurrences":rows}
    (trial.OUT/"placement-audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="occurrences"},indent=2))
if __name__=="__main__":main()
