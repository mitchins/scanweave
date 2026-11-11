#!/bin/sh
set -eu
R=/data/coding/scanweave/qualification/acr06
O=$R/local/hvc41c/default
mkdir -p "$O"
for doc in historical receipts financial mixed forms; do
 /data/coding/scanweave/qualification/.venv/bin/python -I "$R/hvc41c/locked_run.py" "/data/coding/scanweave/qualification/pdf_packaging/groups/$doc-input.pdf" "$O/$doc.pdf" --sidecar "$R/local/ink33r/$doc.pdf.json" --time-file "$O/$doc.time" > "$O/$doc.log" 2>&1
 cmp "$O/$doc.pdf" "$R/local/ink33r/$doc.pdf"
 echo "$doc IDENTICAL"
done
echo COMPLETE
