#!/usr/bin/env python3
"""Synthetic scan + normalized-OCR fixture generation for the M0 probe.

Generates pixel-hash-v1-compliant normalized OCR JSON (dogfoods SPEC Appendix A)
paired with PNG scans rasterized from system fonts. Fonts are harness-only and
never committed. Pages (all symbol granularity, provenance source_generated):

  p01_latin      clean 8, 6, a + an IDENTICAL second 8   (shape sharing, E1/E2)
  p02_wronglabel an 8 whose OCR label is 6               (VS-01 / E3)
  p03_kana       multi-component kana with dakuten       (E5 / VS-05)
  p04_ligature   fi ligature (U+FB01 -> "fi") + U+1D400  (TX-02 / E4)
  p05_colour     8 on coloured paper                     (VS-06)
  p06_degraded   blurred/noisy 8, distinct variant       (E2 distinct GID)
"""
import hashlib
import json
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures", "probe")
DPI = 300.0
PT = 72.0 / DPI

DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
IPA = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"


def pixel_hash_rgb(width: int, height: int, rgb: bytes) -> str:
    header = f"SWRASTER1\nrgb8\n{width}\n{height}\nsrgb\n-\n".encode("ascii")
    return hashlib.sha256(header + rgb).hexdigest()


def canonical_rgb(img: Image.Image) -> bytes:
    return img.convert("RGB").tobytes()


def make_page(name: str, glyphs, paper=(255, 255, 255), w=520, h=340):
    """glyphs: list of (text, font_path, size, x, y, ocr_text or None)"""
    img = Image.new("RGB", (w, h), paper)
    draw = ImageDraw.Draw(img)
    spans = []
    order = []
    for i, g in enumerate(glyphs):
        text, font_path, size, x, y = g[:5]
        ocr = g[5] if len(g) > 5 else None
        font = ImageFont.truetype(font_path, size)
        draw.text((x, y), text, font=font, fill=(20, 20, 20))
        bbox = draw.textbbox((x, y), text, font=font)
        oid = f"g{i:03d}"
        spans.append(
            {
                "id": oid,
                "text": ocr if ocr is not None else text,
                "separator_after": " ",
                "polygon": [
                    [bbox[0], bbox[1]],
                    [bbox[2], bbox[1]],
                    [bbox[2], bbox[3]],
                    [bbox[0], bbox[3]],
                ],
                "direction": "ltr",
                "role": "body",
                "language": None,
                "confidence": {"value": 99.0, "scale": "range_0_100", "calibrated": False},
                "provenance": "source_generated",
                "symbols": [
                    {
                        "id": oid + "s0",
                        "text_range_utf8": [0, len((ocr if ocr is not None else text).encode("utf-8"))],
                        "polygon": [
                            [bbox[0], bbox[1]],
                            [bbox[2], bbox[1]],
                            [bbox[2], bbox[3]],
                            [bbox[0], bbox[3]],
                        ],
                        "confidence": {"value": 99.0, "scale": "range_0_100", "calibrated": False},
                    }
                ],
            }
        )
        order.append(oid)

    page_id = name.split("_")[0]
    png_path = os.path.join(OUT, name, name + ".png")
    img.save(png_path)
    rgb = canonical_rgb(img)
    file_sha = hashlib.sha256(open(png_path, "rb").read()).hexdigest()
    pixel_sha = pixel_hash_rgb(w, h, rgb)
    doc = {
        "schema_version": "1.0",
        "page_id": page_id,
        "raster": {
            "asset_path": f"{name}/{name}.png",
            "file_sha256": file_sha,
            "pixel_sha256": pixel_sha,
            "width_px": w,
            "height_px": h,
            "canonical_format": "rgb8",
            "colour_tag": "srgb",
            "icc_sha256": None,
            "orientation_policy": "applied_once",
            "decoder_id": "m0-fixture-pillow-rasterizer",
            "dpi_x": DPI,
            "dpi_y": DPI,
        },
        "page": {
            "width_pt": w * PT,
            "height_pt": h * PT,
            "raster_to_page_pt": [PT, 0.0, 0.0, -PT, 0.0, h * PT],
        },
        "producer": {
            "name": "m0-fixture-generator",
            "version": "1.0",
            "models": [],
            "languages": [],
        },
        "granularity": "symbol",
        "reading_order_status": "supplied",
        "reading_order": order,
        "spans": spans,
        "protected_regions": [],
    }
    with open(os.path.join(OUT, name, name + ".ocr.json"), "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    print(f"{name}: {len(glyphs)} glyphs, file_sha={file_sha[:12]}..., pixel_sha={pixel_sha[:12]}...")


def main():
    os.makedirs(OUT, exist_ok=True)
    for d in ["p01_latin", "p02_wronglabel", "p03_kana", "p04_ligature", "p05_colour", "p06_degraded"]:
        os.makedirs(os.path.join(OUT, d), exist_ok=True)

    # p01: clean latin incl. two IDENTICAL 8 shapes (share a glyph: E1/E2)
    eight_bbox = None
    make_page(
        "p01_latin",
        [
            ("8", DEJAVU, 200, 20, 20),
            ("6", DEJAVU, 200, 180, 20),
            ("8", DEJAVU, 200, 340, 20),  # identical shape to first 8
            ("a", DEJAVU, 120, 20, 170),
        ],
    )

    # p02: observed 8, OCR label 6 (VS-01 / E3)
    make_page("p02_wronglabel", [("8", DEJAVU, 200, 60, 30, "6")])

    # p03: multi-component kana with dakuten (E5 / VS-05)
    make_page("p03_kana", [("ガ", IPA, 200, 60, 30)])

    # p04: fi ligature (2 codepoints) + supplementary-plane scalar (TX-02 / E4)
    make_page(
        "p04_ligature",
        [
            ("\ufb01", DEJAVU, 200, 30, 20, "fi"),
            ("\U0001d400", DEJAVU, 140, 260, 40),
        ],
    )

    # p05: 8 on coloured paper (VS-06): counters must show paper colour
    make_page("p05_colour", [("8", DEJAVU, 200, 60, 30)], paper=(216, 200, 160))

    # p06: degraded 8 variant (E2: distinct GID, same ToUnicode string)
    img = Image.new("RGB", (520, 340), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(DEJAVU, 200)
    draw.text((60, 30), "8", font=font, fill=(20, 20, 20))
    img = img.filter(ImageFilter.GaussianBlur(2.2))
    # noise: sprinkle light speckle on the ink area
    import random

    random.seed(20261013)
    px = img.load()
    for _ in range(900):
        x, y = random.randint(70, 200), random.randint(60, 230)
        v = random.randint(90, 200)
        px[x, y] = (v, v, v)
    img.save(os.path.join(OUT, "p06_degraded", "p06_degraded.png"))
    w, h = img.size
    rgb = canonical_rgb(img)
    file_sha = hashlib.sha256(open(os.path.join(OUT, "p06_degraded", "p06_degraded.png"), "rb").read()).hexdigest()
    pixel_sha = pixel_hash_rgb(w, h, rgb)
    bbox = ImageDraw.Draw(img).textbbox((60, 30), "8", font=font)
    doc = {
        "schema_version": "1.0",
        "page_id": "p06",
        "raster": {
            "asset_path": "p06_degraded/p06_degraded.png",
            "file_sha256": file_sha,
            "pixel_sha256": pixel_sha,
            "width_px": w,
            "height_px": h,
            "canonical_format": "rgb8",
            "colour_tag": "srgb",
            "icc_sha256": None,
            "orientation_policy": "applied_once",
            "decoder_id": "m0-fixture-pillow-rasterizer-degraded",
            "dpi_x": DPI,
            "dpi_y": DPI,
        },
        "page": {
            "width_pt": w * PT,
            "height_pt": h * PT,
            "raster_to_page_pt": [PT, 0.0, 0.0, -PT, 0.0, h * PT],
        },
        "producer": {"name": "m0-fixture-generator", "version": "1.0", "models": [], "languages": []},
        "granularity": "symbol",
        "reading_order_status": "supplied",
        "reading_order": ["g000"],
        "spans": [
            {
                "id": "g000",
                "text": "8",
                "separator_after": " ",
                "polygon": [
                    [bbox[0], bbox[1]],
                    [bbox[2], bbox[1]],
                    [bbox[2], bbox[3]],
                    [bbox[0], bbox[3]],
                ],
                "direction": "ltr",
                "role": "body",
                "language": None,
                "confidence": {"value": 99.0, "scale": "range_0_100", "calibrated": False},
                "provenance": "source_generated",
                "symbols": [
                    {
                        "id": "g000s0",
                        "text_range_utf8": [0, 1],
                        "polygon": [
                            [bbox[0], bbox[1]],
                            [bbox[2], bbox[1]],
                            [bbox[2], bbox[3]],
                            [bbox[0], bbox[3]],
                        ],
                        "confidence": {"value": 99.0, "scale": "range_0_100", "calibrated": False},
                    }
                ],
            }
        ],
        "protected_regions": [],
    }
    with open(os.path.join(OUT, "p06_degraded", "p06_degraded.ocr.json"), "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    print(f"p06_degraded: degraded variant, file_sha={file_sha[:12]}...")


if __name__ == "__main__":
    main()
