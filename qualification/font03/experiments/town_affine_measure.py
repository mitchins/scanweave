from pathlib import Path
import json
import tempfile
import subprocess
import numpy as np
from PIL import Image, ImageDraw
import pypdfium2 as pdfium
from qualification.font03.consensus import geometry_rejections, geometry

root = Path("qualification/font03/local/town-affine")
old = Path("qualification/font02/local/reuse-study")
g = json.loads((root / "town-groups.json").read_text())
bounds = {
    (r["target"]): r["source_bounds"]
    for r in json.loads((old / "rendered-substitution-results.json").read_text())[
        "records"
    ]
}
maps = np.load(old / "added-missing-ink-maps.npz")
results = []
renders = {}


def render(path, p, e):
    if e == "pdfium":
        d = pdfium.PdfDocument(path)
        page = d[p]
        b = page.render(scale=300 / 72)
        a = np.asarray(b.to_pil().convert("RGB")).copy()
        b.close()
        page.close()
        d.close()
        return a
    with tempfile.TemporaryDirectory() as t:
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                str(p + 1),
                "-l",
                str(p + 1),
                "-singlefile",
                "-r",
                "300",
                "-png",
                str(path),
                t + "/p",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with Image.open(t + "/p.png") as im:
            return np.asarray(im.convert("RGB")).copy()


for e in ["pdfium", "poppler"]:
    source = render(
        Path("qualification/pdf_packaging/groups/financial-input.pdf"), 0, e
    )
    for p, arm in enumerate(["A", "B", "C"]):
        image = render(root / "town-ABC.pdf", p, e)
        renders[e, arm] = image
        for i in range(42):
            x, y, xx, yy = bounds[i]
            a = maps[f"{e}-t{i}-source"]
            b = 1 - image[y:yy, x:xx].mean(2) / 255
            mass = max(1.0, a.sum())
            results.append(
                dict(
                    engine=e,
                    arm=arm,
                    target=i,
                    mse=float(((a - b) ** 2).sum() / mass),
                    added=float(np.maximum(b - a, 0).sum() / mass),
                    missing=float(np.maximum(a - b, 0).sum() / mass),
                    geometry_reasons=geometry_rejections(a, b),
                    geometry=geometry(b),
                )
            )
            np.save(root / f"{e}-{arm}-{i}.npy", b)
    # Fixed source selected words, native complete composition.
    images = [
        ("Source", source),
        (
            "Adobe",
            render(
                Path("qualification/pdf_packaging/groups/financial-adobe.pdf"), 0, e
            ),
        ),
        ("A", render(Path("qualification/font02/local/financial-required.pdf"), 0, e)),
        ("B", render(root / "financial-B-shadow.pdf", 0, e)),
        ("C", render(root / "financial-C-shadow.pdf", 0, e)),
    ]
    for name, box in [
        ("expires", [280, 175, 403, 226]),
        ("lower", [35, 290, 405, 450]),
    ]:
        box = tuple(round(v * 300 / 72) for v in box)
        w, h = box[2] - box[0], box[3] - box[1]
        sheet = Image.new("RGB", (w, (h + 22) * len(images)), "white")
        draw = ImageDraw.Draw(sheet)
        for n, (label, image) in enumerate(images):
            sheet.paste(Image.fromarray(image).crop(box), (0, n * (h + 22) + 22))
            draw.text((2, n * (h + 22) + 2), label, fill="black")
        sheet.save(root / f"town-{name}-{e}.png")
(root / "town-render-results.json").write_text(json.dumps(results, indent=2))
print(
    {
        (e, arm): round(
            float(
                np.mean(
                    [
                        r["mse"]
                        for r in results
                        if r["engine"] == e
                        and r["arm"] == arm
                        and r["target"]
                        in sum([f["original_indices"] for f in g["fitted"]], [])
                    ]
                )
            ),
            5,
        )
        for e in ["pdfium", "poppler"]
        for arm in ["A", "B", "C"]
    }
)
