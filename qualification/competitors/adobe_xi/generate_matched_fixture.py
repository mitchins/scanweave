#!/usr/bin/env python3
"""Build a deterministic 3-page Adobe XI / ScanWeave matched synthetic pilot.

Only inputs/ is supplied to either converter. oracle/ is evaluator-only.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter
from lossless_pdf import write_image_only_pdf

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "qualification/competitors/adobe_xi"
PAGE_PT = (612, 792)
FONTS = {
    "serif": "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "serif_bold": "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "sans": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "sans_bold": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "dejavu_serif": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
}
TEXT = [
    [
        ("CASH ACCOUNT STATEMENT", "serif_bold", 17, 72, 70),
        ("The quick brown fox jumps over the lazy dog.", "serif", 12, 72, 115),
        ("Repeated letters: e a g 8 0 O 6 8; punctuation: , . : ; / -", "serif", 12, 72, 145),
        ("ACCOUNT 0186-2408     TOTAL $1,208.50     TAX 8.25%", "sans_bold", 11, 72, 195),
        ("Mixed styles preserve family distinctions and readable spacing.", "sans", 11, 72, 245),
        ("Liberation Serif / Liberation Sans", "dejavu_serif", 11, 72, 285),
    ],
    [
        ("PRINT AND TONER VARIATION", "serif_bold", 17, 72, 70),
        ("eeeee aaaaa ggggg 88888 00000 OOOOO", "serif", 13, 72, 120),
        ("The same document repeats useful letter and number forms.", "serif", 12, 72, 155),
        ("INVOICE 0186-2408     BALANCE $1,208.50", "sans_bold", 11, 72, 205),
        ("Light rules and a small table remain non-text content.", "sans", 11, 72, 245),
    ],
    [
        ("AGED PAPER / REPEATED IMPRESSIONS", "serif_bold", 17, 72, 70),
        ("e e e e e e e e e e   a a a a a   8 8 8 8 8", "serif", 14, 72, 125),
        ("Different impressions preserve complementary stroke evidence.", "serif", 12, 72, 165),
        ("ROUTE 608     ACCOUNT 0186-2408     $1,208.50", "sans_bold", 11, 72, 215),
        ("Distinct families: serif, sans, bold and regular.", "sans", 11, 72, 255),
    ],
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def page_font(path: str, pt: float, dpi: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, max(1, round(pt * dpi / 72)))


def ptpx(value: float, dpi: int) -> int:
    return round(value * dpi / 72)


def correlated_noise(rng: np.random.Generator, size: tuple[int, int], scale: float,
                     amplitude: float) -> np.ndarray:
    small = rng.normal(0, 1, (max(2, size[0] // 48), max(2, size[1] // 48)))
    field = np.asarray(Image.fromarray(np.uint8(np.clip((small + 3) * 32, 0, 255)))
                       .resize((size[1], size[0]), Image.Resampling.BICUBIC), dtype=np.float32)
    field = (field - field.mean()) / max(field.std(), 1.0)
    # A second, finer correlated component models paper fibres and ink grain.
    fine = gaussian_filter(rng.normal(0, 1, size), sigma=max(0.6, scale))
    fine = (fine - fine.mean()) / max(fine.std(), 1e-6)
    return amplitude * (0.65 * field + 0.35 * fine)


def make_page(page_index: int, dpi: int):
    scale = dpi / 72
    w, h = round(PAGE_PT[0] * scale), round(PAGE_PT[1] * scale)
    rng = np.random.default_rng(0xA11CE + page_index * 101 + dpi)
    pristine = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(pristine)
    words = []
    glyphs = []
    for line_no, (line, font_key, pt, x_pt, y_pt) in enumerate(TEXT[page_index]):
        font_path = FONTS[font_key]
        font = page_font(font_path, pt, dpi)
        x = ptpx(x_pt, dpi)
        y = ptpx(y_pt, dpi)
        # Draw word runs separately so OCR word boxes and symbol boxes share
        # exactly the same layout coordinates as the pristine page.
        cursor = x
        for token_i, token in enumerate(line.split(" ")):
            if not token:
                cursor += round(font.getlength(" "))
                continue
            token_bbox = draw.textbbox((cursor, y), token, font=font)
            draw.text((cursor, y), token, font=font, fill=12)
            wid = f"p{page_index+1:02}-l{line_no:02}-w{token_i:02}"
            chars = []
            char_cursor = cursor
            for ci, ch in enumerate(token):
                cb = draw.textbbox((char_cursor, y), ch, font=font)
                # Advances from the prefix retain pair kerning for adjacent letters.
                next_x = cursor + round(font.getlength(token[:ci+1]))
                cb = draw.textbbox((char_cursor, y), ch, font=font)
                bx0, by0, bx1, by1 = cb
                chars.append({"text": ch, "bbox": [bx0, by0, bx1, by1]})
                glyphs.append({"page": page_index + 1, "word": wid, "text": ch,
                               "bbox": [bx0, by0, bx1, by1], "font_key": font_key,
                               "font_path": font_path, "pt": pt, "line": line_no,
                               "char_index": ci})
                char_cursor = next_x
            words.append({"id": wid, "text": token, "bbox": list(token_bbox),
                          "glyphs": chars, "font_key": font_key})
            cursor += round(font.getlength(token)) + round(font.getlength(" "))

    # Small vector-like artwork in the pristine source; it must not be learned
    # as typography or lost when text is replaced.
    art = ImageDraw.Draw(pristine)
    art.rectangle((ptpx(72, dpi), ptpx(310, dpi), ptpx(540, dpi), ptpx(360, dpi)), outline=70, width=max(1, ptpx(.6, dpi)))
    art.line((ptpx(72, dpi), ptpx(334, dpi), ptpx(540, dpi), ptpx(334, dpi)), fill=95, width=max(1, ptpx(.45, dpi)))
    art.ellipse((ptpx(500, dpi), ptpx(72, dpi), ptpx(520, dpi), ptpx(92, dpi)), outline=25, width=max(1, ptpx(1.2, dpi)))

    # Forward image formation: print density + thermal banding first.
    base = np.asarray(pristine, dtype=np.float32)
    damage = np.zeros((h, w), dtype=np.uint8)
    if page_index == 1:
        field = correlated_noise(rng, (h, w), scale=max(1, dpi / 450), amplitude=8.0)
        band = 6.0 * np.sin(np.linspace(0, 15 * math.pi, h))[:, None]
        ink_strength = np.clip((255 - base) / 243, 0, 1)
        base = 255 - ink_strength * (243 - field - band)
        # Sparse spatially-correlated ink starvation; no box-shaped erasures.
        starvation = np.maximum(0, correlated_noise(rng, (h, w), scale=1.3, amplitude=0.35) - 0.48)
        base = base + starvation * ink_strength * 120
    elif page_index == 2:
        # Aged paper: low-frequency yellow/brown shift is represented in luma,
        # with correlated fibre texture, local fading, and uneven illumination.
        paper = correlated_noise(rng, (h, w), scale=2.3, amplitude=8.5)
        yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        xx = np.linspace(0, 1, w, dtype=np.float32)[None, :]
        illumination = 10 * yy + 6 * np.sin(xx * math.pi)
        base = base + paper + illumination
        ink_strength = np.clip((255 - np.asarray(pristine, dtype=np.float32)) / 243, 0, 1)
        fade = np.clip(0.72 + 0.18 * np.sin(xx * 2 * math.pi) + 0.07 * yy, 0.48, 0.98)
        base = np.where(ink_strength > 0, 255 - ink_strength * 243 * fade, base)
        # Irregular abrasion within selected glyphs. A low-frequency correlated
        # field produces separated worn fragments instead of rectangular cuts.
        targets = [g for g in glyphs if g["page"] == 3 and g["text"] in "ea8"]
        target_queues = {ch: 0 for ch in "ea8"}
        for g in targets:
            ch = g["text"]
            idx = target_queues[ch]
            target_queues[ch] += 1
            if idx % 3 == 2:  # leave donors intact across the page
                continue
            gx0, gy0, gx1, gy1 = g["bbox"]
            gw, gh = max(1, gx1-gx0), max(1, gy1-gy0)
            patch_rng = np.random.default_rng(0xD00D + idx * 29 + ord(ch))
            low = patch_rng.normal(0, 1, (max(3, gh//7), max(3, gw//7)))
            wear_image = Image.fromarray(np.uint8(np.clip((low + 3) * 36, 0, 255)))
            wear = np.asarray(
                wear_image.resize((gw, gh), Image.Resampling.BICUBIC), dtype=np.float32
            ) / 255
            threshold = 0.66 + 0.04 * (idx % 2)
            mask = wear > threshold
            crop = base[gy0:gy1, gx0:gx1]
            ink = np.asarray(pristine, dtype=np.float32)[gy0:gy1, gx0:gx1] < 220
            crop[mask & ink] = np.maximum(crop[mask & ink], 228)
            damage[gy0:gy1, gx0:gx1][mask & ink] = 1

    # Capture: mild optical blur and sensor noise. Dots are sampled at the
    # actual target resolution above; no post-hoc resize substitutes for DPI.
    base = np.clip(base, 0, 255)
    im = Image.fromarray(base.astype(np.uint8), mode="L")
    sigma = 0.22 if dpi == 300 else 0.32
    im = im.filter(ImageFilter.GaussianBlur(radius=sigma))
    sensor = rng.normal(0, 1.1 if page_index else 0.35, (h, w))
    scan = np.clip(np.asarray(im, dtype=np.float32) + sensor, 0, 255).astype(np.uint8)
    return pristine, Image.fromarray(scan, mode="L"), words, glyphs, damage


def make_ocr(page_id: str, path: Path, dpi: int, words: list[dict], w: int, h: int):
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    pixel_header = f"SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n".encode("ascii")
    pixel_hash = hashlib.sha256(pixel_header + rgb.tobytes()).hexdigest()
    spans = []
    reading_order = []
    for i, word in enumerate(words):
        x0,y0,x1,y1=word["bbox"]
        sid=word["id"]
        symbols=[]; pos=0
        for j,g in enumerate(word["glyphs"]):
            a,b,c,d=g["bbox"]
            symbols.append({"id":f"{sid}s{j:03}","text_range_utf8":[pos,pos+len(g["text"].encode())],"polygon":[[a,b],[c,b],[c,d],[a,d]],"confidence":{"value":100.0,"scale":"range_0_100","calibrated":False}})
            pos += len(g["text"].encode())
        spans.append({"id":sid,"text":word["text"],"separator_after":" ","polygon":[[x0,y0],[x1,y0],[x1,y1],[x0,y1]],"direction":"ltr","role":"body","language":"en","confidence":{"value":100.0,"scale":"range_0_100","calibrated":False},"provenance":"ocr","symbols":symbols})
        reading_order.append(sid)
    if spans: spans[-1]["separator_after"]="\n"
    return {"schema_version":"1.0","page_id":page_id,"raster":{"asset_path":path.name,"file_sha256":sha(path),"pixel_sha256":pixel_hash,"width_px":w,"height_px":h,"canonical_format":"rgb8","colour_tag":"srgb","icc_sha256":None,"orientation_policy":"applied_once","decoder_id":"adobe_xi_m1e_synthetic_generator","dpi_x":float(dpi),"dpi_y":float(dpi)},"page":{"width_pt":float(PAGE_PT[0]),"height_pt":float(PAGE_PT[1]),"raster_to_page_pt":[72.0/dpi,0.0,0.0,-72.0/dpi,0.0,float(PAGE_PT[1])]},"producer":{"name":"synthetic_oracle","version":"1","models":[],"languages":["en"]},"granularity":"symbol","reading_order_status":"inferred","reading_order":reading_order,"spans":spans,"protected_regions":[]}


def build(dpi: int):
    in_dir=OUT/"inputs"/f"dpi{dpi}"; oracle_dir=OUT/"oracle"/f"dpi{dpi}"
    in_dir.mkdir(parents=True,exist_ok=True); oracle_dir.mkdir(parents=True,exist_ok=True)
    pages=[]; all_glyphs=[]; all_words=[]
    for i in range(3):
        pristine,scan,words,glyphs,damage=make_page(i,dpi)
        page_id=f"page{i+1}"
        image_path=in_dir/f"{page_id}.png"; pristine_path=oracle_dir/f"{page_id}-pristine.png"
        scan.save(image_path,optimize=True); pristine.save(pristine_path,optimize=True)
        ocr=make_ocr(page_id,image_path,dpi,words,*scan.size)
        ocr_path=in_dir/f"{page_id}.ocr.json"; ocr_path.write_text(json.dumps(ocr,indent=2)+"\n")
        original_refs={"page":i+1,"pristine_image":str(pristine_path.relative_to(OUT)),"pristine_sha256":sha(pristine_path),"scan_image":str(image_path.relative_to(OUT)),"scan_sha256":sha(image_path),"ocr_sha256":sha(ocr_path),"glyphs":glyphs,"words":words,"damage_mask_sha256":hashlib.sha256(damage.tobytes()).hexdigest(),"damage_mask_pixels":int(damage.sum())}
        (oracle_dir/f"{page_id}-truth.json").write_text(json.dumps(original_refs,indent=2)+"\n")
        pages.append({"page_id":page_id,"image":str(image_path.relative_to(OUT)),"ocr":str(ocr_path.relative_to(OUT)),"width_px":scan.width,"height_px":scan.height,"page_width_pt":PAGE_PT[0],"page_height_pt":PAGE_PT[1]})
        all_glyphs.extend(glyphs); all_words.extend(words)
    # Bundle follows ScanWeave's existing content-addressed document format.
    sources=[]; bundle_pages=[]
    for i,p in enumerate(pages):
        image_path=OUT/p["image"]; ocr_path=OUT/p["ocr"]
        sources.append({"source_id":f"src{i:03}","asset_path":Path(p["image"]).name,"file_sha256":sha(image_path),"kind":"image"})
        bundle_pages.append({"page_id":p["page_id"],"source_id":f"src{i:03}","source_page_index":0,"ocr_page_path":Path(p["ocr"]).name,"ocr_page_sha256":sha(ocr_path)})
    bundle={"schema_version":"1.0","document_id":f"adobe-xi-m1e-{dpi}","sources":sources,"pages":bundle_pages}
    (in_dir/"document.json").write_text(json.dumps(bundle,indent=2)+"\n")
    # Lossless image-only PDF for Adobe; PNG image samples are embedded directly.
    pdf_path=in_dir/"image-only.pdf"
    write_image_only_pdf([OUT/p["image"] for p in pages], pdf_path, dpi, PAGE_PT)
    settings={"dpi":dpi,"page_points":PAGE_PT,"page_pixels":[pages[0]["width_px"],pages[0]["height_px"]],"pages":pages,"image_only_pdf":str(pdf_path.relative_to(OUT)),"image_only_pdf_sha256":sha(pdf_path),"image_only_pdf_bytes":pdf_path.stat().st_size,"fonts":{k:{"path":v,"sha256":sha(Path(v))} for k,v in FONTS.items()},"font_licenses":{"Liberation":"SIL Open Font License; /usr/share/doc/fonts-liberation/copyright","DejaVu":"Bitstream Vera/DejaVu license; /usr/share/doc/fonts-dejavu-core/copyright"},"regimes":["page1 clean antialiased scan","page2 ink-density variation, correlated toner starvation/banding, capture blur/noise","page3 paper-aging gradient/fibres/fading plus irregular correlated impression abrasion; intact donors remain"]}
    (oracle_dir/"manifest.json").write_text(json.dumps({"source_fonts":settings["fonts"],"license":settings["font_licenses"],"page_truth":pages,"glyphs":all_glyphs,"settings":settings},indent=2)+"\n")
    print(json.dumps(settings,indent=2))

if __name__=="__main__":
    for resolution in (300,600): build(resolution)
