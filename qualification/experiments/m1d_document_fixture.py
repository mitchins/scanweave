#!/usr/bin/env python3
"""Generate a 12-page 300/600-DPI document-wide glyph-repair fixture."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qualification/fixtures/m1d_document"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
ALT = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
TEXT = "ea8"


def build(dpi):
    scale = dpi // 300
    width, height = 600 * scale, 240 * scale
    pages = []
    for page_no in range(12):
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        truth_image = Image.new("RGB", (width, height), "white")
        truth_draw = ImageDraw.Draw(truth_image)
        font_path = ALT if page_no in (8, 9, 10) else FONT
        font = ImageFont.truetype(font_path, 68 * scale)
        records = []
        if page_no == 0:
            chars = [(ch, 72 + i * 120 * scale, 34 * scale, True) for i, ch in enumerate(TEXT)]
        else:
            chars = [(ch, 32 * scale + i * 88 * scale, (32 + (page_no % 3) * 4) * scale, False)
                     for i, ch in enumerate("ea8ea8")]
        if page_no == 11:
            # OCR-confusable control: visual e, intentionally labeled c.
            chars.append(("e", 535 * scale, 132 * scale, False, "c"))
        for idx, item in enumerate(chars):
            ch, x, y, damaged = item[:4]
            label = item[4] if len(item) > 4 else ch
            bbox = draw.textbbox((x, y), ch, font=font)
            draw.text((x, y), ch, font=font, fill=(20, 20, 20))
            truth_draw.text((x, y), ch, font=font, fill=(20, 20, 20))
            if damaged:
                x0, y0, x1, y1 = bbox
                if ch == "e":
                    cy = (y0 + y1) // 2
                    draw.rectangle((x0 + 12 * scale, cy - 6 * scale,
                                    x1 - 8 * scale, cy + 6 * scale), fill="white")
                elif ch == "a":
                    draw.rectangle((x0 + 2 * scale, y0 + 20 * scale,
                                    x0 + 10 * scale, y0 + 40 * scale), fill="white")
                else:
                    draw.rectangle((x1 - 13 * scale, y0 + 31 * scale,
                                    x1 - 5 * scale, y0 + 40 * scale), fill="white")
            pad = 4 * scale
            records.append({"id": f"p{page_no:02}-s{idx:02}", "text": label,
                            "bbox": [bbox[0] - pad, bbox[1] - pad,
                                     bbox[2] + pad, bbox[3] + pad],
                            "source": "alternate" if font_path == ALT else "primary"})

        protected = []
        if page_no == 0:
            amount = "$123.45"
            amount_font = ImageFont.truetype(FONT, 28 * scale)
            x, y = 70 * scale, 166 * scale
            draw.text((x, y), amount, font=amount_font, fill=(20, 20, 20))
            truth_draw.text((x, y), amount, font=amount_font, fill=(20, 20, 20))
            boxes = []
            cursor = x
            for j, ch in enumerate(amount):
                bb = draw.textbbox((cursor, y), ch, font=amount_font)
                pad = 2 * scale
                records.append({"id": f"p{page_no:02}-amount{j:02}", "text": ch,
                                "bbox": [bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad],
                                "protected": True})
                boxes.append(bb)
                cursor += draw.textlength(ch, font=amount_font)
            protected = [[min(b[0] for b in boxes) - 3 * scale,
                          min(b[1] for b in boxes) - 3 * scale,
                          max(b[2] for b in boxes) + 3 * scale,
                          max(b[3] for b in boxes) + 3 * scale]]
        path = OUT / f"dpi{dpi}" / f"page{page_no:02}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, optimize=False)
        truth_path = path.with_name(path.stem + "-pristine.png")
        truth_image.save(truth_path, optimize=False)
        pages.append({"page_id": f"p{page_no:02}", "image": str(path.relative_to(ROOT)),
                      "truth_image": str(truth_path.relative_to(ROOT)),
                      "width": width, "height": height, "observations": records,
                      "protected": protected, "dpi": dpi})
    (OUT / f"document-{dpi}.json").write_text(json.dumps({
        "dpi": dpi, "font": FONT, "font_license": "Bitstream Vera/DejaVu license; see m1d_damage/DEJAVU-LICENSE.txt",
        "pages": pages,
    }, indent=2) + "\n")


if __name__ == "__main__":
    build(300)
    build(600)
