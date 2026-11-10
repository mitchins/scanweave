#!/bin/sh
set -eu
r=/data/coding/scanweave/qualification/acr06
out=$r/local/ink33r
e=$r/ink33r
p=/data/coding/scanweave/qualification/.venv/bin/python
for doc in historical receipts financial mixed forms; do
 while ! grep -q "^$doc DONE$" "$out/run.log"; do sleep 60; done
 "$p" -I -c 'import sys,json,hashlib,pathlib; d=sys.argv[1]; r=pathlib.Path("/data/coding/scanweave/qualification/acr06"); expected=next(x for x in json.loads((r/"ink37c/cprime/bytes.json").read_text())["documents"] if x["document"]==d)["sha256"][3]; actual=hashlib.sha256((r/"local/ink33r"/(d+".pdf")).read_bytes()).hexdigest(); print(d,actual,"MATCH" if actual==expected else "MISMATCH",flush=True); sys.exit(actual!=expected)' "$doc"
 "$p" -I "$e/prepare.py" "$doc" > "$out/prepare-$doc.log" 2>&1
 echo "$doc PREPARED"
 "$p" -I "$e/measure.py" "$doc" > "$out/measure-$doc.log" 2>&1
 echo "$doc MEASURED"
done
"$p" -I "$e/operator_audit.py" > "$out/audit.log" 2>&1
"$p" -I "$e/line_inventory.py" > "$out/inventory.log" 2>&1
"$p" -I "$e/adobe_policy.py" > "$out/adobe.log" 2>&1
"$p" -I "$e/validate_edits.py" > "$out/validate.log" 2>&1
"$p" -I "$e/panels.py" > "$out/panels.log" 2>&1
echo COMPLETE
