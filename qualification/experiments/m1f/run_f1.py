#!/usr/bin/env python3
"""Generate bounded, real-PDF F1 ablations; converter never reads oracle."""
from __future__ import annotations
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "qualification/competitors/adobe_xi"
OUT = Path(__file__).resolve().parent / "results"
CLI = ROOT / "target/debug/scanweave-cli"

CASES = [
    ("dpi300", 300, "clearscan", ["reuse", "gray"]),
    ("dpi300-12", 300, "faithful", ["reuse"]),
]

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    records = []
    for case, dpi, profile, variants in CASES:
        source = EVIDENCE / "inputs" / case / "document.json"
        for variant in variants:
            target = OUT / case / profile / f"{variant}.pdf"
            report = OUT / case / profile / f"{variant}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and report.exists():
                report_data = json.loads(report.read_text())
                record = {"case": case, "dpi": dpi, "profile": profile, "variant": variant,
                          "returncode": 0, "reused_existing_output": True,
                          "peak_rss_kib": None, "pdf": str(target.relative_to(ROOT)),
                          "pdf_bytes": target.stat().st_size, "pdf_sha256": sha(target),
                          "report": str(report.relative_to(ROOT)), "report_sha256": sha(report),
                          "report_data": report_data}
                records.append(record)
                print(json.dumps({k: v for k, v in record.items() if k != "report_data"}, indent=2), flush=True)
                continue
            command = ["/usr/bin/time", "-f", "M1F_PEAK_RSS_KIB=%M", str(CLI), "build", "--bundle", str(source), "--mode", "auto",
                       "--profile", profile, "--pdf-image-variant", variant,
                       "--output", str(target), "--report", str(report)]
            start = time.monotonic()
            run = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            elapsed = time.monotonic() - start
            combined = run.stdout + run.stderr
            rss = re.search(r"M1F_PEAK_RSS_KIB=(\d+)", run.stderr)
            record = {"case": case, "dpi": dpi, "profile": profile, "variant": variant,
                      "command": command, "returncode": run.returncode,
                      "elapsed_seconds": round(elapsed, 3),
                      "peak_rss_kib": int(rss.group(1)) if rss else None,
                      "stdout": combined.strip()}
            if run.returncode == 0:
                record.update({"pdf": str(target.relative_to(ROOT)), "pdf_bytes": target.stat().st_size,
                               "pdf_sha256": sha(target), "report": str(report.relative_to(ROOT)),
                               "report_sha256": sha(report),
                               "report_data": json.loads(report.read_text())})
            records.append(record)
            print(json.dumps({k: v for k, v in record.items() if k != "report_data"}, indent=2), flush=True)
            if run.returncode:
                break
    (OUT / "f1-runs.json").write_text(json.dumps(records, indent=2) + "\n")

if __name__ == "__main__":
    main()
