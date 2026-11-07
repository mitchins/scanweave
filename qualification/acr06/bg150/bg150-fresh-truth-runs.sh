#!/bin/bash
set -u
q=/data/coding/scanweave/qualification; root=$q/acr06/local/bg150; e=$q/acr06/bg150
while [ ! -s "$e/fresh-truth-sha256.txt" ]; do sleep 5; done
for i in 1 2; do
 name=freshtruth$i; input=$root/fresh-truth/page-$i.pdf
 for arm in baseline candidate repeat; do
  if [ "$arm" = baseline ]; then binary=/tmp/scanweave-bg150/target/release/scanweave; flag=(); else binary=/tmp/bg150-audited-target/release/scanweave; flag=(--experimental-background-dpi 150); fi
  SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so "$binary" "$input" "$root/$arm/$name.pdf" --dpi 300 --profile clearscan --glyph-sharing off "${flag[@]}" > "$root/$arm/$name.log" 2>&1
  status=$?; printf '%s %s\n' "$name" "$status" >> "$root/$arm/status.txt"; [ "$status" -eq 0 ] || exit "$status"
 done
 cmp -s "$root/candidate/$name.pdf" "$root/repeat/$name.pdf"; printf '%s %s\n' "$name" "$?" >> "$root/determinism.txt"
 cp "$root/candidate/$name.pdf" "$root/audited-verify/$name.pdf"; cp "$root/candidate/$name.log" "$root/audited-verify/$name.log"
 printf 'run %s 0\nsame %s 0\n' "$name" "$name" >> "$root/audited-verify/status.txt"
 LD_LIBRARY_PATH=/data/coding/scanweave/tools/dist/lib /data/coding/scanweave/tools/dist/bin/qpdf --check "$root/candidate/$name.pdf" > "$root/qualification/$name-qpdf-fixed.log" 2>&1
 printf '%s %s\n' "$name" "$?" >> "$root/qualification/qpdf-status.txt"
 "$q/.venv/bin/python" -I "$e/preservation.py" "$root/baseline/$name.pdf" "$root/candidate/$name.pdf" "$e/preservation-$name.json" > "$root/qualification/$name-preservation.log" 2>&1; printf 'preservation %s %s\n' "$name" "$?" >> "$root/qualification/status.txt"
 "$q/.venv/bin/python" -I "$e/measure.py" "$input" "$root/baseline/$name.pdf" "$root/candidate/$name.pdf" "$e/quality-$name.json" > "$root/qualification/$name-quality.log" 2>&1; printf 'quality %s %s\n' "$name" "$?" >> "$root/qualification/status.txt"
 "$q/.venv/bin/python" -I "$e/panels.py" "$name" "$input" "$root/baseline/$name.pdf" "$root/candidate/$name.pdf" "$root/panels" > "$root/qualification/$name-panels.log" 2>&1; printf 'panels %s %s\n' "$name" "$?" >> "$root/qualification/status.txt"
done
