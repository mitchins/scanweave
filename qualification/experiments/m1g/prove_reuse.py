#!/usr/bin/env python3
"""Extract the 60-occurrence cross-page `a` prototype reuse proof."""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).resolve().parent / "fixture" / "dpi300"
PROTOTYPE = "prototype:40f6b6b18aa07c830cf39d96ad37f27e4a8a4860424fffbb4ce2fad58cdd4b95"


def main() -> None:
    report = json.loads((FIXTURE / "output" / "report.json").read_text())
    records = []
    gids = {}
    for page in report["page_reports"]:
        matches = [o for o in page["reconstruction"]["occurrences"]
                   if o["prototype_id"] == PROTOTYPE and (o["repaired"] or o["reused"])]
        if not matches:
            continue
        ids = {o["symbol_id"] for o in matches}
        gid = next((g["gid"] for g in page["glyph_stats"]
                    if g.get("symbol_id") in ids), None)
        gids[page["page_id"]] = gid
        for o in matches:
            records.append({"page_id": page["page_id"],
                            "symbol_id": o["symbol_id"],
                            "decision": o["decision"],
                            "source_mask_iou": o["source_mask_iou"]})
    counts = collections.Counter(x["decision"] for x in records)
    proof = {"character": "a", "prototype_id": PROTOTYPE,
             "accepted_occurrences": len(records), "pages": sorted(gids),
             "representative_gids_by_page": gids,
             "decision_counts": dict(counts),
             "source_mask_iou_range": [min(x["source_mask_iou"] for x in records),
                                       max(x["source_mask_iou"] for x in records)],
             "occurrences": records}
    if len(records) != 60 or len(gids) != 6 or set(gids.values()) != {2}:
        raise SystemExit("reuse proof did not match expected 60 occurrences / six pages / GID 2")
    path = FIXTURE / "output" / "reuse-proof.json"
    path.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(path)


if __name__ == "__main__":
    main()
