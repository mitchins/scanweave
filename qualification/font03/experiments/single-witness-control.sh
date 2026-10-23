#!/bin/sh
set -eu
export PYTHONPATH=.
py=qualification/.venv/bin/python
root=qualification/font03/local/single-witness-control
for split in validation test; do
 $py qualification/font03/experiments/single_witness_control.py prepare "$split"
 mkdir -p "$root/$split-curves"
 target/release/font03_templates "$root/$split-trace-input.json" "$root/$split-curves"
 $py qualification/font03/experiments/single_witness_control.py pdf "$split"
 $py qualification/font03/experiments/single_witness_control.py evaluate "$split"
done
