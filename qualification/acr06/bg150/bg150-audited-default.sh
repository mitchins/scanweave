#!/bin/bash
set -u
q=/data/coding/scanweave/qualification
root=$q/acr06/local/bg150
out=$root/audited-default
mkdir -p "$out"
while ! grep -q '^complete$' "$root/baseline/status.txt" 2>/dev/null; do sleep 10; done
for g in financial forms historical mixed receipts; do
 SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so /tmp/bg150-audited-target/release/scanweave "$q/pdf_packaging/groups/$g-input.pdf" "$out/$g.pdf" --dpi 300 --profile clearscan --glyph-sharing off > "$out/$g.log" 2>&1
 status=$?; printf '%s %s\n' "$g" "$status" >> "$out/status.txt"; [ "$status" -eq 0 ] || exit "$status"
 cmp -s "$out/$g.pdf" "$root/baseline/$g.pdf"; printf '%s %s\n' "$g" "$?" >> "$out/identity.txt"
done
