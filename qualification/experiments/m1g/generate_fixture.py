#!/usr/bin/env python3
"""Generate independent 12-page scan/OCR bundles and sealed synthetic oracle.

The converter bundles contain only captured RGB pages and supplied OCR boxes.
Pristine page images and source text are written under the separate oracle tree.
"""
from __future__ import annotations
import hashlib, json, random, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "qualification/experiments/m1g/fixture"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
ALT = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
KANA = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"
TEXT = "e8a0g6e,a; 8e0ag6! e8a0g6e,a; 8e0ag6?"

def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()

def make_page(dpi: int, page: int):
    scale = dpi // 300
    W, H = 1800 * scale, 900 * scale
    font_path = ALT if page in (6, 7) else FONT
    font = ImageFont.truetype(font_path, 44 * scale)
    pristine = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(pristine)
    records = []
    # Independently rendered occurrences: no page image or damaged crop is copied.
    for row in range(2):
        y = (75 + row * 178) * scale
        x = 70 * scale
        for j, ch in enumerate(TEXT):
            bb = d.textbbox((x, y), ch, font=font)
            d.text((x, y), ch, font=font, fill=15)
            pad = 5 * scale
            records.append({"id": f"p{page:02}s{len(records):04}", "text": ch,
                            "separator_after":"", "bbox": [bb[0]-pad, bb[1]-pad, bb[2]+pad, bb[3]+pad]})
            x += int(d.textlength(ch, font=font)) + 7 * scale
        records[-1]["separator_after"]="\n"
    # A small, independent horizontal kana run and line-art negative control.
    if page == 0:
        kfont=ImageFont.truetype(KANA,30*scale); x=75*scale; y=710*scale
        for ch in "かなカナかなカナ":
            bb=d.textbbox((x,y),ch,font=kfont); d.text((x,y),ch,font=kfont,fill=15)
            records.append({"id":f"p{page:02}kana{len(records):03}","text":ch,
                            "separator_after":"", "bbox":[bb[0]-4*scale,bb[1]-4*scale,bb[2]+4*scale,bb[3]+4*scale]})
            x+=int(d.textlength(ch,font=kfont))+5*scale
        records[-1]["separator_after"]="\n"
        # Genuine non-text rules/logo box, preserved as artwork in the oracle.
        d.rectangle((1370*scale,690*scale,1660*scale,815*scale),outline=90,width=3*scale)
        d.line((1390*scale,730*scale,1640*scale,730*scale),fill=90,width=2*scale)
        d.ellipse((1400*scale,748*scale,1455*scale,803*scale),outline=40,width=3*scale)
    # Approximate print-to-paper-to-capture: varying deposition, irregular
    # abrasion, paper field and scanner blur/noise, with a fresh seed per page.
    rng = np.random.default_rng(7100 + dpi * 31 + page)
    src = np.asarray(pristine, dtype=np.float32)
    low = rng.normal(0, 1, (max(2,H//90), max(2,W//90))).astype(np.float32)
    low_img = Image.fromarray(np.uint8(np.clip(128 + low*28,0,255))).resize((W,H), Image.Resampling.BICUBIC)
    deposition = (np.asarray(low_img, dtype=np.float32)-128) * 0.16
    pix = src + deposition
    # Local print dropout and paper texture are spatially varying; no rectangular glyph masks.
    paper = rng.normal(0, 1.8, (H,W)).astype(np.float32)
    pix = pix + paper
    ink = src < 245
    defect = rng.random((H,W))
    dropout = ink & (defect < (0.018 if page % 3 else 0.065))
    pix[dropout] = 225 + paper[dropout]
    faint = ink & (rng.random((H,W)) < 0.16)
    pix[faint] = np.minimum(255, pix[faint] + rng.uniform(18,65,int(faint.sum())))
    captured = Image.fromarray(np.uint8(np.clip(pix,0,255)))
    captured = captured.filter(ImageFilter.GaussianBlur(radius=0.32 * scale))
    rgb = np.asarray(captured.convert("RGB"), dtype=np.uint8)
    oracle = np.asarray(pristine.convert("RGB"), dtype=np.uint8)
    return rgb, oracle, records, FONT if font_path == FONT else ALT

def emit_dpi(dpi: int):
    bundle = OUT / f"dpi{dpi}" / "input"
    oracle_dir = OUT / f"dpi{dpi}" / "oracle"
    bundle.mkdir(parents=True, exist_ok=True); oracle_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile("/usr/share/doc/fonts-dejavu-core/copyright", OUT/"DEJAVU-LICENSE.txt")
    shutil.copyfile("/usr/share/doc/fonts-liberation/copyright", OUT/"LIBERATION-LICENSE.txt")
    shutil.copyfile("/usr/share/doc/fonts-ipafont-gothic/copyright", OUT/"IPA-LICENSE.txt")
    sources, pages = [], []
    for p in range(8):
        rgb, truth, records, font = make_page(dpi,p)
        im = Image.fromarray(rgb, "RGB"); truth_im = Image.fromarray(truth, "RGB")
        name = f"page{p:02}.png"; ocr_name=f"page{p:02}.ocr.json"
        im.save(bundle/name, optimize=False)
        truth_im.save(oracle_dir/name, optimize=False)
        w,h=im.size; page_id=f"p{p:02}"
        spans=[]
        for i,r in enumerate(records):
            x0,y0,x1,y1=r["bbox"]
            conf={"value":99.0,"scale":"range_0_100","calibrated":False}
            # One deliberate OCR-confusable control: visual e supplied as c.
            hypothesis = "c" if p == 7 and r["text"] == "e" and i == 0 else r["text"]
            spans.append({"id":r["id"],"text":hypothesis,"separator_after":r.get("separator_after",""),
              "confidence":conf,"direction":"ltr","provenance":"source_generated",
              "role":"body","language":None,
              "polygon":[[x0,y0],[x1,y0],[x1,y1],[x0,y1]],
                "symbols":[{"id":r["id"],"confidence":conf,"text_range_utf8":[0,len(hypothesis.encode())],
                "polygon":[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]}]})
        rgbbytes=rgb.tobytes(); imbytes=(bundle/name).read_bytes()
        ocr={"schema_version":"1.0","page_id":page_id,"granularity":"symbol",
          "page":{"width_pt":w*72/dpi,"height_pt":h*72/dpi,
            "raster_to_page_pt":[72/dpi,0,0,-72/dpi,0,h*72/dpi]},
          "raster":{"asset_path":name,"file_sha256":sha(imbytes),
            "pixel_sha256":sha(f"SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n".encode()+rgbbytes),
            "width_px":w,"height_px":h,"canonical_format":"rgb8","colour_tag":"srgb",
            "icc_sha256":None,"orientation_policy":"applied_once","decoder_id":"m1g-generator",
            "dpi_x":dpi,"dpi_y":dpi},
          "producer":{"name":"m1g-grounded-synthetic-ocr","version":"1","models":[],"languages":[]},
          "reading_order_status":"supplied","reading_order":[s["id"] for s in spans],
          "protected_regions":[],"spans":spans}
        ob=json.dumps(ocr,indent=2).encode(); (bundle/ocr_name).write_bytes(ob)
        sources.append({"source_id":f"src{p:03}","asset_path":name,"file_sha256":sha(imbytes),"kind":"image"})
        pages.append({"page_id":page_id,"source_id":f"src{p:03}","source_page_index":0,
                      "ocr_page_path":ocr_name,"ocr_page_sha256":sha(ob)})
        (oracle_dir/f"page{p:02}.truth.json").write_text(json.dumps({"font":font,"dpi":dpi,"page":p,"records":records},indent=2)+"\n")
    doc={"schema_version":"1.0","document_id":f"m1g-dpi{dpi}","sources":sources,"pages":pages}
    (bundle/"document.json").write_text(json.dumps(doc,indent=2)+"\n")

if __name__ == "__main__":
    emit_dpi(300); emit_dpi(600)
