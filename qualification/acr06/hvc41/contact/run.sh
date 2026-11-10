#!/bin/sh
set -eu
mode=$1
out=/data/coding/scanweave/qualification/acr06/local/hvc41/contact/$mode
mkdir -p "$out"
cd /tmp/scanweave-hvc41
export SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so
export SCANWEAVE_HVC41_PIXEL_CONTACT=1
if [ "$mode" = interior ]; then export SCANWEAVE_HVC41_INTERIOR=1; docs='historical receipts'; else unset SCANWEAVE_HVC41_INTERIOR; docs='historical receipts financial mixed forms'; fi
for doc in $docs; do
 mkdir -p "$out/$doc"
 export SCANWEAVE_HVC41_DUMP_DIR="$out/$doc"
 /usr/bin/time -v -o "$out/$doc.time" ./target/release/scanweave "/data/coding/scanweave/qualification/pdf_packaging/groups/$doc-input.pdf" "$out/$doc.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$out/$doc.log" 2>&1
 echo "$doc COMPLETE"
done
echo COMPLETE
