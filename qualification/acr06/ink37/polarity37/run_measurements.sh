#!/bin/sh
set -eu
out=/data/coding/scanweave/qualification/acr06/local/ink37/polarity37
src=/data/coding/scanweave/qualification/pdf_packaging/groups
bin=/tmp/scanweave-ink37/target/release/scanweave
export SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so
export SCANWEAVE_POLARITY37_MEASURE=1
for doc in historical financial mixed receipts forms; do
 "$bin" "$src/$doc-input.pdf" "$out/$doc-main.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$out/$doc.log" 2>&1
 sha256sum "$out/$doc-main.pdf"
done
printf 'COMPLETE\n'
