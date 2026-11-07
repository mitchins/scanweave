#!/bin/bash
set -u
out=/data/coding/scanweave/qualification/acr06/local/bg150/baseline
run() {
 name=$1; input=$2; dpi=$3
 SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so /tmp/scanweave-bg150/target/release/scanweave "$input" "$out/$name.pdf" --dpi "$dpi" --profile clearscan --glyph-sharing off > "$out/$name.log" 2>&1
 status=$?; printf '%s %s\n' "$name" "$status" >> "$out/extra-status.txt"; [ "$status" -eq 0 ] || exit "$status"
}
q=/data/coding/scanweave/qualification
run single "$q/pdf_packaging/real/input/scan-c03-29.pdf" 300
run competitive300 "$q/clearscan_competitive/300/source.pdf" 300
run competitive600 "$q/clearscan_competitive/600/source.pdf" 600
run fresh1 "$q/acr06/local/bg150/fresh/page-1.pdf" 300
run fresh2 "$q/acr06/local/bg150/fresh/page-2.pdf" 300
printf 'complete\n' >> "$out/extra-status.txt"
