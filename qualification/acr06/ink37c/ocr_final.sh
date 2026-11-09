#!/bin/sh
set -eu
root=/data/coding/scanweave/qualification/acr06/local
out=$root/ink37c/ocr-final
mkdir -p "$out"
for item in historical-02 historical-05 receipts-04; do
 doc=${item%-*}; n=${item#*-}
 for arm in source lossless compact; do
  case "$arm" in
   source) file="$root/ink33/renders/$doc/$n-source.png" ;;
   lossless) file="$root/ink37/owner37/renders/pdfium/$doc/candidate-$n.png" ;;
   compact) file="$root/ink37c/renders-final/pdfium/$item-300.png" ;;
  esac
  tesseract "$file" "$out/$item-$arm" -l eng --psm 3 > "$out/$item-$arm.log" 2>&1
  echo "$item $arm COMPLETE"
 done
done
echo COMPLETE
