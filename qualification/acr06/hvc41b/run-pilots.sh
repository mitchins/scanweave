#!/bin/sh
set -eu
cd /tmp/scanweave-hvc41
export SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so
export SCANWEAVE_HVC41B_OCR_SIDECAR=/data/coding/scanweave/qualification/acr06/local/ink33r/historical.pdf.json
export SCANWEAVE_HVC41B_INTERIOR=1
unset SCANWEAVE_HVC41_INTERIOR SCANWEAVE_HVC41_PIXEL_CONTACT SCANWEAVE_HVC41_DUMP_DIR
for mode in interior border; do
 out=/data/coding/scanweave/qualification/acr06/local/hvc41b/$mode
 mkdir -p "$out"
 export SCANWEAVE_HVC41B_TRACE_DIR="$out"
 if [ "$mode" = border ]; then export SCANWEAVE_HVC41B_BORDER_CONTACT=1; else unset SCANWEAVE_HVC41B_BORDER_CONTACT; fi
 /usr/bin/time -v -o "$out/historical.time" ./target/release/scanweave /data/coding/scanweave/qualification/pdf_packaging/groups/historical-input.pdf "$out/historical.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$out/historical.log" 2>&1
 echo "$mode COMPLETE"
done
echo COMPLETE
