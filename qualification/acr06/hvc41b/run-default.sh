#!/bin/sh
set -eu
cd /tmp/scanweave-hvc41
out=/data/coding/scanweave/qualification/acr06/local/hvc41b/default
mkdir -p "$out"
unset SCANWEAVE_HVC41_INTERIOR SCANWEAVE_HVC41_PIXEL_CONTACT SCANWEAVE_HVC41_DUMP_DIR SCANWEAVE_HVC41B_INTERIOR SCANWEAVE_HVC41B_BORDER_CONTACT SCANWEAVE_HVC41B_TRACE_DIR
export SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so
for doc in historical receipts financial mixed forms; do
 export SCANWEAVE_HVC41B_OCR_SIDECAR="/data/coding/scanweave/qualification/acr06/local/ink33r/$doc.pdf.json"
 /usr/bin/time -v -o "$out/$doc.time" ./target/release/scanweave "/data/coding/scanweave/qualification/pdf_packaging/groups/$doc-input.pdf" "$out/$doc.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$out/$doc.log" 2>&1
 echo "$doc COMPLETE"
done
echo COMPLETE
