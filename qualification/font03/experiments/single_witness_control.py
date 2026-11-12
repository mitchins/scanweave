"""Matched source-singleton tracing control; fixed cohorts and no new admission."""

from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile

import numpy as np
import pikepdf
import pypdfium2 as pdfium
from PIL import Image

from qualification.font03.probe_pdf import contour_matrix, font_resource, operands
from qualification.font02.rendered_reuse import coverage_metrics

ROOT = Path("qualification/font03/local")
OUT = ROOT / "single-witness-control"


def prepare(split):
    """Use the same non-target medoid and placement as the existing B arm."""
    root = ROOT / "affine-refinement"
    rows = json.loads((ROOT / f"{split}-sources.json").read_text())["records"]
    images = np.load(ROOT / f"{split}-canvases.npy")
    plan = json.loads((root / f"{split}-render-plan.json").read_text())
    templates = []
    for target in plan["targets"]:
        donor = target["medoid"]
        if (
            rows[donor]["id"] == target["id"]
            or rows[donor]["id"] not in target["witness_ids"]
        ):
            raise RuntimeError("Single donor is not an independent witness")
        if rows[donor]["character"] != target["character"]:
            raise RuntimeError("Single donor character mismatch")
        templates.append(
            dict(
                key=target["id"],
                character=rows[donor]["character"],
                size=64,
                coverage=images[donor].ravel().tolist(),
            )
        )
    OUT.mkdir(exist_ok=True)
    (OUT / f"{split}-trace-input.json").write_text(
        json.dumps(dict(templates=templates))
    )


def make_pdf(split):
    """Fresh trace and existing multi-witness programs occupy separate fonts."""
    root = ROOT / "affine-refinement"
    source = json.loads((ROOT / f"{split}-bindings.json").read_text())["source_pdf"]
    rows = json.loads((ROOT / f"{split}-sources.json").read_text())["records"]
    plan = json.loads((root / f"{split}-render-plan.json").read_text())
    curves = OUT / f"{split}-curves"
    outlines = json.loads((curves / "template-outlines.json").read_text())
    lookup = {o["key"]: o for o in outlines}
    with pikepdf.open(source) as original:
        pdf = pikepdf.Pdf.new()
        font = font_resource(pdf, curves / "templates.ttf", outlines)
        for number in range(3):
            pdf.pages.append(original.pages[number])
            page = pdf.pages[-1]
            page.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F3=font))
            commands = ["q 1 1 1 rg 0 0 432 648 re f Q", "BT 0 Tr 0 0 0 rg /F3 1 Tf"]
            for target in plan["targets"]:
                row = rows[target["target"]]
                if row["page"] != number:
                    continue
                outline = lookup[target["id"]]
                matrix = operands(
                    contour_matrix(row, target["medoid_parameters"], outline)
                )
                commands.append(
                    " ".join(f"{v:.10f}" for v in matrix)
                    + " Tm <"
                    + outline["gid"].to_bytes(2, "big").hex()
                    + "> Tj"
                )
            commands.append("ET")
            page.Contents = pdf.make_stream(("\n".join(commands) + "\n").encode())
        pdf.save(
            OUT / f"{split}-F.pdf",
            object_stream_mode=pikepdf.ObjectStreamMode.generate,
            compress_streams=True,
            deterministic_id=True,
        )


def render(path, page, dpi, engine):
    if engine == "pdfium":
        document = pdfium.PdfDocument(path)
        p = document[page]
        bitmap = p.render(scale=dpi / 72)
        image = np.asarray(bitmap.to_pil().convert("L")).copy()
        bitmap.close()
        p.close()
        document.close()
        return image
    with tempfile.TemporaryDirectory() as directory:
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
                directory + "/p",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        with Image.open(directory + "/p.png") as image:
            return np.asarray(image.convert("L")).copy()


def evaluate(split):
    """Oracle evaluation only after source input and completed PDF are saved."""
    root = ROOT / "affine-refinement"
    rows = {
        r["id"]: r
        for r in json.loads((ROOT / f"{split}-sources.json").read_text())["records"]
    }
    records = json.loads((root / f"{split}-evaluated.json").read_text())["records"]
    results = []
    for engine in ["pdfium", "poppler"]:
        pages = {
            p: render(OUT / f"{split}-F.pdf", p, [200, 300, 600][p], engine)
            for p in range(3)
        }
        for record in records:
            if record["renderer"] != engine or record["arm"] != "C":
                continue
            row = rows[record["target"]]
            left, top, right, bottom = record["bounds"]
            x, y, xx, yy = row["public_bbox"]
            pristine = np.zeros((bottom - top, right - left))
            path = (
                Path("qualification/font01/local/corpus-font01-v1")
                / split
                / "oracle"
                / f'{record["target"]}-pristine.png'
            )
            with Image.open(path) as image:
                pristine[y - top : yy - top, x - left : xx - left] = (
                    1 - np.asarray(image.convert("L"), float) / 255
                )
            coverage = (
                1 - pages[row["page"]][top:bottom, left:right].astype(float) / 255
            )
            results.append(
                dict(
                    target=record["target"],
                    renderer=engine,
                    multi=record["pristine"],
                    single=coverage_metrics(pristine, coverage),
                )
            )
    summary = {
        arm: dict(
            mean_error=float(np.mean([r[arm]["mse"] for r in results])),
            p95_error=float(np.quantile([r[arm]["mse"] for r in results], 0.95)),
            mean_iou=float(np.mean([r[arm]["iou"] for r in results])),
        )
        for arm in ["single", "multi"]
    }
    output = dict(
        summary=summary,
        records=results,
        source_sha256=hashlib.sha256(
            (OUT / f"{split}-trace-input.json").read_bytes()
        ).hexdigest(),
        pdf_sha256=hashlib.sha256((OUT / f"{split}-F.pdf").read_bytes()).hexdigest(),
    )
    (OUT / f"{split}-evaluated.json").write_text(json.dumps(output, indent=2))
    print(split, summary, flush=True)


if __name__ == "__main__":
    action, split = sys.argv[1:]
    {"prepare": prepare, "pdf": make_pdf, "evaluate": evaluate}[action](split)
