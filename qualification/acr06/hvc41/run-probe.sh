#!/bin/sh
set -eu
cd /tmp/scanweave-hvc41
out=/data/coding/scanweave/qualification/acr06/local/hvc41
cargo build --release --locked -p scanweave-cli
export SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so
export SCANWEAVE_HVC41_INTERIOR=1
for doc in historical receipts financial mixed forms; do
 mkdir -p "$out/trial2/$doc"
 if [ "$doc" = historical ] || [ "$doc" = receipts ]; then export SCANWEAVE_HVC41_DUMP_DIR="$out/trial2/$doc"; else unset SCANWEAVE_HVC41_DUMP_DIR; fi
 /usr/bin/time -v -o "$out/trial2/$doc.time" ./target/release/scanweave "/data/coding/scanweave/qualification/pdf_packaging/groups/$doc-input.pdf" "$out/trial2/$doc.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$out/trial2/$doc.log" 2>&1
 echo "$doc COMPLETE"
done
echo COMPLETE
