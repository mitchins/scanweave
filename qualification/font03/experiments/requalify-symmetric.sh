#!/bin/sh
set -eu
export PYTHONPATH=.
py=qualification/.venv/bin/python
root=qualification/font03/local/affine-refinement
$py qualification/font03/experiments/affine_refinement.py
for split in validation test; do
  mkdir -p "$root/$split-curves"
  target/release/font03_templates "$root/$split-trace-input.json" "$root/$split-curves"
done
$py qualification/font03/experiments/synthetic_pdfs.py "$root"
$py qualification/font03/experiments/synthetic_measure.py validation "$root"
$py qualification/font03/experiments/synthetic_measure.py test "$root"
$py qualification/font03/experiments/native_budget.py
$py qualification/font03/experiments/structural_calibration.py
$py qualification/font03/experiments/synthetic_evaluate.py validation "$root"
$py qualification/font03/experiments/synthetic_evaluate.py test "$root"
$py qualification/font03/experiments/final_atlas.py
