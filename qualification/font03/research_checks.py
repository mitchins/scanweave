"""Fail-closed evidence checks shared by the research entry points."""

from pathlib import Path


def require_files(paths):
    """Missing declared prerequisites must not silently disappear from provenance."""
    missing = [str(path) for path in paths if not Path(path).is_file()]
    if missing:
        raise FileNotFoundError("Missing required evidence: " + ", ".join(missing))


def repair_margin_supported(margin):
    """A best/next comparison requires two cohorts, including in rejected probes."""
    return margin is not None and margin >= 0.015


def require_construction_verification(result):
    """Persist diagnostics first, but never exit successfully after a failed gate."""
    if any(result[name]["returncode"] != 0 for name in ("qpdf", "ots")):
        raise RuntimeError(
            "PDF/font validation failed; inspect construction-verification.json"
        )
    for engine in ("pdfium", "poppler"):
        data = result[engine]
        counts = data["page_counts"]
        if len(counts) != 2 or counts[0] != counts[1]:
            raise RuntimeError(engine + " page count changed")
        if not data["extraction_identical"]:
            raise RuntimeError(engine + " native extraction changed")
        if any(not row["equal"] for row in data["pages"] if row["page"] != 1):
            raise RuntimeError(engine + " changed an uninvolved page")
