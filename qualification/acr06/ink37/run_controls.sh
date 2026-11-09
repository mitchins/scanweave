#!/bin/sh
set -eu
arm="$1"
binary="$2"
base=/data/coding/scanweave/qualification/acr06/local/ink37
mkdir -p "$base/control-$arm"
export SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so
for input in "$base"/controls/*.pdf; do
  name=$(basename "$input" .pdf)
  "$binary" "$input" "$base/control-$arm/$name.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$base/control-$arm/$name.log" 2>&1
  sha256sum "$base/control-$arm/$name.pdf"
done
printf 'COMPLETE\n'
