#!/usr/bin/env python3
"""Historical painted-resource audit entry point; shared implementation."""
from pathlib import Path
import sys

B = Path(__file__).resolve().parent
ROOT = B.parents[1]
sys.path.insert(0, str(B.parent))
from clearscan_audit import audit as _audit, main as _main


def audit(dpi, arm, path, report_path=None):
    """Retain the historical arm argument; accounting is arm-independent."""
    return _audit(dpi, path, report_path, root=ROOT)


if __name__ == '__main__':
    _main(B, ROOT)
