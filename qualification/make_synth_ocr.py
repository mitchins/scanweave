#!/usr/bin/env python3
"""Ground-truth (source-side) OCR variants for M1-A behavior fixtures.

The converter sees only these synthetic spans (source-side ground truth from the
drawing), never the original font. The real-Tesseract hOCR variants remain for
the integration path.
"""
import json
import os

from PIL import Image, ImageDraw, ImageFont

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "probe")
DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
IPA = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"


def draw_word(draw, x, y, font, text, squeeze=0, fill=(20, 20, 20)):
    boxes = []
    for ch in text:
        bb = draw.textbbox((x, y), ch, font=font)
        boxes.append(bb)
        draw.text((x, y), ch, font=font, fill=fill)
        x += (bb[2] - bb[0]) - squeeze
    return boxes


def phrase_boxes(img, font, text, x, y, squeeze=0):
    d = ImageDraw.Draw(img)
    boxes = draw_word(d, x, y, font, text, squeeze=squeeze)
    return boxes


def emit(name, png_name, entries):
    """entries: list of (text, per-char boxes)"""
    spans = []
    for i, (text, boxes) in enumerate(entries):
        sid = f"g{i:03d}"
        # span polygon: union of char boxes
        x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
        x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
        syms = []
        off = 0
        for k, ch in enumerate(text):
            n = len(ch.encode("utf-8"))
            b = boxes[k]
            syms.append({
                "id": f"{sid}s{k:02d}",
                "text_range_utf8": [off, off + n],
                "polygon": [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]],
                "confidence": {"value": None, "scale": "unknown", "calibrated": False},
            })
            off += n
        spans.append({
            "id": sid, "text": text, "separator_after": " ",
            "polygon": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
            "direction": "ltr", "role": "body", "language": None,
            "confidence": {"value": None, "scale": "unknown", "calibrated": False},
            "provenance": "source_generated",
            "symbols": syms,
        })
    return spans


def write(name, png_name, spans):
    import hashlib
    png = os.path.join(FIX, name, png_name)
    rgb = Image.open(png).convert("RGB").tobytes()
    w, h = Image.open(png).size
    header = f"SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n".encode()
    doc = {
        "schema_version": "1.0",
        "page_id": name,
        "raster": {
            "asset_path": f"{name}/{png_name}",
            "file_sha256": hashlib.sha256(open(png, "rb").read()).hexdigest(),
            "pixel_sha256": hashlib.sha256(header + rgb).hexdigest(),
            "width_px": w, "height_px": h,
            "canonical_format": "rgb8", "colour_tag": "srgb", "icc_sha256": None,
            "orientation_policy": "applied_once",
            "decoder_id": "m1a-synth-ground-truth",
            "dpi_x": 300.0, "dpi_y": 300.0,
        },
        "page": {"width_pt": w * 72.0 / 300.0, "height_pt": h * 72.0 / 300.0,
                 "raster_to_page_pt": [72.0 / 300.0, 0.0, 0.0, -72.0 / 300.0, 0.0, h * 72.0 / 300.0]},
        "producer": {"name": "m1a-synth", "version": "1.0", "models": [], "languages": []},
        "granularity": "symbol", "reading_order_status": "supplied",
        "reading_order": [s["id"] for s in spans],
        "spans": spans,
        "protected_regions": [],
    }
    out = os.path.join(FIX, name, f"{name}.synth.json")
    json.dump(doc, open(out, "w"), indent=1)
    print(f"{name}: {len(spans)} ground-truth spans")


def main():
    # p11_touching: same drawing geometry as the fixture generator
    f = ImageFont.truetype(DEJAVU, 64)
    img = Image.new("RGB", (640, 300), (250, 249, 246))
    e1 = []
    e1.append(("mini", phrase_boxes(img, f, "mini", 40, 30, squeeze=6)))
    e1.append(("glass", phrase_boxes(img, f, "glass", 40, 110, squeeze=5)))
    e1.append(("68", phrase_boxes(img, f, "68", 40, 190, squeeze=12)))
    e1.append(("shift", phrase_boxes(img, f, "shift", 300, 30, squeeze=4)))
    e1.append(("fi", phrase_boxes(img, f, "fi", 300, 190, squeeze=2)))
    write("p11_touching", "p11_touching.png", emit("p11_touching", None, e1))

    # p12_disconnected: same geometry as the fixture generator
    img = Image.new("RGB", (640, 300), (252, 251, 248))
    fj = ImageFont.truetype(IPA, 72)
    e2 = []
    e2.append(("ij", phrase_boxes(img, fj, "ij", 40, 30, squeeze=0)))
    e2.append(("!", phrase_boxes(img, fj, "!", 40, 130, squeeze=2)))
    e2.append(("ガパ", phrase_boxes(img, fj, "ガパ", 40, 210)))
    write("p12_disconnected", "p12_disconnected.png", emit("p12_disconnected", None, e2))


if __name__ == "__main__":
    main()
