#!/bin/sh
set -eu
base=/data/coding/scanweave/qualification/acr06/local/ink37
out=$base/polarity37
bin=/tmp/scanweave-ink37/target/release/scanweave
export SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so
export SCANWEAVE_POLARITY37_MEASURE=1
for set in controls controls-supplemental positive-controls table-candidates; do
 mkdir -p "$out/$set"
 for input in "$base/$set"/*.pdf; do
  name=$(basename "$input" .pdf)
  "$bin" "$input" "$out/$set/$name.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$out/$set/$name.log" 2>&1
  printf '%s/%s complete\n' "$set" "$name"
 done
done
"$bin" "$base/table-context-control.pdf" "$out/table-context.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$out/table-context.log" 2>&1
printf 'COMPLETE\n'
