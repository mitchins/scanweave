from pathlib import Path
import json
import subprocess
import tempfile
import hashlib
import numpy as np
import pikepdf
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from qualification.tools_env import qpdf_bin, qpdf_env, ots_bin

root = Path("qualification/font03/local")
paths = [
    Path("qualification/font02/local/financial-required.pdf"),
    root / "financial-preunion.pdf",
]
result = {}
renders = {}
for engine in ["pdfium", "poppler"]:
    records = []
    texts = []
    for number, path in enumerate(paths):
        with tempfile.TemporaryDirectory() as t:
            if engine == "poppler":
                subprocess.run(
                    ["pdftoppm", "-r", "300", "-png", str(path), t + "/page"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            d = pdfium.PdfDocument(path)
            text = []
            for pi in range(len(d)):
                p = d[pi]
                if engine == "pdfium":
                    b = p.render(scale=300 / 72)
                    a = np.asarray(b.to_pil().convert("RGB")).copy()
                    b.close()
                    tp = p.get_textpage()
                    text.append(tp.get_text_range())
                    tp.close()
                else:
                    with Image.open(f"{t}/page-{pi+1:02d}.png") as image:
                        a = np.asarray(image.convert("RGB")).copy()
                if number == 0:
                    if pi == 0:
                        renders[engine, "baseline"] = a.copy()
                    np.save(root / f"verify-{engine}-{pi}.npy", a)
                else:
                    if pi == 0:
                        renders[engine, "candidate"] = a.copy()
                    baseline = np.load(root / f"verify-{engine}-{pi}.npy")
                    records.append(
                        dict(
                            page=pi + 1,
                            equal=bool(np.array_equal(a, baseline)),
                            changed_pixels=int(np.any(a != baseline, axis=2).sum()),
                            baseline_sha256=hashlib.sha256(
                                baseline.tobytes()
                            ).hexdigest(),
                            candidate_sha256=hashlib.sha256(a.tobytes()).hexdigest(),
                        )
                    )
                p.close()
            d.close()
            if engine == "poppler":
                data = subprocess.check_output(["pdftotext", "-layout", str(path), "-"])
                texts.append(data)
            else:
                texts.append("\n".join(text).encode())
    result[engine] = dict(
        pages=records,
        extraction_identical=texts[0] == texts[1],
        extraction_hashes=[hashlib.sha256(t).hexdigest() for t in texts],
    )
path = paths[1]
check = subprocess.run(
    [qpdf_bin(), "--check", str(path)], env=qpdf_env(), capture_output=True, text=True
)
result["qpdf"] = dict(
    returncode=check.returncode, stdout=check.stdout, stderr=check.stderr
)
with pikepdf.open(path) as pdf:
    font = (
        pdf.pages[0]
        .Resources.Font.F1.DescendantFonts[0]
        .FontDescriptor.FontFile2.read_bytes()
    )
    (root / "preunion.ttf").write_bytes(font)
ots = subprocess.run(
    [ots_bin(), str(root / "preunion.ttf"), str(root / "preunion-sanitized.ttf")],
    capture_output=True,
    text=True,
)
result["ots"] = dict(returncode=ots.returncode, stdout=ots.stdout, stderr=ots.stderr)
(root / "construction-verification.json").write_text(json.dumps(result, indent=2))
print(
    json.dumps(
        {
            e: dict(
                extraction_identical=result[e]["extraction_identical"],
                changed_pages=[r["page"] for r in result[e]["pages"] if not r["equal"]],
            )
            for e in ["pdfium", "poppler"]
        },
        indent=2,
    )
)
print("validators", check.returncode, ots.returncode)
# Show exact fixed source boxes around the four planned substitutions.
meta = json.loads(
    Path("qualification/font02/local/reuse-study/registered-pairs.json").read_text()
)["observations"]
plan = json.loads((root / "town-affine/preunion-plan.json").read_text())["occurrences"]
source = np.asarray(
    Image.open("qualification/font02/local/reuse-study/town-source.png").convert("RGB")
)
for e in ["pdfium", "poppler"]:
    sheet = Image.new("RGB", (3 * 256, len(plan) * 180), "white")
    draw = ImageDraw.Draw(sheet)
    for row, occ in enumerate(plan):
        x, y, xx, yy = meta[occ["target"]]["bbox"]
        box = (x - 4, y - 4, xx + 4, yy + 4)
        pdfbox = tuple(
            round(v * 300 / 72 * (435 / 1813 if k % 2 == 0 else 637 / 2655))
            for k, v in enumerate(box)
        )
        for col, (label, image, bounds) in enumerate(
            [
                ("Source", source, box),
                ("Baseline", renders[e, "baseline"], pdfbox),
                ("Candidate", renders[e, "candidate"], pdfbox),
            ]
        ):
            crop = Image.fromarray(image).crop(bounds)
            crop.thumbnail((240, 150))
            draw.text(
                (col * 256 + 2, row * 180 + 2),
                label + " target" + str(occ["target"]),
                fill="black",
            )
            sheet.paste(
                crop.resize(
                    (
                        crop.width * min(4, 240 // crop.width),
                        crop.height * min(4, 150 // crop.height),
                    ),
                    Image.Resampling.NEAREST,
                ),
                (col * 256, row * 180 + 22),
            )
    sheet.save(root / f"construction-four-{e}.png")
