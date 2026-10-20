#!/usr/bin/env python3
"""Independent Poppler/PDFium glyph and PDF measurements for M1-GX."""
import hashlib,json,re,subprocess,sys,os
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"qualification/experiments/m1g/fixture/dpi300"
OUT=ROOT/"qualification/experiments/m1gx/300"
ARMS=["O0-source-searchable","O1-oracle-outline-placement","O2-reconstructed-oracle-placement","O3-oracle-identity-current-placement","O3-reconstructed-current-placement","O3-uniform-placement","C0-source-under-vector","C2-inferred-clean-background","O4-current-m1g","O5-pipeline-uniform-300"]
THRESHOLDS=(64,96,128,160,192,224)
RENDER_ROOT=OUT/("renders-"+os.environ.get("GX_RENDER_SET","pristine-exact"))
def run(a): return subprocess.run(a,check=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT).stdout
def mask(a): return a<170
def iou(a,b):
 x,y=mask(a),mask(b); return float((x&y).sum()/max(1,(x|y).sum()))
def main():
 import pypdfium2 as pdfium
 outdata={}; source_scores={}; source_images=[]
 for arm in ARMS:
  pdf=(OUT/"canonical-uniform-300.pdf") if arm=="O5-pipeline-uniform-300" else OUT/f"{arm}.pdf"; render=RENDER_ROOT/arm; render.mkdir(parents=True,exist_ok=True)
  # Render every measured PDF afresh.  Never trust a cache based on filenames:
  # that can silently pair a changed PDF with stale pixels.
  run(["pdftoppm","-r","300","-png",str(pdf),str(render/"p")])
  pop=[]
  for i in range(8):
   path=render/f"p-{i+1}.png"
   pop.append(np.asarray(Image.open(path).convert("L")))
  doc=pdfium.PdfDocument(str(pdf)); py=[]; pdfium_text=""; pyrender=render/"pdfium"; pyrender.mkdir(exist_ok=True)
  for i in range(len(doc)):
   page=doc[i]; pdfium_text+=page.get_textpage().get_text_range(); cache=pyrender/f"p-{i+1}.png"
   page.render(scale=300/72).to_pil().convert("L").save(cache)
   rendered=Image.open(cache).convert("L")
   if rendered.size!=(1800,900):
    # PDFium rounds the 432x216pt page to 1801x901. Crop the extra right/bottom
    # edge at the shared top-left origin; resampling changes glyph geometry.
    rendered=rendered.crop((0,0,1800,900))
   py.append(np.asarray(rendered))
  doc.close(); pop_text=run(["pdftotext",str(pdf),"-"])
  result={"bytes":pdf.stat().st_size,"sha256":hashlib.sha256(pdf.read_bytes()).hexdigest(),"pages":len(pop),"per_character":{},"poppler_search_chars":len(re.sub(r"\s+","",pop_text)),"pdfium_search_chars":len(re.sub(r"\s+","",pdfium_text)),"whitespace_occurrences_excluded":0,"render_size_px":[[int(x.shape[1]),int(x.shape[0])] for x in pop]}
  total=[]; occurrences=[]; strata={"healthy":[],"moderate":[],"heavy":[]}; thresholds={k:{th:[] for th in THRESHOLDS} for k in ("poppler","pdfium")}; maes={"poppler":[],"pdfium":[],"source":[]}
  for p in range(8):
   src=np.asarray(Image.open(BASE/"input"/f"page{p:02}.png").convert("L")); truth=np.asarray(Image.open(BASE/"oracle"/f"page{p:02}.png").convert("L"))
   oracle=json.loads((BASE/"oracle"/f"page{p:02}.truth.json").read_text())
   for rec in oracle["records"]:
    if rec["text"].isspace(): result["whitespace_occurrences_excluded"]+=1; continue
    pad=4 if ord(rec["text"][0])>127 else 5
    x0,y0,x1,y1=map(int,rec["bbox"]); sl=(slice(max(0,y0+pad),min(src.shape[0],y1-pad)),slice(max(0,x0+pad),min(src.shape[1],x1-pad)))
    src_crop=src[sl]; truth_crop=truth[sl]; pop_crop=pop[p][sl]; py_crop=py[p][sl]
    s= iou(src_crop,truth_crop); a=iou(pop_crop,truth_crop); b=iou(py_crop,truth_crop); ch=rec["text"]
    maes["source"].append(float(np.mean(np.abs(src_crop.astype(np.int16)-truth_crop.astype(np.int16)))))
    maes["poppler"].append(float(np.mean(np.abs(pop_crop.astype(np.int16)-truth_crop.astype(np.int16)))))
    maes["pdfium"].append(float(np.mean(np.abs(py_crop.astype(np.int16)-truth_crop.astype(np.int16)))))
    occurrences.append({"id":rec["id"],"page":p,"unicode":ch,
      "raw_scan_iou":s,"poppler_iou":a,"pdfium_iou":b,
      "raw_scan_mae":maes["source"][-1],"poppler_mae":maes["poppler"][-1],"pdfium_mae":maes["pdfium"][-1]})
    for th in THRESHOLDS:
     tm=truth_crop<th
     for renderer,img in (("poppler",pop_crop),("pdfium",py_crop)):
      om=img<th; thresholds[renderer][th].append(float((om&tm).sum()/max(1,(om|tm).sum())))
    z=result["per_character"].setdefault(ch,{"n":0,"source_iou":0.0,"poppler_iou":0.0,"pdfium_iou":0.0})
    z["n"]+=1; z["source_iou"]+=s; z["poppler_iou"]+=a; z["pdfium_iou"]+=b
    total.append((ch,s,a,b,p,sl))
    bucket="healthy" if s>=0.94 else "moderate" if s>=0.85 else "heavy"
    strata[bucket].append((s,a,b))
  for z in result["per_character"].values():
   for k in ("source_iou","poppler_iou","pdfium_iou"): z[k]/=z["n"]
  result["mean_source_iou"]=float(np.mean([x[1] for x in total])); result["mean_poppler_iou"]=float(np.mean([x[2] for x in total])); result["mean_pdfium_iou"]=float(np.mean([x[3] for x in total]))
  result["mean_crop_mae_to_pristine"]={k:float(np.mean(v)) for k,v in maes.items()}
  result["threshold_iou_sweep"]={renderer:{str(th):float(np.mean(vals)) for th,vals in values.items()} for renderer,values in thresholds.items()}
  result["damage_strata"]={k:{"n":len(v),"source_iou":float(np.mean([x[0] for x in v])) if v else None,"poppler_iou":float(np.mean([x[1] for x in v])) if v else None,"pdfium_iou":float(np.mean([x[2] for x in v])) if v else None} for k,v in strata.items()}
  norm=lambda s:re.sub(r"\s+","",s)
  expected="".join(s["text"] for p in range(8) for s in json.loads((BASE/"input"/f"page{p:02}.ocr.json").read_text())["spans"])
  result["poppler_search_matches_ocr"]=norm(pop_text)==norm(expected)
  result["pdfium_search_matches_ocr"]=norm(pdfium_text)==norm(expected)
  truth_expected="".join(r["text"]+r.get("separator_after","") for p in range(8) for r in json.loads((BASE/"oracle"/f"page{p:02}.truth.json").read_text())["records"])
  result["poppler_search_matches_source_truth_order"]=norm(pop_text)==norm(truth_expected)
  result["pdfium_search_matches_source_truth_order"]=norm(pdfium_text)==norm(truth_expected)
  result["occurrences"]=occurrences
  outdata[arm]=result
  # retain source score only once for damage stratification
  if arm==ARMS[0]: source_scores={i:(x[0],x[1]) for i,x in enumerate(total)}
  if arm=="O4-current-m1g": source_images=pop
  print(arm,round(result["mean_poppler_iou"],4),round(result["mean_pdfium_iou"],4),result["bytes"],result["poppler_search_matches_ocr"],result["pdfium_search_matches_ocr"])
 # Damage severity uses raw-source IoU per truth occurrence, independent of output.
 for arm,result in outdata.items():
  arr=[]
  for z in result["per_character"].values(): pass
  source_by_id={o["id"]:o for o in outdata[ARMS[0]]["occurrences"]}
  paired=[]
  for o in result["occurrences"]:
   b=source_by_id[o["id"]]
   o["poppler_delta_vs_rendered_raster"]=o["poppler_iou"]-b["poppler_iou"]
   o["pdfium_delta_vs_rendered_raster"]=o["pdfium_iou"]-b["pdfium_iou"]
   o["poppler_delta_vs_raw_scan"]=o["poppler_iou"]-o["raw_scan_iou"]
   o["pdfium_delta_vs_raw_scan"]=o["pdfium_iou"]-o["raw_scan_iou"]
   paired.append(o)
  result["paired_vs_rendered_raster"]={renderer:{
   "mean_iou_delta":float(np.mean([o[renderer+"_delta_vs_rendered_raster"] for o in paired])),
   "improved_occurrences":sum(o[renderer+"_delta_vs_rendered_raster"]>1e-9 for o in paired),
   "regressed_occurrences":sum(o[renderer+"_delta_vs_rendered_raster"]<-1e-9 for o in paired),
   "best_repair":max(paired,key=lambda o:o[renderer+"_delta_vs_rendered_raster"]),
   "worst_regression":min(paired,key=lambda o:o[renderer+"_delta_vs_rendered_raster"])}
   for renderer in ("poppler","pdfium")}
 # contact sheet at natural crop scale and 8x zoom.
 sample=[]
 for p in (0,1,7):
  t=json.loads((BASE/"oracle"/f"page{p:02}.truth.json").read_text())
  for wanted in ("e","0","8","a","g"):
   rec=next((r for r in t["records"] if r["text"]==wanted),None)
   if rec: sample.append((p,rec))
 tilew,tileh=260,90; sheet=Image.new("RGB",(tilew*len(ARMS),tileh*len(sample)),"white"); d=ImageDraw.Draw(sheet)
 for row,(p,r) in enumerate(sample):
  x0,y0,x1,y1=map(int,r["bbox"]); box=(max(0,x0-4),max(0,y0-4),x1+4,y1+4)
  for col,arm in enumerate(ARMS):
   path=RENDER_ROOT/arm/f"p-{p+1}.png"
   im=Image.open(path).convert("L").crop(box)
   im=im.resize((min(100,im.width*3),min(70,im.height*3)))
   sheet.paste(im.convert("RGB"),(col*tilew,row*tileh+16)); d.text((col*tilew,row*tileh),f"{arm} {r['text']} p{p}",fill="black")
 sheet.save(OUT/"oracle-ladder-crops.png")
 (OUT/"gx_metrics.json").write_text(json.dumps({"arms":outdata,"source_damage_bins":"see report; stratified by occurrence source IoU","pdfs":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob("*.pdf"))}},indent=2)+"\n")

if __name__=="__main__": main()
