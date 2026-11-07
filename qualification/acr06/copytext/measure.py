#!/usr/bin/env python3
"""Issue #31 measurement: per page, compare PDFium and Poppler extracted words with the
reference word sequence carried by the PDF itself (the per-span /ActualText strings in
content order). Usage: measure.py OUT.json PDF [PDF ...]"""
import json, sys, subprocess, re
from collections import Counter
from pathlib import Path
import pikepdf, pypdfium2 as pdfium

def actual_texts(page):
    out = []
    for operands, op in pikepdf.parse_content_stream(page):
        if op == pikepdf.Operator("BDC") and len(operands) == 2 and isinstance(operands[1], pikepdf.Dictionary):
            a = operands[1].get("/ActualText")
            if a is not None:
                out.append(str(a))
    return out

def words(s):
    return s.split()

def norm(s):
    # whitespace, PDFium's U+FFFE line-end hyphen marker and hyphens are layout, not content
    return re.sub(r"[\s\ufffe\u00ad\-\u2010\u2011]", "", s)

def diff(ref_words, got_text):
    """Character alignment of extracted text against the reference sequence.
    inserted: chars absent from the reference at that place; duplicated: inserted runs of
    >=3 chars that repeat reference text within 200 chars; deleted: reference chars lost."""
    import difflib
    r, g = norm("".join(ref_words)), norm(got_text)
    sm = difflib.SequenceMatcher(None, r, g, autojunk=False)
    ins = dele = dup = 0; dups = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("insert", "replace"):
            seg = g[j1:j2]; ins += len(seg)
            if len(seg) >= 3 and seg in r[max(0, i1 - 200):i2 + 200]:
                dup += len(seg); dups.append(seg[:40])
        if tag in ("delete", "replace"):
            dele += i2 - i1
    return dict(ref_chars=len(r), inserted=ins, deleted=dele, duplicated=dup, duplicated_runs=len(dups), examples=dups[:6])

def main():
    res = {}
    for p in sys.argv[2:]:
        p = Path(p)
        pk = pikepdf.open(p); pd = pdfium.PdfDocument(str(p))
        pages = []
        for i, page in enumerate(pk.pages):
            ref = [w for a in actual_texts(page) for w in words(a)]
            tp = pd[i].get_textpage()
            fw = words(tp.get_text_range())
            pw = words(subprocess.run(["pdftotext", "-f", str(i + 1), "-l", str(i + 1), "-enc", "UTF-8", str(p), "-"], capture_output=True, text=True).stdout)
            pages.append(dict(page=i, pdfium=diff(ref, " ".join(fw)), poppler=diff(ref, " ".join(pw))))
            rt = Counter(norm(w) for w in ref if norm(w))
            for eng, got in (("pdfium", fw), ("poppler", pw)):
                gt = Counter(norm(w) for w in got if norm(w))
                pages[-1][eng]["word_tokens"] = sum(rt.values())
                pages[-1][eng]["word_tokens_matched"] = sum((rt & gt).values())
        res[p.name] = pages
    summary = {}
    for eng in ("pdfium", "poppler"):
        for k in ("ref_chars", "inserted", "deleted", "duplicated", "duplicated_runs", "word_tokens", "word_tokens_matched"):
            summary[f"{eng}_{k}"] = sum(pg[eng][k] for d in res.values() for pg in d)
        summary[f"{eng}_pages_with_duplication"] = sum(1 for d in res.values() for pg in d if pg[eng]["duplicated_runs"])
    Path(sys.argv[1]).write_text(json.dumps(dict(summary=summary, documents=res), indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
