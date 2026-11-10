#!/bin/sh
set -eu
cd /data/coding/scanweave
p=qualification/.venv/bin/python
e=qualification/acr06/ink33r
for script in provenance.py ocr_provenance.py old_all.py old_summary.py compare.py paired_lines.py fill_local.py edge_differences.py export_chars.py report.py verify.py; do
 "$p" -I "$e/$script"
done
