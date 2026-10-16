#!/usr/bin/env python3
"""Create a deterministic donor-reconstruction page from installed licensed fonts."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "qualification/fixtures/m1d_damage"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
ALT = "/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf"
S = 4
W, H = 760, 470
im = Image.new("RGB", (W*S, H*S), "white")
records = []

def add(text, x, y, font_path=FONT, damage=None, phase=0):
    f = ImageFont.truetype(font_path, 48*S)
    # Small phase changes in the high-resolution sampling grid create distinct
    # antialiasing while keeping the source typeface and nominal size fixed.
    px, py = int(phase % S), int((phase * 3) % S)
    draw = ImageDraw.Draw(im)
    bx = draw.textbbox((x*S+px, y*S+py), text, font=f)
    draw.text((x*S+px, y*S+py), text, font=f, fill=(22, 22, 22))
    x0, y0, x1, y1 = [v//S for v in bx]
    if damage == "crossbar":
        # Clear the central crossbar of e while keeping its outer silhouette.
        cy = (y0 + y1) // 2 + 1
        draw.rectangle((x0*S + 7*S, cy*S-5*S, x1*S-7*S, cy*S+5*S), fill="white")
    elif damage == "notch":
        draw.rectangle(((x0+15)*S, (y0+13)*S, (x0+20)*S, (y0+21)*S), fill="white")
    records.append({"id": f"s{len(records):02}", "text": text,
                    "bbox": [x0-2, y0-2, x1+2, y1+2],
                    "damage": damage, "font": Path(font_path).name})

# Ten donor observations. The first appears after the two targets so tracing
# order cannot accidentally select a damaged observation as the prototype.
positions = [(x, y) for y in (26, 102) for x in (40, 145, 250, 355, 460)]
add("e", 40, 178, damage="crossbar", phase=1)
add("e", 145, 178, damage="notch", phase=2)
for k, (x, y) in enumerate(positions): add("e", x, y, phase=k)
# Identity controls and a same-label, visibly different typeface control.
for k, (ch, x, y) in enumerate([
    ("6", 600, 178), ("6", 640, 178), ("6", 680, 178),
    ("8", 600, 254), ("8", 640, 254), ("8", 680, 254),
    ("0", 600, 320), ("0", 640, 320), ("0", 680, 320),
    ("O", 600, 386), ("O", 640, 386), ("O", 680, 386),
]):
    add(ch, x, y, phase=k % S)
# A competing coherent e cohort from a second typeface tests style separation.
for k, x in enumerate((40, 145, 250)):
    add("e", x, 254, font_path=ALT, phase=k)

# Evaluator-only pristine render: overlay the intact known-font outline at the
# damaged occurrence, outside the input fixture consumed by ScanWeave.
truth = im.copy()
ImageDraw.Draw(truth).text((40*S + 1, 178*S + 3), "e",
    font=ImageFont.truetype(FONT, 48*S), fill=(22, 22, 22))
truth = truth.resize((W, H), Image.Resampling.LANCZOS)
im = im.resize((W, H), Image.Resampling.LANCZOS)
# Quiet low-amplitude scanner softness, then restore high contrast dark ink.
im = im.filter(ImageFilter.GaussianBlur(0.12))
records.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))
im.save(OUT / "source.png", optimize=False)
truth_dir = ROOT / "qualification/evaluator"
truth_dir.mkdir(parents=True, exist_ok=True)
truth.save(truth_dir / "m1d_damage_ground_truth.png", optimize=False)
(OUT / "positions.json").write_text(json.dumps({"width": W, "height": H,
    "font": FONT, "font_license": "Bitstream Vera / DejaVu Fonts license; see /usr/share/doc/fonts-dejavu-core/copyright",
    "observations": records}, indent=2) + "\n")
print(f"wrote {OUT/'source.png'} with {len(records)} observations")
