#!/bin/sh
set -eu
r=/data/coding/scanweave/qualification/acr06
for mode in corner interior_mode bright_mode interior_median tile_median_128; do
 /usr/bin/time -v -o "$r/local/hvc41/time-$mode.txt" /data/coding/scanweave/qualification/.venv/bin/python -I "$r/hvc41/time_estimator.py" "$mode" > "$r/local/hvc41/time-$mode.json" 2>&1
 echo "$mode COMPLETE"
done
echo COMPLETE
