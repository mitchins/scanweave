#!/bin/sh
set -eu
cd /tmp/scanweave-ink33r
cargo build --release --locked -p scanweave-cli
export SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so
out=/data/coding/scanweave/qualification/acr06/local/ink33r
src=/data/coding/scanweave/qualification/pdf_packaging/groups
for doc in historical receipts financial mixed forms; do
 /usr/bin/time -v -o "$out/$doc.time" ./target/release/scanweave "$src/$doc-input.pdf" "$out/$doc.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$out/$doc.log" 2>&1
 echo "$doc DONE"
done
echo COMPLETE
