#!/usr/bin/env python3
"""Dual-layer fixture validation (qualification harness only).

Layer 1 (this script): authoritative Draft 2020-12 JSON-Schema validation of the
negative/positive fixtures (serde semantics alone diverge from JSON Schema).
Layer 2: Rust typed layer with deny_unknown_fields — see
crates/scanweave-core/tests/ocr_page_validation.rs (cargo test -p scanweave-core).

Run: python3 qualification/validate_fixtures.py
"""
import glob
import json
import os
import sys

import jsonschema

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_DIR = os.path.join(HERE, "..", "reference", "scanweave-spec-v0.1", "schemas")


def main() -> int:
    schema = json.load(open(os.path.join(SCHEMA_DIR, "ocr-page.schema.json")))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    failures = []

    for f in sorted(glob.glob(os.path.join(HERE, "fixtures", "positive", "*.json"))):
        doc = json.load(open(f))
        errs = list(validator.iter_errors(doc))
        status = "ok" if not errs else "UNEXPECTED REJECT: " + errs[0].message
        print(f"positive {os.path.basename(f)}: {status}")
        if errs:
            failures.append(f)

    for f in sorted(glob.glob(os.path.join(HERE, "fixtures", "negative", "*.json"))):
        doc = json.load(open(f))
        errs = list(validator.iter_errors(doc))
        status = "ok" if errs else "SCHEMA ACCEPTED INVALID DOCUMENT"
        print(f"negative {os.path.basename(f)}: {status}")
        if not errs:
            failures.append(f)

    if failures:
        print(f"FAILED: {failures}")
        return 1
    print("schema fixture layer: all fixtures behave as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
