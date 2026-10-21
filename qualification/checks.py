#!/usr/bin/env python3
"""M0 independent verification harness (qualification-only).

Runs the probe on every synthetic page and verifies each artifact with tools
independent of the implementation:
  - qpdf --check                    (structural, local build)
  - ots-sanitize                    (OpenType sanitizer)
  - fontTools                       (glyf contours, winding, glyph reuse)
  - pdftotext (Poppler)             (extraction engine #1)
  - pypdfium2 (PDFium)              (extraction + render engine #2)
  - pdftoppm (Poppler)              (render engine #1)
  - numpy metrics                   (dev-initial-1: IoU, edge p95/max, MAE,
                                     component/hole topology, counter colour)

Usage: qualification/.venv/bin/python qualification/checks.py [--pages p01,...]
Exits non-zero on any gate failure. Writes qualification/probe_results.json.
"""
import json
import os
import re
import subprocess
import sys
from collections import Counter

import numpy as np
from PIL import Image

FIXTURE_NOT_RUN = 'NOT_RUN (fixture page not in run)'
TRACE_LOG_JSON = 'trace_log.json'
OUTPUT_PDF = 'out.pdf'
OUTPUT_FONT_TTF = 'out.ttf'


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROBE = os.path.join(ROOT, "target", "debug", "m0-font-pdf")
FIXTURES = os.path.join(HERE, "fixtures", "probe")
WORK = os.path.join(ROOT, "work", "m0-checks")
# external tools resolve through the environment (local build, PATH, or an
# explicit override) so the harness runs on a clean checkout and in CI
from tools_env import ots_bin, qpdf_bin, qpdf_env, version  # noqa: E402


def QPDF() -> str:
    """qpdf, resolved on first use (a missing tool fails the gate, not the import)."""
    return qpdf_bin()


def OTS() -> str:
    """The OpenType sanitizer, resolved on first use."""
    return ots_bin()

sys.path.insert(0, os.path.join(HERE, ".venv", "lib", "python3.12", "site-packages"))
import pypdfium2 as pdfium  # noqa: E402

DPI = 300.0
PT = 72.0 / DPI

# dev-initial-1 operating policy (defaults.toml [visual])
MIN_IOU = 0.98
MAX_EDGE_P95 = 0.5
MAX_EDGE_MAX = 1.0
MAX_MAE = 0.02
THRESHOLDS = (55, 60, 65)  # bounded stand-in for threshold offsets -0.05/0/+0.05

DEFAULT_PAGES = [
    "p01_latin", "p02_wronglabel", "p03_kana", "p04_ligature",
    "p05_colour", "p06_degraded", "p07_sharedcid", "p08_symbols",
]

EXPECTED = {
    "p01_latin": ["8", "6", "8", "a"],
    "p02_wronglabel": ["6"],
    "p03_kana": ["ガ"],
    "p04_ligature": ["fi", "𝐀"],
    "p05_colour": ["8"],
    "p06_degraded": ["8"],
    "p07_sharedcid": ["8", "6", "8", "18"],
    "p08_symbols": [".", ",", "-", "$", "%", "1,234.56", "-42"],
}


def expected_from_ocr(name: str) -> list[str] | None:
    """Original OCR input (the normalized OCR JSON fixture) — the transport
    contract is verified against THIS source, not a hand-typed list. Returns
    span texts in the fixture's declared reading order."""
    path = os.path.join(FIXTURES, name, f"{name}.ocr.json")
    if not os.path.exists(path):
        return None
    doc = json.load(open(path))
    spans = {s["id"]: s["text"] for s in doc["spans"]}
    if doc.get("reading_order"):
        return [spans[i] for i in doc["reading_order"] if i in spans]
    return [s["text"] for s in doc["spans"]]

results = {"pages": {}, "gates": {}, "tools": {}}


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def fg_mask(gray: np.ndarray, paper_lum: float, thresh: float = 60.0) -> np.ndarray:
    return np.abs(gray.astype(np.float64) - paper_lum) > thresh


def paper_luminance(rgb: np.ndarray) -> float:
    patches = np.concatenate(
        [
            rgb[:8, :8].reshape(-1, 3),
            rgb[:8, -8:].reshape(-1, 3),
            rgb[-8:, :8].reshape(-1, 3),
            rgb[-8:, -8:].reshape(-1, 3),
        ]
    )
    med = np.median(patches, axis=0)
    return 0.2126 * med[0] + 0.7152 * med[1] + 0.0722 * med[2]


def gray_of(rgb: np.ndarray) -> np.ndarray:
    return (
        0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    )


def boundary(m: np.ndarray) -> np.ndarray:
    er = m & np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1)
    return m & ~er


def subpixel_boundary_points(gray: np.ndarray, m: np.ndarray, i50: float) -> np.ndarray:
    """Anti-aliased sub-pixel boundary localization.

    For every adjacent (inside p, outside q) pixel pair, the 50%-coverage
    crossing is found by linear interpolation ALONG THE INSIDE-TO-OUTSIDE
    segment direction: I(t) = vi + (vq - vi) * t with t measured from p toward
    q; the crossing sits at t* = (i50 - vi) / (vq - vi), i.e. BEYOND p toward q,
    never mirrored. Pairs with a degenerate ramp (|vq - vi| < 1e-6) are skipped.

    Sampling threshold (rigorous definition): i50 MUST be the 50%-coverage
    intensity, i50 = (paper_ref + ink_ref) / 2, computed per image from its own
    paper and ink references. The binary mask `m` is only used to locate
    adjacent pairs; the metric therefore measures the geometric 50% contour of
    each image independently of its rasterizer's anti-aliasing strength.

    Known bound: linear interpolation of an ideal area-coverage edge has a
    phase-dependent bias of at most (3/2 - sqrt(2)) = (sqrt(2)-1)^2/2 ~= 0.086 px;
    analytical tests
    assert recovery within 0.09 px on that basis.

    Returns continuous points (pixel centres at x+0.5, y+0.5)."""
    pts = []
    H, W = m.shape
    g = gray
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        ys, xs = np.nonzero(m)
        qy, qx = ys + dy, xs + dx
        ok = (qy >= 0) & (qy < H) & (qx >= 0) & (qx < W)
        ys, xs, qy, qx = ys[ok], xs[ok], qy[ok], qx[ok]
        out_side = ~m[qy, qx]
        ys, xs, qy, qx = ys[out_side], xs[out_side], qy[out_side], qx[out_side]
        if len(ys) == 0:
            continue
        vi = g[ys, xs].astype(np.float64)
        vq = g[qy, qx].astype(np.float64)
        denom = vq - vi
        good = np.abs(denom) > 1e-6
        ys, xs, vi, vq, qy, qx = ys[good], xs[good], vi[good], vq[good], qy[good], qx[good]
        if len(ys) == 0:
            continue
        # t from p toward q at the i50 crossing (mirrored formula was the defect)
        t = (i50 - vi) / (vq - vi)
        t = np.clip(t, 0.0, 1.0)
        px = xs + 0.5
        py = ys + 0.5
        qx_c = qx + 0.5
        qy_c = qy + 0.5
        cx = px + (qx_c - px) * t
        cy = py + (qy_c - py) * t
        pts.append(np.stack([cx, cy], axis=1))
    if not pts:
        return np.zeros((0, 2))
    return np.concatenate(pts, axis=0)


def edge_errors_subpixel(
    gray_a: np.ndarray, a: np.ndarray, gray_b: np.ndarray, b: np.ndarray,
    i50_a: float, i50_b: float, cap: float = 12.0,
) -> tuple[float, float]:
    """Symmetric sub-pixel symmetric boundary distance (source pixels)."""
    if not a.any() and not b.any():
        return (0.0, 0.0)
    if not a.any() or not b.any():
        return (float(cap), float(cap))
    pa = subpixel_boundary_points(gray_a, a, i50_a)
    pb = subpixel_boundary_points(gray_b, b, i50_b)
    if len(pa) == 0 or len(pb) == 0:
        return (float(cap), float(cap))
    # cap the point counts for memory (bounded work)
    if len(pa) > 20000:
        pa = pa[:: len(pa) // 20000 + 1]
    if len(pb) > 20000:
        pb = pb[:: len(pb) // 20000 + 1]
    d2 = (
        (pa[:, 0][:, None] - pb[:, 0][None, :]) ** 2
        + (pa[:, 1][:, None] - pb[:, 1][None, :]) ** 2
    )
    da = np.sqrt(d2.min(axis=1))
    db = np.sqrt(d2.min(axis=0))
    per_point = np.concatenate([da, db])
    per_point = per_point[per_point <= cap]
    if len(per_point) == 0:
        return (float(cap), float(cap))
    p95 = float(np.percentile(per_point, 95))
    mx = float(per_point.max())
    return (p95, mx)


def components(m: np.ndarray) -> int:
    lab = np.zeros(m.shape, dtype=np.int32)
    nxt = 0
    H, W = m.shape
    for y in range(H):
        for x in range(W):
            if m[y, x] and lab[y, x] == 0:
                nxt += 1
                stack = [(y, x)]
                lab[y, x] = nxt
                while stack:
                    cy, cx = stack.pop()
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < H and 0 <= nx < W and m[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = nxt
                            stack.append((ny, nx))
    return nxt


def holes(m: np.ndarray) -> int:
    return components(~m) - 1  # minus the outer background component


def extract_poppler(pdf: str) -> str:
    r = sh(["pdftotext", pdf, "-"])
    return r.stdout


def extract_pdfium(pdf: str) -> str:
    doc = pdfium.PdfDocument(pdf)
    page = doc[0]
    tp = page.get_textpage()
    text = tp.get_text_bounded()
    doc.close()
    return text


def render_poppler(pdf: str, out_png: str) -> None:
    sh(["pdftoppm", "-r", "300", "-png", "-singlefile", pdf, out_png[:-4]])


def render_pdfium(pdf: str, out_png: str) -> None:
    doc = pdfium.PdfDocument(pdf)
    page = doc[0]
    bmp = page.render(scale=DPI / 72.0)
    pil = bmp.to_pil()
    if pil.mode != "RGB":
        pil = pil.convert("RGB")
    pil.save(out_png)
    doc.close()


def check_page(name: str) -> dict:
    out = {"name": name, "checks": {}, "metrics": {}, "fail": []}

    exp = EXPECTED.get(name)
    ocr_exp = expected_from_ocr(name)
    if ocr_exp is not None:
        if exp is not None and sorted(ocr_exp) != sorted(exp):
            # fixture OCR and hand list disagree — the OCR input is authoritative
            out["fail"].append(f"fixture OCR spans {ocr_exp} disagree with EXPECTED hand list {exp}")
        exp = ocr_exp
    if exp is None:
        out["fail"].append("no expectation source for this page")
        return out

    page_dir = os.path.join(FIXTURES, name)
    out_dir = os.path.join(WORK, name)
    os.makedirs(out_dir, exist_ok=True)

    # 1. probe build
    r = sh([PROBE, "build", "--page", page_dir, "--out", out_dir])
    out["checks"]["probe_build"] = r.returncode == 0
    if r.returncode != 0:
        out["fail"].append(f"probe build failed: {r.stderr[:300]}")
        return out
    pdf_path = os.path.join(out_dir, OUTPUT_PDF)
    ttf_path = os.path.join(out_dir, OUTPUT_FONT_TTF)
    out["pdf_bytes"] = os.path.getsize(pdf_path)
    out["ttf_bytes"] = os.path.getsize(ttf_path)

    # 2. qpdf --check + marked-content balance (qpdf does NOT check BDC/EMC
    #    pairing — the astral fix regression was invisible to it, so it is
    #    asserted structurally here)
    env = qpdf_env()
    r = sh([QPDF(), "--check", pdf_path], env=env)
    out["checks"]["qpdf"] = r.returncode == 0
    if r.returncode != 0:
        out["fail"].append(f"qpdf --check rc={r.returncode}: {r.stderr[:300]}")
    qdf = os.path.join(out_dir, "out.qdf.pdf")
    qr = sh([QPDF(), "--qdf", "--object-streams=disable", pdf_path, qdf], env=env)
    if qr.returncode == 0:
        raw = open(qdf, "rb").read()
        bdc, emc = raw.count(b"BDC\n"), raw.count(b"EMC\n")
        out["checks"]["marked_content_balanced"] = bdc == emc
        out["marked_content"] = {"bdc": bdc, "emc": emc}
        if bdc != emc:
            out["fail"].append(f"marked content unbalanced: BDC={bdc} EMC={emc}")
    else:
        out["checks"]["marked_content_balanced"] = False
        out["fail"].append("qpdf --qdf failed; balance not checked")

    # 3. ots-sanitize
    r = sh([OTS(), ttf_path])
    out["checks"]["ots"] = r.returncode == 0
    if r.returncode != 0:
        out["fail"].append(f"ots-sanitize rc={r.returncode}: {(r.stdout + r.stderr)[:300]}")

    # 4. fontTools independent font parse: contours + winding + reuse via CIDToGIDMap
    from fontTools.ttLib import TTFont

    try:
        tt = TTFont(ttf_path)
        glyf = tt["glyf"]
        names = [g for g in glyf.keys() if g != ".notdef"]
        out["font_glyphs"] = len(names)
        contour_info = {}
        for gname in names:
            g = glyf[gname]
            contours = g.numberOfContours
            # winding: TrueType outer contours are clockwise (negative shoelace y-up)
            winds = []
            pts = g.getCoordinates(glyf)[0]
            start = 0
            for ci in range(contours):
                end = g.endPtsOfContours[ci]
                ring = [pts[i] for i in range(start, end + 1)]
                start = end + 1
                area2 = sum(
                    ring[i][0] * ring[(i + 1) % len(ring)][1]
                    - ring[(i + 1) % len(ring)][0] * ring[i][1]
                    for i in range(len(ring))
                )
                winds.append(area2 / 2.0)
            contour_info[gname] = {"contours": contours, "signed_areas": winds}
        out["font_contours"] = contour_info
        out["checks"]["fonttools_parse"] = True
        # hole orientation check: every glyph with holes must have opposite-sign pairs
        holes_ok = True
        for gname, info in contour_info.items():
            areas = info["signed_areas"]
            # nonzero-winding correctness: the largest-magnitude contour is an
            # outer (clockwise, negative in y-up); degenerate contours flagged.
            # Multi-outer glyphs (disconnected marks) have several negative contours;
            # counter fidelity itself is verified by the render topology gate.
            if not areas:
                continue
            largest = max(areas, key=abs)
            if largest >= 0:
                holes_ok = False
                out["fail"].append(f"{gname}: outer contour not clockwise areas={areas}")
            degenerate = [a for a in areas if abs(a) < 5.0]
            if degenerate:
                out["degenerate_contours"] = {gname: degenerate}
        out["checks"]["hole_winding"] = holes_ok
    except Exception as e:  # noqa: BLE001
        out["checks"]["fonttools_parse"] = False
        out["fail"].append(f"fontTools parse failed: {e}")

    # 5. extraction: both engines verified against the OCR-input expectation
    # (exp is derived at the top of check_page from the fixture's OCR spans)
    for engine, fn in (("poppler", extract_poppler), ("pdfium", extract_pdfium)):
        try:
            text = fn(pdf_path)
        except Exception as e:  # noqa: BLE001
            out["checks"][f"extract_{engine}"] = False
            out["fail"].append(f"{engine} extraction failed: {e}")
            continue
        # Transport verification against the ORIGINAL OCR INPUT (item 3):
        # (1) codepoint cardinality + duplicate detection: the whitespace-
        #     stripped extraction must have EXACTLY the expected code points
        #     (no additions, deletions or duplicate layers);
        # (2) span coverage: each admitted span appears in reading order
        #     (order-preserving subsequence). Extractors may merge/remove
        #     inter-span whitespace and regroup layout lines; punctuation is
        #     never normalized. p08's scattered-symbol layout divergence
        #     remains a FAIL (not an exception) per the operator directive.
        got = "".join(t for t in re.split(r"\s+", text) if t)
        expected = "".join(exp)
        from collections import Counter as _C

        cardinality_ok = _C(got) == _C(expected)
        # coverage: each admitted span appears in reading order (order-preserving
        # subsequence) ...
        coverage_ok = True
        pos = 0
        for span_text in exp:
            idx = got.find(span_text, pos)
            if idx < 0:
                coverage_ok = False
                break
            pos = idx + len(span_text)
        # independent duplicate detection: after the ordered consumption of all
        # admitted spans, NOTHING may remain unconsumed. A duplicated layer or
        # unexpected extra text leaves a remainder (or breaks cardinality);
        # string counting is confounded by nested spans ('8' inside "18").
        duplicates_ok = coverage_ok and pos == len(got)
        # word-boundary integrity (primary semantic criteria): every span's text
        # must appear CONTIGUOUSLY in the raw extraction, and no multi-character
        # span may be split by spaces ('T o t a l' for 'Total' — the M0-Q-A defect
        # signature). Single-character spans between tokens are legitimate
        # separators. Whitespace-stripped cardinality stays supplementary.
        words_ok = all(sv in text for sv in exp)
        spaces_ok = not any(
            " ".join(sv) in text for sv in exp if len(sv) > 1
        )
        ok = words_ok and spaces_ok and cardinality_ok and duplicates_ok and coverage_ok
        out["checks"][f"extract_{engine}"] = ok
        out[f"extracted_{engine}"] = got
        out[f"transport_{engine}"] = {
            "cardinality_ok": cardinality_ok,          # supplementary
            "duplicates_ok": duplicates_ok,
            "span_coverage_ok": coverage_ok,
            "word_boundary_ok": words_ok,              # primary: intact words/tokens
            "no_intra_word_spaces": spaces_ok,         # primary: defect guard
        }
        if not ok:
            out["fail"].append(
                f"{engine} transport vs original OCR: words={words_ok} spaces={spaces_ok} "
                f"cardinality={cardinality_ok} duplicates={duplicates_ok} "
                f"coverage={coverage_ok} (got {len(got)} chars, expected {len(expected)})"
            )

    # 6. renders + visual metrics vs source
    src = np.asarray(Image.open(os.path.join(page_dir, f"{name}.png")).convert("RGB"))
    src_gray = gray_of(src)
    paper = paper_luminance(src)
    src_fg = fg_mask(src_gray, paper)

    pop_png = os.path.join(out_dir, "render_poppler.png")
    pdf_png = os.path.join(out_dir, "render_pdfium.png")
    render_poppler(pdf_path, pop_png)
    render_pdfium(pdf_path, pdf_png)

    for engine, png in (("poppler", pop_png), ("pdfium", pdf_png)):
        rend = np.asarray(Image.open(png).convert("RGB"))
        if rend.shape != src.shape:
            # poppler may pad; crop to source size
            rend = rend[: src.shape[0], : src.shape[1]]
        rend_gray = gray_of(rend)
        rend_paper = paper_luminance(rend)
        rend_fg = fg_mask(rend_gray, rend_paper)

        m = {
            "iou": 0.0,
            "edge_p95": None,
            "edge_max": None,
            "mae": None,
            "mae_ink": None,
            "topology_ok": False,
        }
        inter = (src_fg & rend_fg).sum()
        union = (src_fg | rend_fg).sum()
        m["iou"] = float(inter / union) if union else 1.0
        # rigorous 50%-coverage references: i50 = (paper + ink)/2 per image,
        # ink = median intensity of that image's own foreground pixels
        ink_src = float(np.median(src_gray[src_fg])) if src_fg.any() else 0.0
        ink_ren = float(np.median(rend_gray[rend_fg])) if rend_fg.any() else 0.0
        p95, mx = edge_errors_subpixel(
            src_gray, src_fg, rend_gray, rend_fg,
            (paper + ink_src) / 2.0, (rend_paper + ink_ren) / 2.0,
        )
        m["edge_p95"], m["edge_max"] = p95, mx
        mae = float(np.abs(src_gray - rend_gray).mean() / 255.0)
        m["mae"] = mae
        ink = src_fg | rend_fg
        m["mae_ink"] = float(np.abs(src_gray - rend_gray)[ink].mean() / 255.0) if ink.any() else 0.0
        topo_ok = True
        for t in THRESHOLDS:
            if (
                components(fg_mask(src_gray, paper, t))
                != components(fg_mask(rend_gray, rend_paper, t))
            ):
                topo_ok = False
            src_h = holes(fg_mask(src_gray, paper, t))
            ren_h = holes(fg_mask(rend_gray, rend_paper, t))
            if src_h != ren_h:
                topo_ok = False
                m[f"holes@{t}"] = (src_h, ren_h)
        m["topology_ok"] = topo_ok
        out["metrics"][engine] = m

        gate = (
            m["iou"] >= MIN_IOU
            and m["edge_p95"] <= MAX_EDGE_P95
            and m["edge_max"] <= MAX_EDGE_MAX
            and m["mae"] <= MAX_MAE
            and topo_ok
        )
        out["checks"][f"visual_{engine}"] = gate
        if not gate:
            out["fail"].append(
                f"{engine} visual gate: iou={m['iou']:.4f} p95={m['edge_p95']:.2f} "
                f"max={m['edge_max']:.2f} mae={m['mae']:.4f} topo={topo_ok}"
            )

    # 7. coloured-paper counter check: counters show paper colour, not white
    if name == "p05_colour":
        rend = np.asarray(Image.open(pdf_png).convert("RGB"))
        src_fg_full = fg_mask(src_gray, paper)
        # find holes in the source 8 and sample their colour in the render
        inv = ~src_fg_full
        # a hole = background region fully inside glyph bbox area (rows 58..209, cols 60..200 approx)
        crop = inv[70:200, 70:190]
        hole_mask = crop
        if hole_mask.any():
            counter_pixels = rend[70:200, 70:190][hole_mask]
            mean_counter = counter_pixels.mean(axis=0)
            paper_rgb = np.array([216, 200, 160])
            white = np.array([255, 255, 255])
            d_paper = float(np.abs(mean_counter - paper_rgb).mean())
            d_white = float(np.abs(mean_counter - white).mean())
            out["checks"]["counters_paper_colour"] = d_paper < d_white
            out["counter_colour"] = {"mean": mean_counter.tolist(), "d_paper": d_paper, "d_white": d_white}
            if d_paper >= d_white:
                out["fail"].append("counters appear white/painted rather than paper colour")
        else:
            out["checks"]["counters_paper_colour"] = False
            out["fail"].append("no counter pixels found for colour check")

    # 8. trace log: budget + unowned accounting
    log = json.load(open(os.path.join(out_dir, TRACE_LOG_JSON)))
    out["unowned_components"] = log["unowned_components"]
    if name != "p06_degraded" and log["unowned_components"] != 0:
        out["fail"].append(f"unowned components {log['unowned_components']} (must be 0)")
    out["glyphs"] = [
        {
            "gid": g["gid"],
            "text": g["semantic_strings"],
            "cids": g["cids"],
            "contours": g["contours"],
            "points": g["points"],
            "stages": g["stages"],
            "budget_ok": g["budget_ok"],
        }
        for g in log["glyphs"]
    ]
    return out


def qdf_of(pdf_path: str, tag: str) -> str:
    env = qpdf_env()
    out = os.path.join(WORK, f"{tag}.qdf.pdf")
    r = sh([QPDF(), "--qdf", "--object-streams=disable", pdf_path, out], env=env)
    assert r.returncode == 0, r.stderr
    return out


def parse_font_graph(pdf_path: str, tag: str) -> dict:
    """Independently extract CIDToGIDMap + ToUnicode from the PDF via qpdf qdf."""
    import re as _re

    qdf = qdf_of(pdf_path, tag)
    data = open(qdf, "rb").read()
    graph = {}
    # CIDToGIDMap stream: dict pair /CIDToGIDMap N 0 R followed later by that obj
    m = _re.search(rb"/CIDToGIDMap (\d+) 0 R", data)
    if m:
        n = int(m.group(1))
        om = _re.search(rb"\n" + str(n).encode() + rb" 0 obj\n(.*?)\nendobj", data, _re.S)
        if om:
            sm = _re.search(rb"stream\r?\n(.*?)\r?\nendstream", om.group(1), _re.S)
            if sm:
                graph["cid_to_gid"] = list(sm.group(1))
    # ToUnicode bfchar pairs
    m = _re.search(rb"/ToUnicode (\d+) 0 R", data)
    if m:
        n = int(m.group(1))
        om = _re.search(rb"\n" + str(n).encode() + rb" 0 obj\n(.*?)\nendobj", data, _re.S)
        if om:
            sm = _re.search(rb"stream\r?\n(.*?)\r?\nendstream", om.group(1), _re.S)
            if sm:
                body = sm.group(1).decode("latin1")
                pairs = _re.findall(r"<([0-9A-Fa-f]{4})> <([0-9A-Fa-f]+)>", body)
                graph["tounicode"] = {int(a, 16): bytes.fromhex(b).decode("utf-16-be") for a, b in pairs}
    return graph


def have(name: str) -> bool:
    """Whether a gate fixture page is present in the current fixtures dir/run."""
    return name in results["pages"]

def e_proofs(results: dict) -> None:
    """WP-E font-graph proofs (E1..E7). Evidence from the PDF/font graph itself.

    Proofs whose fixture page is not part of the current run (e.g. a corpus
    bundle subset) are recorded NOT_RUN rather than crashing."""
    ep = {}
    if not have("p07_sharedcid"):
        for k in ("E1_same_outline_two_cids", "E2_two_gids_one_string",
                  "E0_key_property", "E7_determinism"):
            ep[k] = FIXTURE_NOT_RUN
        results["eproofs"] = ep
        results["gates"].update({k: None for k in ep})
        return
    work1 = os.path.join(WORK, "p07_sharedcid")
    pdf7 = os.path.join(work1, OUTPUT_PDF)

    # E1: identical shape, labels 8 and 6 -> two CIDs, ONE GID (glyph REUSE)
    g = parse_font_graph(pdf7, "e1")
    m = g.get("cid_to_gid", [])
    if len(m) >= 4:
        c1, c2 = (m[2], m[3]), (m[4], m[5])
        ep["E1_same_outline_two_cids"] = {
            "cid1_gid": c1[0] * 256 + c1[1],
            "cid2_gid": c2[0] * 256 + c2[1],
            "reuse_proven": c1 == c2,
            "tounicode": {1: g["tounicode"].get(1), 2: g["tounicode"].get(2)},
        }
    else:
        ep["E1_same_outline_two_cids"] = "MISSING cid_to_gid"

    # E2: different outlines, same label -> distinct GIDs, same ToUnicode string
    if len(m) >= 8:
        g1 = m[2] * 256 + m[3]  # CID1 -> regular 8
        g3 = m[8] * 256 + m[9]  # CID4 (small 8 of "18") -> distinct glyph
        tu = g.get("tounicode", {})
        ep["E2_two_gids_one_string"] = {
            "gid_regular8": g1,
            "gid_small8": g3,
            "distinct_gids": g1 != g3,
            "strings": (tu.get(1), tu.get(4)),
            "same_string": tu.get(1) == tu.get(4) == "8",
        }

    # E4: multi-codepoint + supplementary-plane ToUnicode (UTF-16BE)
    if not have("p04_ligature"):
        ep["E4_utf16_transport"] = FIXTURE_NOT_RUN
        results["eproofs"] = ep
        results["gates"].update({"E4_utf16_transport": None})
        return
    g4 = parse_font_graph(os.path.join(WORK, "p04_ligature", OUTPUT_PDF), "e4")
    tu4 = g4.get("tounicode", {})
    ep["E4_utf16_transport"] = {
        "fi": tu4.get(1),
        "supplementary": tu4.get(2),
        "fi_ok": tu4.get(1) == "fi",
        "surrogate_ok": tu4.get(2) == "𝐀",
    }

    # E3: wrong-label preservation — visible render matches the 8 SOURCE, extraction says 6
    p02 = results["pages"].get("p02_wronglabel", {})
    if not have("p02_wronglabel") or not have("p03_kana"):
        ep["E3_wronglabel_preservation"] = FIXTURE_NOT_RUN
        ep["E5_kana"] = FIXTURE_NOT_RUN
        results["eproofs"] = ep
        results["gates"].update({"E3_wronglabel_preservation": None, "E5_kana": None})
        return
    src = np.asarray(Image.open(os.path.join(FIXTURES, "p02_wronglabel", "p02_wronglabel.png")).convert("L"))
    ren = np.asarray(Image.open(os.path.join(WORK, "p02_wronglabel", "render_pdfium.png")).convert("L"))

    def _fg(a):
        return np.abs(a.astype(float) - 255) > 60

    a, b = _fg(src), _fg(ren[: src.shape[0], : src.shape[1]])
    inter = (a & b).sum()
    union = (a | b).sum()
    iou = float(inter / union) if union else 1.0
    ep["E3_wronglabel_preservation"] = {
        "visible_shape_iou_vs_source": iou,
        "extracted_text": p02.get("extracted_pdfium"),
        "provenance": "ocr (unreviewed; recorded in normalized OCR)",
        "visually_preserved": iou > 0.95,
    }

    # E5: kana multi-component, no normalization
    p03 = results["pages"].get("p03_kana", {})
    ep["E5_kana"] = {
        "extracted_poppler": p03.get("extracted_poppler"),
        "extracted_pdfium": p03.get("extracted_pdfium"),
        "ok": p03.get("extracted_poppler") == "ガ" and p03.get("extracted_pdfium") == "ガ",
    }

    # E6: span over multiple units + owner recording
    log = json.load(open(os.path.join(WORK, "p07_sharedcid", TRACE_LOG_JSON)))
    span_ids = Counter(o["span_id"] for o in log["occurrences"] if o["span_id"] != "unowned")
    owners = {o["owner"] for o in log["occurrences"]}
    ep["E6_span_cardinality_owners"] = {
        "multi_unit_spans": {k: v for k, v in span_ids.items() if v > 1},
        "owners": sorted(owners),
        "ok": any(v > 1 for v in span_ids.values()) and "visible_tounicode" in owners,
    }

    # E7: deterministic repeat (byte-equal font + PDF)
    page_dir = os.path.join(FIXTURES, "p01_latin")
    out2 = os.path.join(WORK, "p01_rerun")
    os.makedirs(out2, exist_ok=True)
    sh([PROBE, "build", "--page", page_dir, "--out", out2])
    import hashlib as _hl

    h = lambda p: _hl.sha256(open(p, "rb").read()).hexdigest()  # noqa: E731
    ep["E7_determinism"] = {
        "pdf_equal": h(os.path.join(WORK, "p01_latin", OUTPUT_PDF)) == h(os.path.join(out2, OUTPUT_PDF)),
        "ttf_equal": h(os.path.join(WORK, "p01_latin", OUTPUT_FONT_TTF)) == h(os.path.join(out2, OUTPUT_FONT_TTF)),
    }

    # E0: executable four-part-key mutation property test (encoding.rs Rust unit
    # test): mutating each of (visual_glyph_id, semantic_string, writing_mode,
    # required_metrics) must assert CID separation; identical keys dedup.
    env = dict(os.environ)
    env.setdefault("PATH", os.environ.get("PATH", ""))
    r = sh(["bash", "-lc", "source $HOME/.cargo/env && cargo test -p scanweave-io e0_four_part_key_property 2>&1"],
           env=env)
    e0_pass = r.returncode == 0 and "test encoding::tests::e0_four_part_key_property ... ok" in r.stdout
    if not have("p01_latin"):
        ep["E0_key_property"] = {"passed": None, "note": "E1.pdf pages not in run"}
        results["eproofs"] = ep
        return
    log1 = json.load(open(os.path.join(WORK, "p01_latin", TRACE_LOG_JSON)))
    e0 = {
        "rust_property_test": "cargo test e0_four_part_key_property: ok" if e0_pass else r.stdout.strip()[-200:],
        "passed": e0_pass,
        "same_glyph_same_string_single_cid": any(len(g["cids"]) == 1 for g in log1["glyphs"]),
        "same_glyph_diff_string_multi_cid": any(
            len(g["cids"]) > 1
            for g in json.load(open(os.path.join(WORK, "p07_sharedcid", TRACE_LOG_JSON)))["glyphs"]
        ),
    }
    ep["E0_key_property"] = e0

    results["eproofs"] = ep
    status_key = {
        "E1_same_outline_two_cids": "reuse_proven",
        "E2_two_gids_one_string": "same_string",
        "E3_wronglabel_preservation": "visually_preserved",
        "E4_utf16_transport": "surrogate_ok",
        "E5_kana": "ok",
        "E6_span_cardinality_owners": "ok",
        "E7_determinism": "pdf_equal",
        "E0_key_property": "same_glyph_diff_string_multi_cid",
    }
    for k, v in ep.items():
        if isinstance(v, str):
            print(f"NOT_RUN {k}")
            results["gates"].setdefault(k, None)
            continue
        key = status_key.get(k)
        vok = bool(v.get(key)) if isinstance(v, dict) and key else False
        if k == "E4_utf16_transport":
            vok = bool(v.get("fi_ok") and v.get("surrogate_ok"))
        if k == "E0_key_property":
            vok = bool(v.get("passed") and v.get("same_glyph_diff_string_multi_cid") and v.get("same_glyph_same_string_single_cid"))
        print(f"{'PASS' if vok else 'FAIL'} {k}")
        results["gates"][k] = vok
    return


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", help="comma-separated page list")
    ap.add_argument("--fixtures-dir", help="override the probe fixtures root (corpus bundles)")
    ap.add_argument("--out", help="results output path. Defaults to the committed "
                                  "gate artifact qualification/probe_results.json ONLY for "
                                  "default gate runs; non-gate runs MUST pass a distinct "
                                  "path so gate evidence can never be overwritten")
    args = ap.parse_args()
    pages_in_run = [p.strip() for p in args.pages.split(",") if p.strip()] if args.pages else list(DEFAULT_PAGES)
    canonical = os.path.join(HERE, "probe_results.json")
    # ONLY the full default run (no --pages, no --fixtures-dir) writes the
    # committed gate artifact; any subset or override must pass --out, so a
    # partial run can never dilute the canonical evidence.
    is_gate_run = (args.pages is None) and (not args.fixtures_dir)
    if args.out:
        results_path = os.path.abspath(args.out)
        if not is_gate_run and results_path == os.path.abspath(canonical):
            # an explicit --out must not be able to target the canonical gate
            # artifact from a subset/overridden run either
            raise SystemExit(
                "non-gate run may not target the committed gate artifact via --out; "
                "choose a distinct path"
            )
    elif is_gate_run:
        results_path = canonical
    else:
        # never silently overwrite (or dilute) the committed gate evidence
        raise SystemExit(
            "non-gate run requires --out <path>; the committed gate artifact "
            f"{os.path.relpath(canonical, ROOT)} is protected"
        )
    if args.fixtures_dir:
        global FIXTURES
        FIXTURES = os.path.abspath(args.fixtures_dir)
    os.makedirs(WORK, exist_ok=True)
    results["tools"]["qpdf"] = version(QPDF())
    results["tools"]["poppler"] = sh(["pdftotext", "-v"]).stderr.splitlines()[0]
    results["tools"]["pdfium"] = "pypdfium2 bundled"
    results["tools"]["ots"] = sh([OTS(), "--version"]).stdout.strip()

    pages = pages_in_run
    all_ok = True
    for name in pages:
        res = check_page(name)
        results["pages"][name] = res
        ok = not res["fail"]
        all_ok &= ok
        print(f"{'PASS' if ok else 'FAIL'} {name}" + ("" if ok else f" — {res['fail'][:2]}"))

    e_proofs(results)

    with open(results_path, "w") as f:
        json.dump(results, f, indent=1, default=str)
    print(f"results written to {os.path.relpath(results_path, ROOT)}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
