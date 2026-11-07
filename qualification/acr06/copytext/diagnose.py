#!/usr/bin/env python3
"""Issue #31 diagnosis with PDFium itself: map each extracted char to its source text
object (FPDFText_GetTextObject), group objects by their /ActualText span, and report every
span whose text PDFium emits more than once, with the objects that interrupted it.
Usage: diagnose.py PDF [PAGE ...]"""
import sys, ctypes, json
import pikepdf, pypdfium2 as pdfium, pypdfium2.raw as R
sys.path.insert(0, __import__("os").path.dirname(__file__))
from simulate import objects

def diagnose(pdf_path, pages=None):
    pk = pikepdf.open(pdf_path); doc = pdfium.PdfDocument(pdf_path); out = []
    for pi in pages if pages is not None else range(len(doc)):
        meta = objects(pk.pages[pi])  # text objects in content order
        pg = doc[pi]; tp = pg.get_textpage()
        text_objs = [R.FPDFPage_GetObject(pg.raw, i) for i in range(R.FPDFPage_CountObjects(pg.raw))]
        text_objs = [o for o in text_objs if R.FPDFPageObj_GetType(o) == R.FPDF_PAGEOBJ_TEXT]
        assert len(text_objs) == len(meta), (len(text_objs), len(meta))
        idx = {ctypes.cast(o, ctypes.c_void_p).value: i for i, o in enumerate(text_objs)}
        runs = []  # (mark, [object indices]) in extraction order
        for c in range(R.FPDFText_CountChars(tp.raw)):
            o = R.FPDFText_GetTextObject(tp.raw, c)
            i = idx.get(ctypes.cast(o, ctypes.c_void_p).value)
            if i is None:
                continue
            m = meta[i]["mark"]
            if runs and runs[-1][0] == m:
                if i not in runs[-1][1]:
                    runs[-1][1].append(i)
            else:
                runs.append((m, [i]))
        seen = {}
        for k, (m, objs) in enumerate(runs):
            if m is None:
                continue
            if m in seen:
                prev = runs[k - 1]
                culprit = [dict(text=meta[i]["text"], invisible=meta[i]["invisible"], x=round(meta[i]["x"], 2), y=round(meta[i]["y"], 2), w=round(meta[i]["w"], 2), h=round(meta[i]["h"], 2)) for i in prev[1]]
                victim = [dict(x=round(meta[i]["x"], 2), y=round(meta[i]["y"], 2), invisible=meta[i]["invisible"]) for i in objs]
                out.append(dict(page=pi, span=meta[objs[0]]["text"], intruder=culprit[:3], resumed_at=victim[:2]))
            seen[m] = k
    return out

if __name__ == "__main__":
    pages = [int(p) for p in sys.argv[2:]] or None
    res = diagnose(sys.argv[1], pages)
    for r in res:
        print(json.dumps(r, ensure_ascii=False))
    print("repeats", len(res))
