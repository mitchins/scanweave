from pathlib import Path
import json
import sys
import tempfile
import subprocess
import hashlib
import time
import numpy as np
from PIL import Image
from scipy import ndimage
import pypdfium2 as pdfium
from qualification.font03.consensus import geometry_rejections, warp, affine_warp

root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("qualification/font03/local")
split = sys.argv[1]
plan = json.loads((root / f"{split}-render-plan.json").read_text())
rows = json.loads((root / f"{split}-sources.json").read_text())["records"]
lookup = {r["id"]: r for r in rows}
source_canvases = np.load(root / f"{split}-canvases.npy")
target_plan = {r["id"]: r for r in plan["targets"]}
templates = {
    r["key"]: np.array(r["coverage"]).reshape(64, 64)
    for r in json.loads((root / f"{split}-trace-input.json").read_text())["templates"]
}
pages = {
    i: np.asarray(
        Image.open(
            Path("qualification/font01/local/corpus-font01-v1")
            / split
            / f"page-{i}.png"
        ).convert("L"),
        float,
    )
    for i in range(3)
}


def region(r):
    x, y, xx, yy = map(int, r["bbox"])
    px, py, qx, qy = r["public_bbox"]
    left, top, right, bottom = (
        min(x, px) - 4,
        min(y, py) - 4,
        max(xx, qx) + 4,
        max(yy, qy) + 4,
    )
    patch = pages[r["page"]][top:bottom, left:right]
    mask = np.zeros(patch.shape, bool)
    mask[y - top : yy - top, x - left : xx - left] = np.array(r["mask"], bool).reshape(
        r["height"], r["width"]
    )
    distance = ndimage.distance_transform_edt(~mask)
    foreign = (r["paper"] - patch > 60) & ~mask
    fd = (
        ndimage.distance_transform_edt(~foreign)
        if foreign.any()
        else np.full(mask.shape, 100.0)
    )
    coverage = np.clip((r["paper"] - patch) / (r["paper"] - r["ink"]), 0, 1) * (
        (distance <= 1.5) & (distance < fd)
    )
    return [left, top, right, bottom], coverage


regions = {i: region(lookup[i]) for i in target_plan}


def render(page, dpi, engine):
    path = root / f"{split}-ABCD.pdf"
    if engine == "pdfium":
        d = pdfium.PdfDocument(path)
        p = d[page]
        b = p.render(scale=dpi / 72)
        a = np.asarray(b.to_pil().convert("L")).copy()
        b.close()
        p.close()
        d.close()
        return a
    with tempfile.TemporaryDirectory() as t:
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                str(page + 1),
                "-l",
                str(page + 1),
                "-singlefile",
                "-r",
                str(dpi),
                "-gray",
                "-png",
                str(path),
                t + "/p",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with Image.open(t + "/p.png") as im:
            return np.asarray(im.convert("L")).copy()


start = time.monotonic()
records = []
maps = {}
for engine in ["pdfium", "poppler"]:
    for atlas in plan["atlas"]:
        image = render(atlas["atlas_page"], atlas["dpi"], engine)
        for target in atlas["targets"]:
            p = target_plan[target]
            arm = atlas["arm"]
            bounds, source = regions[target]
            x, y, xx, yy = bounds
            coverage = 1 - image[y:yy, x:xx].astype(float) / 255.0
            maps[f"{engine}-{arm}-{target}"] = coverage.astype(np.float32)
            normerror = None
            normreasons = []
            if arm in ["C", "D"]:
                field = templates[p[arm]]
                aligned = (affine_warp if len(p["parameters"]) == 5 else warp)(
                    source_canvases[p["target"]], p["parameters"]
                )
                normerror = float(
                    ((field - aligned) ** 2).sum() / max(1.0, aligned.sum())
                )
                normreasons = geometry_rejections(aligned, field)
            native_reasons = geometry_rejections(source, coverage)
            gate = (
                arm in ["C", "D"]
                and normerror <= plan["training_noise_upper"]
                and not normreasons
                and not native_reasons
            )
            records.append(
                dict(
                    renderer=engine,
                    target=target,
                    arm=arm,
                    bounds=bounds,
                    source_mse=float(
                        ((source - coverage) ** 2).sum() / max(1.0, source.sum())
                    ),
                    native_geometry_reasons=native_reasons,
                    normalized_geometry_reasons=normreasons,
                    normalized_error=normerror,
                    source_gate=gate,
                )
            )
    np.savez_compressed(root / f"{split}-native-coverages.npz", **maps)
    print(split, engine, "seconds", round(time.monotonic() - start, 2), flush=True)
output = root / f"{split}-source-rendered.json"
output.write_text(
    json.dumps(dict(records=records, seconds=time.monotonic() - start), indent=2)
)
(root / f"{split}-source-freeze.json").write_text(
    json.dumps(
        dict(
            decisions_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
            coverage_sha256=hashlib.sha256(
                (root / f"{split}-native-coverages.npz").read_bytes()
            ).hexdigest(),
            protocol_sha256=hashlib.sha256(
                (root / "initial-protocol.json").read_bytes()
            ).hexdigest(),
            noise_sha256=hashlib.sha256(
                (root / "training-noise-calibration.json").read_bytes()
            ).hexdigest(),
        ),
        indent=2,
    )
)
