#!/bin/bash
set -u
cd /tmp/scanweave-bg150
out=/data/coding/scanweave/qualification/acr06/local/bg150/baseline
mkdir -p "$out"
for g in financial forms historical mixed receipts; do
  SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so target/release/scanweave "/data/coding/scanweave/qualification/pdf_packaging/groups/$g-input.pdf" "$out/$g.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$out/$g.log" 2>&1
  status=$?
  printf '%s %s\n' "$g" "$status" >> "$out/status.txt"
  [ "$status" -eq 0 ] || exit "$status"
done
sha256sum "$out"/*.pdf > "$out/sha256.txt"
printf 'complete\n' >> "$out/status.txt"
