#!/bin/bash
set -u
q=/data/coding/scanweave/qualification
root=$q/acr06/local/bg150
e=$q/acr06/bg150
for name in historical mixed receipts fresh1 fresh2; do
 case "$name" in fresh1) src="$root/fresh/page-1.pdf";; fresh2) src="$root/fresh/page-2.pdf";; *) src="$q/pdf_packaging/groups/$name-input.pdf";; esac
 while ! grep -q "^$name 0$" "$root/candidate/status.txt" 2>/dev/null; do sleep 10; done
 "$q/.venv/bin/python" -I "$e/artwork.py" "$name" "$src" "$root/baseline/$name.pdf" "$root/candidate/$name.pdf" "$e/artwork-$name.json" > "$root/qualification/$name-artwork.log" 2>&1
 printf '%s %s\n' "$name" "$?" >> "$root/qualification/artwork-status.txt"
 if [ -f "$root/unguarded/$name.pdf" ]; then
  "$q/.venv/bin/python" -I "$e/artwork.py" "$name" "$src" "$root/baseline/$name.pdf" "$root/unguarded/$name.pdf" "$e/phase1-artwork-$name.json" > "$root/qualification/$name-phase1-artwork.log" 2>&1
  printf '%s %s\n' "$name" "$?" >> "$root/qualification/phase1-artwork-status.txt"
 fi
done
