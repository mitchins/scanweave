#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
PY="${SCANWEAVE_EVAL_PYTHON:-/tmp/scanweave-competitive-venv/bin/python}"
B=qualification/clearscan_competitive
cargo build --release -p scanweave-cli
for dpi in 300 600; do
  /usr/bin/time -v -o "$B/$dpi/final-time.txt" target/release/scanweave-cli build --bundle "qualification/experiments/m1g/fixture/dpi$dpi/input/document.json" --profile clearscan --output "$B/$dpi/clearscan.pdf" --report "$B/$dpi/clearscan.json" > "$B/$dpi/final.log" 2>&1
  for arm in source adobe previous final; do
    pdf="$B/$dpi/$arm.pdf"; report="$B/$dpi/$arm.json"
    if [[ "$arm" == final ]]; then pdf="$B/$dpi/clearscan.pdf"; report="$B/$dpi/clearscan.json"; fi
    "$PY" "$B/compare.py" "$dpi" "$arm" "$pdf"
    if [[ "$arm" == final || "$arm" == previous ]]; then
      [[ "$dpi/$arm" == 300/previous ]] && report="$B/300/diagnostic.json"
      "$PY" "$B/audit.py" "$dpi" "$arm" "$pdf" --report "$report"
    elif [[ "$arm" == adobe ]]; then "$PY" "$B/audit.py" "$dpi" "$arm" "$pdf"; fi
  done
  "$PY" "$B/stages.py" "$dpi" final "$B/$dpi/clearscan.pdf" "$B/$dpi/clearscan.json"
done
"$PY" "$B/identity.py"
"$PY" "$B/geometry.py"
"$PY" "$B/ownership_audit.py"
"$PY" "$B/summarize.py"
"$PY" "$B/examples.py"
