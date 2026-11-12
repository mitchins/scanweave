from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw

root = Path("qualification/font03/local")
out = root / "final-review"
out.mkdir(exist_ok=True)
index = []
for split in ["validation", "test"]:
    ref = root / "affine-refinement"
    accepted = {
        r["target"]
        for r in json.loads((ref / f"{split}-final-decisions.json").read_text())[
            "decisions"
        ]
        if r["accepted"]
    }
    rows = {
        r["id"]: r
        for r in json.loads((root / f"{split}-sources.json").read_text())["records"]
    }
    evaluated = json.loads((ref / f"{split}-evaluated.json").read_text())["records"]
    lookup = {(r["target"], r["renderer"], r["arm"]): r for r in evaluated}
    maps = np.load(ref / f"{split}-native-coverages.npz")
    pages = {}
    for target in sorted(accepted):
        row = rows[target]
        r = lookup[target, "pdfium", "C"]
        x, y, xx, yy = r["bounds"]
        px, py, qx, qy = row["public_bbox"]
        pristine = Image.new("L", (xx - x, yy - y), 255)
        pristine.paste(
            Image.open(
                Path("qualification/font01/local/corpus-font01-v1")
                / split
                / "oracle"
                / f"{target}-pristine.png"
            ).convert("L"),
            (px - x, py - y),
        )
        page = row["page"]
        if page not in pages:
            pages[page] = Image.open(
                Path("qualification/font01/local/corpus-font01-v1")
                / split
                / f"page-{page}.png"
            ).convert("L")
        source = pages[page].crop((x, y, xx, yy))
        number = len(index)
        flip = number % 2 == 0
        index.append(
            dict(
                case=number,
                split=split,
                target=target,
                character=row["character"],
                U="canonical" if flip else "current",
                V="current" if flip else "canonical",
                flag=any(
                    lookup[target, e, "C"]["material"] for e in ["pdfium", "poppler"]
                ),
            )
        )
        for engine in ["pdfium", "poppler"]:
            selected = [("Source", source), ("Pristine", pristine)]
            labels = [("U", "C" if flip else "A"), ("V", "A" if flip else "C")]
            for name, arm in labels:
                selected.append(
                    (
                        name,
                        Image.fromarray(
                            np.uint8(
                                np.clip(
                                    255 * (1 - maps[f"{engine}-{arm}-{target}"]), 0, 255
                                )
                            )
                        ),
                    )
                )
            scale = 4
            w, h = (xx - x) * scale, (yy - y) * scale
            sheet = Image.new("RGB", (4 * (w + 12), h + 36), "white")
            draw = ImageDraw.Draw(sheet)
            for j, (name, im) in enumerate(selected):
                sheet.paste(
                    im.resize((w, h), Image.Resampling.NEAREST), (j * (w + 12), 36)
                )
                draw.text((j * (w + 12), 18), name, fill="black")
            draw.text(
                (0, 0),
                f'Case {number} {row["character"]} {engine} source dpi{row["dpi"]}',
                fill="black",
            )
            sheet.save(out / f"case-{number}-{engine}.png")
for engine in ["pdfium", "poppler"]:
    for start in range(0, len(index), 7):
        files = [
            Image.open(out / f"case-{i}-{engine}.png").convert("RGB")
            for i in range(start, min(start + 7, len(index)))
        ]
        sheet = Image.new(
            "RGB", (max(i.width for i in files), sum(i.height for i in files)), "white"
        )
        y = 0
        for image in files:
            sheet.paste(image, (0, y))
            y += image.height
        sheet.save(out / f"atlas-{engine}-{start//7}.png")
(out / "blind-key.json").write_text(json.dumps(index, indent=2))
print("all accepted", len(index), "cases;7atlaspages perengine")
