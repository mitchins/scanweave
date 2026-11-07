#!/bin/bash
set -u
q=/data/coding/scanweave/qualification; root=$q/acr06/local/bg150; out=$root/audited-verify
mkdir -p "$out"
while ! grep -q 'Finished `release` profile' "$root/audited-build.log"; do sleep 5; done
run() {
 name=$1; input=$2; dpi=$3
 while ! grep -q "^$name 0$" "$root/candidate/status.txt" 2>/dev/null || ! grep -q "^$name 0$" "$root/repeat/status.txt" 2>/dev/null; do sleep 10; done
 SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so /tmp/bg150-audited-target/release/scanweave "$input" "$out/$name.pdf" --dpi "$dpi" --profile clearscan --glyph-sharing off --experimental-background-dpi 150 > "$out/$name.log" 2>&1
 status=$?; printf 'run %s %s\n' "$name" "$status" >> "$out/status.txt"; [ "$status" -eq 0 ] || exit "$status"
 cmp -s "$out/$name.pdf" "$root/candidate/$name.pdf"; printf 'same %s %s\n' "$name" "$?" >> "$out/status.txt"
}
if [ "$1" = groups ]; then
 for g in financial forms historical mixed receipts; do run "$g" "$q/pdf_packaging/groups/$g-input.pdf" 300; done
else
 run single "$q/pdf_packaging/real/input/scan-c03-29.pdf" 300
 run competitive300 "$q/clearscan_competitive/300/source.pdf" 300
 run competitive600 "$q/clearscan_competitive/600/source.pdf" 600
 run fresh1 "$root/fresh/page-1.pdf" 300
 run fresh2 "$root/fresh/page-2.pdf" 300
fi
