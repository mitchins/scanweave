#!/usr/bin/env python3
"""Write a SHA-256 inventory for M1-G source, oracle, and output evidence."""
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy
import PIL

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).resolve().parent / "fixture"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    subprocess = __import__("subprocess")
    source_paths = ["crates/scanweave-cli/src/main.rs",
                    "crates/scanweave-io/src/convert.rs",
                    "crates/scanweave-io/src/document.rs",
                    "crates/scanweave-io/src/units.rs",
                    "crates/scanweave-io/src/visual_dict.rs"]
    base_head = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                        cwd=ROOT, text=True).strip()
    source_diff = subprocess.check_output(["git", "diff", "--binary", "HEAD", "--", *source_paths],
                                          cwd=ROOT)
    result = {"repository_head": base_head,
        "implementation_source_diff": {"base_head": base_head,
                                        "files": source_paths,
                                        "sha256": hashlib.sha256(source_diff).hexdigest()},
        "generator_environment": {"python": sys.version.split()[0],
                                  "platform": platform.platform(),
                                  "numpy": numpy.__version__,
                                  "pillow": PIL.__version__},
        "source_fonts": {
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf": {
                "sha256": "8f2c103bfa3fd5de71f1b92b18f21906b5a26871fb7e19a9a4c9af539c3cc7ab"},
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf": {
                "sha256": "eaeaf7f2b12544ecde64290c1fa7ec403ff70fd58b313637b265400b20249242"},
            "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf": {
                "sha256": "a63f6153841e56ec9df1b31a54d98d3f41d8aaa1c3d8df30a33502296f5b8068"}},
        "dpi": {}}
    for dpi in (300, 600):
        base = FIXTURE / f"dpi{dpi}"
        files = {}
        manifest = json.loads((base / "input" / "document.json").read_text())
        paths = [base / "input" / "document.json"]
        paths.extend(base / "input" / source["asset_path"]
                     for source in manifest["sources"])
        paths.extend(base / "input" / page["ocr_page_path"]
                     for page in manifest["pages"])
        # Use explicit manifest paths for source files; generated oracle images
        # are kept separate and never exposed to the converter bundle.
        for i in range(len(manifest["pages"])):
            paths.extend([base / "oracle" / f"page{i:02}.png",
                          base / "oracle" / f"page{i:02}.truth.json"])
        output = base / "output"
        output_names = ["canonical-experimental.pdf", "report.json",
                        "evaluation.json", "run.log", "time.txt",
                        "reuse-proof.json", "glyph-crops-poppler.png",
                        "replaced-zero-zoom.png"]
        paths.extend(output / name for name in output_names)
        for path in paths:
            if path.is_file():
                rel = path.relative_to(base).as_posix()
                files[rel] = {"bytes": path.stat().st_size, "sha256": digest(path)}
        result["dpi"][str(dpi)] = files
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else FIXTURE / "m1g_hashes.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(path)


if __name__ == "__main__":
    main()
