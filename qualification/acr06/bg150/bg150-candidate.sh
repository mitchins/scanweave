#!/bin/bash
set -u
q=/data/coding/scanweave/qualification
root=$q/acr06/local/bg150
out=$root/candidate
repeat=$root/repeat
mkdir -p "$out" "$repeat"
while ! grep -q 'Finished `release` profile' "$root/product-build.log"; do sleep 5; done
run() {
 name=$1; input=$2; dpi=$3
 for dest in "$out" "$repeat"; do
   SCANWEAVE_PDFIUM_LIBRARY=/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so /tmp/bg150-product-target/release/scanweave "$input" "$dest/$name.pdf" --dpi "$dpi" --profile clearscan --glyph-sharing off --experimental-background-dpi 150 > "$dest/$name.log" 2>&1
   status=$?; printf '%s %s\n' "$name" "$status" >> "$dest/status.txt"; [ "$status" -eq 0 ] || exit "$status"
 done
 cmp -s "$out/$name.pdf" "$repeat/$name.pdf"; printf '%s %s\n' "$name" "$?" >> "$root/determinism.txt"
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
