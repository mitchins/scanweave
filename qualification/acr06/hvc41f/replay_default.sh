#!/bin/sh
set -u
R=/data/coding/scanweave/qualification/acr06
O=$R/local/hvc41f/default
mkdir -p "$O"
export PATH="$R/local/hvc41f/noocr-bin:$PATH"
for doc in historical receipts financial mixed forms; do
 (
 /data/coding/scanweave/qualification/.venv/bin/python -I "$R/hvc41c/locked_run.py" "/data/coding/scanweave/qualification/pdf_packaging/groups/$doc-input.pdf" "$O/$doc.pdf" --sidecar "$R/local/ink33r/$doc.pdf.json" --time-file "$O/$doc.time" > "$O/$doc.log" 2>&1
 code=$?
 if [ "$code" -eq 0 ] && cmp -s "$O/$doc.pdf" "$R/local/ink33r/$doc.pdf"; then echo IDENTICAL > "$O/$doc.status"; else echo "FAILED:$code" > "$O/$doc.status"; fi
 ) &
done
wait
for doc in historical receipts financial mixed forms; do printf '%s ' "$doc"; cat "$O/$doc.status"; done
