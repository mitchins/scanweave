#!/bin/bash
set -u
q=/data/coding/scanweave/qualification
out=$q/acr06/local/bg150/faithful
mkdir -p "$out"
for mode in default experiment; do
 args=(); [ "$mode" = default ] || args=(--experimental-background-dpi 150)
 SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so /tmp/bg150-product-target/release/scanweave "$q/pdf_packaging/real/input/scan-c03-29.pdf" "$out/$mode.pdf" --dpi 300 --profile faithful --glyph-sharing off "${args[@]}" > "$out/$mode.log" 2>&1
 status=$?; printf '%s %s\n' "$mode" "$status" >> "$out/status.txt"; [ "$status" -eq 0 ] || exit "$status"
done
cmp -s "$out/default.pdf" "$out/experiment.pdf"; printf 'identical %s\n' "$?" >> "$out/status.txt"
