#!/bin/sh
set -eu
out=/data/coding/scanweave/qualification/acr06/local/ink37
src=/data/coding/scanweave/qualification/pdf_packaging/groups
export SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so
for doc in historical financial mixed receipts forms; do
  /tmp/scanweave-ink37/target/release/scanweave "$src/$doc-input.pdf" "$out/$doc-candidate.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$out/$doc-candidate.log" 2>&1
  sha256sum "$out/$doc-candidate.pdf"
done
printf 'COMPLETE\n'
