from pathlib import Path
import hashlib
import json
import subprocess
import sys
import importlib.metadata as md
from qualification.tools_env import qpdf_bin, ots_bin, qpdf_env

root = Path("qualification/font03/local")
paths = [
    Path("qualification/pdf_packaging/groups/financial-input.pdf"),
    Path("qualification/font02/local/financial-required.pdf"),
    root / "financial-preunion.pdf",
    root / "financial-preunion.pdf.json",
    root / "construction-inventory.json",
    root / "construction-verification.json",
    root / "scanweave-main",
    root / "scanweave-preunion",
    Path("target/release/font03_templates"),
]
for split in ["train", "validation", "test"]:
    base = Path("qualification/font01/local/corpus-font01-v1") / split
    paths.extend([base / "observations.jsonl", base / "oracle/labels.jsonl"])
    paths.extend(root.glob(f"{split}-*.*"))
    paths.extend((root / "affine-refinement").glob(f"{split}-*.*"))
paths.extend((root / "affine-refinement").glob("*calibration.json"))
paths.extend((root / "town-affine").glob("*.json"))
paths.extend((root / "repair").glob("*.json"))
paths.extend((root / "final-review").glob("*.json"))
files = {
    str(p): dict(
        bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()
    )
    for p in sorted(set(paths))
    if p.is_file()
}


def version(command, env=None):
    p = subprocess.run(command, env=env, capture_output=True, text=True)
    return (p.stdout + p.stderr).splitlines()[:2]


result = dict(
    base="c10e3dff93ca12ac410c0f6626a4ef74ce34e0c1",
    branch="research/font03-consensus",
    product_activated=False,
    scope="Source-only fitting; pristine files evaluator-only, no production dependency. Test families previously inspected development.",
    versions=dict(
        python=sys.version,
        packages={
            m: md.version(m)
            for m in ["numpy", "scipy", "Pillow", "fonttools", "pikepdf", "pypdfium2"]
        },
        rust=version(["rustc", "--version"]),
        poppler=version(["pdftoppm", "-v"]),
        qpdf=version([qpdf_bin(), "--version"], qpdf_env()),
        ots=version([ots_bin(), "--version"]),
    ),
    files=files,
    performance=dict(
        baseline_seconds=496.86,
        baseline_peak_kib=1466412,
        construction_seconds=469.90,
        construction_peak_kib=1489120,
        note="Unpaired, concurrent qualification. No performance improvement claimed.",
    ),
)
Path("qualification/font03/manifest.json").write_text(json.dumps(result, indent=2))
