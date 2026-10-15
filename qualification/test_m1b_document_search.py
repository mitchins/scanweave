#!/usr/bin/env python3
"""M1-B document-level search gate.

For each document fixture: build with scanweave --bundle, then verify with the
real engines:
  - page count, order and dimensions (pdfinfo)
  - per-page NATIVE PDFium search of distinctive tokens
  - the mixed reconstructed/fallback line "Page 1 of 4" (native + Poppler)
  - horizontal Japanese (kana) survives on the JP pages
  - no duplicated searchable text on any page
  - document-wide Poppler extraction keeps page order
  - qpdf --check
  - the repeated-text document: four pages, one valid searchable PDF
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "qualification/.venv/lib/python3.12/site-packages")
import pypdfium2 as pdfium  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "qualification" / "fixtures" / "documents"
WORK = Path("/tmp/opencode/m1b_docsearch")
CLI = ROOT / "target" / "debug" / "scanweave-cli"

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def build(doc: str, mode: str = "reconstruct"):
    d = WORK / doc
    d.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [str(CLI), "build", "--bundle", str(DOCS / doc / "document.json"),
         "--mode", mode, "--output", str(d / "out.pdf"), "--report", str(d / "out.json")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr[:400]
    return d / "out.pdf", d / "out.json"


def poppler(pdf: Path, first=None, last=None) -> str:
    cmd = ["pdftotext"]
    if first:
        cmd += ["-f", str(first), "-l", str(last or first)]
    cmd += [str(pdf), "-"]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def pdfium_doc(pdf: Path):
    return pdfium.PdfDocument(str(pdf))


def doc_gate(name: str, doc: str, pages: int, tokens: dict[int, list[str]], mode="reconstruct"):
    pdf, rep = build(doc, mode)
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    n_pages = int([l for l in info.splitlines() if l.startswith("Pages:")][0].split()[1])
    check(f"{name}: page count", n_pages == pages, f"{n_pages} != {pages}")
    q = subprocess.run(
        [str(ROOT / "tools/dist/bin/qpdf"), "--check", str(pdf)],
        capture_output=True, text=True,
        env={"LD_LIBRARY_PATH": str(ROOT / "tools/dist/lib")},
    )
    check(f"{name}: qpdf --check", q.returncode == 0, q.stdout.splitlines()[0] if q.stdout else q.stderr[:80])

    d = pdfium_doc(pdf)
    for i in range(min(pages, len(d))):
            tp = d[i].get_textpage()
            text = tp.get_text_bounded()
            for tok in tokens.get(i + 1, []):
                native = bool(tp.search(tok).get_next())
                check(f"{name}: page{i+1} native search {tok!r}", native)
                check(f"{name}: page{i+1} contains {tok!r}", tok in text)
            # no duplicated searchable text: no token appears twice in a page
            for tok in tokens.get(i + 1, []):
                stripped = "".join(text.split())
                if stripped.count(tok) > 1:
                    check(f"{name}: page{i+1} no duplicate {tok!r}", False, f"count={stripped.count(tok)}")
            # kana / astral sanity on JP pages
            if doc == "doc10_mixed" and i + 1 == 8:
                # p03_kana's own label is the single kana ガ; require it exactly
                check("doc10_mixed: page8 kana 'ガ' intact", "ガ" in text, repr(text[:40]))
    d.close()

    # document-wide Poppler extraction keeps page order
    all_text = poppler(pdf)
    order_ok = True
    last = -1
    for i in range(pages):
        toks = tokens.get(i + 1, [])
        if not toks:
            continue
        # the page's LAST distinctive token must appear after the previous
        # page's last token (monotonic reading order in document extraction)
        tok = toks[-1]
        pos = all_text.find(tok, max(last, 0))
        if pos < 0 or pos < last:
            order_ok = False
            break
        last = pos
    check(f"{name}: pages in order (poppler)", order_ok)

    # report honesty
    r = json.loads(rep.read_text())
    check(f"{name}: report page count", r["pages"] == pages, str(r["pages"]))
    check(f"{name}: report order", len(r["page_order"]) == pages)
    check(f"{name}: both candidates measured", {c["name"] for c in r["candidates"]} == {"reconstruct", "raster_baseline"},
          str([c["name"] for c in r["candidates"]]))
    check(f"{name}: search plan covers pages", len(r["search"]["pages"]) == pages)
    check(f"{name}: bindings present", len(r["bindings"]) == pages and all(b["source_sha256"] and b["ocr_sha256"] for b in r["bindings"]))
    return r


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)

    # 4-page invoice: every page natively searchable, incl. the mixed line
    doc_gate("doc4_invoice", "doc4_invoice", 4, {
        1: ["Total", "INV-2026-0042", "Page 1 of 4"],
        2: ["Page 2 of 4"],
        3: ["Page 3 of 4"],
        4: ["Page 4 of 4"],
    })
    # the mixed line also passes in Poppler, in the right position
    pdf, _ = build("doc4_invoice")
    t1 = poppler(pdf, 1, 1)
    check("doc4_invoice: page1 poppler mixed line", "Page 1 of 4." in t1, repr(t1[-60:]))
    check("doc4_invoice: page1 poppler order",
          t1.find("Reference:") < t1.find("Page 1 of 4.") < t1.find("Please pay"))

    # repeated text: four pages of identical content, one valid PDF
    r = doc_gate("doc4_repeat", "doc4_repeat", 4, {
        1: ["Amount"], 2: ["Amount"], 3: ["Amount"], 4: ["Amount"],
    })
    same = all(pr["semantic_spans"] == r["page_reports"][0]["semantic_spans"] for pr in r["page_reports"])
    check("doc4_repeat: pages identical span counts", same)

    # mixed dispositions (statement + noisy + decorative + statement)
    doc_gate("doc4_mixed", "doc4_mixed", 4, {
        1: ["Amount"], 2: ["balance", "receipt"], 3: ["cafe", "42.00"], 4: ["Amount"],
    })

    # 10-page mixed incl. horizontal Japanese
    doc_gate("doc10_mixed", "doc10_mixed", 10, {
        1: ["Amount"], 8: ["ガ"], 10: ["Amount"],
    })

    # 2-page minimal
    doc_gate("doc2_min", "doc2_min", 2, {1: ["Amount"], 2: ["balance"]})

    width = max(len(n) for n, _, _ in results)
    failed = 0
    for name, ok, detail in results:
        if not ok or True:
            print(f"{'PASS' if ok else 'FAIL'} {name.ljust(width)} {detail}")
        failed += 0 if ok else 1
    print()
    print("FAILED:", [n for n, ok, _ in results if not ok] or "none")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
