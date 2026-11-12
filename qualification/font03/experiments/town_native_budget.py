"""Reproduce the frozen pre-review native gate, not a current product policy."""

from pathlib import Path
import json

root = Path("qualification/font03/local/town-affine")
config = json.loads(Path("qualification/font03/construction-control.json").read_text())
rows = json.loads((root / "town-render-results.json").read_text())
fields = json.loads((root / "field-decisions.json").read_text())
lookup = {(r["target"], r["engine"], r["arm"]): r for r in rows}
output = []
for row in fields:
    reasons = list(row["reasons"])
    for engine in ("pdfium", "poppler"):
        baseline = lookup[row["target"], engine, "A"]
        candidate = lookup[row["target"], engine, "C"]
        if candidate["mse"] > baseline["mse"] + config["noise"]:
            reasons.append(engine + " native source budget")
        reasons.extend(
            engine + " " + reason for reason in candidate["geometry_reasons"]
        )
    output.append(dict(target=row["target"], accepted=not reasons, reasons=reasons))
actual = sorted(r["target"] for r in output if r["accepted"])
if actual != config["expected_native_targets"]:
    raise RuntimeError(f"Frozen construction decision mismatch: {actual}")
(root / "native-decisions.json").write_text(json.dumps(output, indent=2))
