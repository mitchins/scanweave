#!/bin/bash
set -u
q=/data/coding/scanweave/qualification
root=$q/acr06/local/bg150
e=$q/acr06/bg150
for g in financial forms mixed receipts; do
 while ! grep -q "^$g 0$" "$root/baseline/status.txt" 2>/dev/null || ! grep -q "^$g 0$" "$root/unguarded/status.txt" 2>/dev/null; do sleep 10; done
 if [ "$g" = financial ]; then pages=(--pages 8,9,10,11,12,13); else pages=(); fi
 "$q/.venv/bin/python" -I "$e/measure.py" "$q/pdf_packaging/groups/$g-input.pdf" "$root/baseline/$g.pdf" "$root/unguarded/$g.pdf" "$e/phase1-heldout-$g.json" "${pages[@]}" > "$root/phase1-heldout-$g.log" 2>&1
 printf '%s %s\n' "$g" "$?" >> "$root/phase1-heldout-status.txt"
done
