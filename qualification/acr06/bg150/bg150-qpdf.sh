#!/bin/bash
root=/data/coding/scanweave/qualification/acr06/local/bg150
for name in financial forms historical mixed receipts single competitive300 competitive600 fresh1 fresh2; do
 while ! grep -q "^$name 0$" "$root/candidate/status.txt" 2>/dev/null; do sleep 10; done
 LD_LIBRARY_PATH=/data/coding/scanweave/tools/dist/lib /data/coding/scanweave/tools/dist/bin/qpdf --check "$root/candidate/$name.pdf" > "$root/qualification/$name-qpdf-fixed.log" 2>&1
 printf '%s %s\n' "$name" "$?" >> "$root/qualification/qpdf-status.txt"
done
