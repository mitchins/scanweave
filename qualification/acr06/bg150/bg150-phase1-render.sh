#!/bin/bash
set -u
q=/data/coding/scanweave/qualification
root=$q/acr06/local/bg150
e=$q/acr06/bg150
for g in financial forms historical mixed receipts; do
 while ! grep -q "^$g 0$" "$root/baseline/status.txt" 2>/dev/null || ! grep -q "^$g 0$" "$root/unguarded/status.txt" 2>/dev/null; do sleep 10; done
 "$q/.venv/bin/python" -I "$e/preservation.py" "$root/baseline/$g.pdf" "$root/unguarded/$g.pdf" "$e/phase1-render-$g.json" > "$root/phase1-render-$g.log" 2>&1
 printf '%s %s\n' "$g" "$?" >> "$root/phase1-render-status.txt"
done
