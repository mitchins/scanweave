#!/bin/bash
set -u
q=/data/coding/scanweave/qualification
root=$q/acr06/local/bg150
evidence=$q/acr06/bg150
python=$q/.venv/bin/python
mkdir -p "$root/qualification" "$root/panels"
run() {
 name=$1; input=$2; statusfile=$3
 while ! grep -q "^$name 0$" "$statusfile" 2>/dev/null || ! grep -q "^$name 0$" "$root/candidate/status.txt" 2>/dev/null; do sleep 10; done
 /data/coding/scanweave/tools/dist/bin/qpdf --check "$root/candidate/$name.pdf" > "$root/qualification/$name-qpdf.log" 2>&1
 printf 'qpdf %s %s\n' "$name" "$?" >> "$root/qualification/status.txt"
 "$python" -I "$evidence/preservation.py" "$root/baseline/$name.pdf" "$root/candidate/$name.pdf" "$evidence/preservation-$name.json" > "$root/qualification/$name-preservation.log" 2>&1
 printf 'preservation %s %s\n' "$name" "$?" >> "$root/qualification/status.txt"
 "$python" -I "$evidence/measure.py" "$input" "$root/baseline/$name.pdf" "$root/candidate/$name.pdf" "$evidence/quality-$name.json" > "$root/qualification/$name-quality.log" 2>&1
 printf 'quality %s %s\n' "$name" "$?" >> "$root/qualification/status.txt"
 if [ "$statusfile" = "$root/baseline/status.txt" ]; then
  "$python" -I "$evidence/panels.py" "$name" "$input" "$root/baseline/$name.pdf" "$root/candidate/$name.pdf" "$root/panels" --adobe "$q/pdf_packaging/groups/$name-adobe.pdf" --archive "$q/pdf_packaging/groups/$name-archive.pdf" > "$root/qualification/$name-panels.log" 2>&1
 else
  "$python" -I "$evidence/panels.py" "$name" "$input" "$root/baseline/$name.pdf" "$root/candidate/$name.pdf" "$root/panels" > "$root/qualification/$name-panels.log" 2>&1
 fi
 printf 'panels %s %s\n' "$name" "$?" >> "$root/qualification/status.txt"
}
if [ "$1" = groups ]; then
 for g in financial forms historical mixed receipts; do run "$g" "$q/pdf_packaging/groups/$g-input.pdf" "$root/baseline/status.txt"; done
else
 s="$root/baseline/extra-status.txt"
 run single "$q/pdf_packaging/real/input/scan-c03-29.pdf" "$s"
 run competitive300 "$q/clearscan_competitive/300/source.pdf" "$s"
 run competitive600 "$q/clearscan_competitive/600/source.pdf" "$s"
 run fresh1 "$root/fresh/page-1.pdf" "$s"
 run fresh2 "$root/fresh/page-2.pdf" "$s"
fi
