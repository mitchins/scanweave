#!/usr/bin/env python3
"""Issue #31 functional check: for every reference word (span /ActualText) of length >= 2,
is it present in PDFium's and in Poppler's page text (whitespace/hyphen-normalized), and how
many times does PDFium's native search find it compared with the reference count?
Usage: findable.py PDF [PDF ...]"""
import sys, re, subprocess
from collections import Counter
import pikepdf, pypdfium2 as pdfium
sys.path.insert(0, __import__("os").path.dirname(__file__))
from measure import actual_texts, norm
tot = Counter()
for p in sys.argv[1:]:
    pk = pikepdf.open(p); doc = pdfium.PdfDocument(p)
    for i, page in enumerate(pk.pages):
        ref = [w for a in actual_texts(page) for w in a.split() if len(norm(w)) >= 2]
        tp = doc[i].get_textpage(); ft = norm(tp.get_text_range())
        pt = norm(subprocess.run(["pdftotext", "-f", str(i + 1), "-l", str(i + 1), "-enc", "UTF-8", p, "-"], capture_output=True, text=True).stdout)
        rc = Counter(ref)
        for w, n in rc.items():
            k = norm(w)
            tot["words"] += n
            tot["pdfium_missing"] += norm(w) not in ft
            tot["poppler_missing"] += norm(w) not in pt
            s = tp.search(w, match_case=True); hits = 0
            while s.get_next():
                hits += 1
            tot["search_short"] += max(0, n - hits)
            tot["search_excess"] += max(0, hits - n)
print(dict(tot))
