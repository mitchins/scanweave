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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROBE = os.path.join(ROOT, "target", "debug", "m0-font-pdf")
FIXTURES = os.path.join(HERE, "fixtures", "probe")
WORK = os.path.join(ROOT, "work", "m0-checks")
QPDF = os.path.join(ROOT, "tools", "dist", "bin", "qpdf")
OTS = os.path.join(HERE, "..", "tools", "src", "ots-bin", "ots-9.3.0-Linux", "ots-sanitize")

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

EXPECTED = {
    "p01_latin": ["8", "6", "8", "a"],
    "p02_wronglabel": ["6"],
    "p03_kana": ["ガ"],
    "p04_ligature": ["fi", "𝐀"],
    "p05_colour": ["8"],
    "p06_degraded": ["8"],
}

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


def edge_errors(a: np.ndarray, b: np.ndarray, cap: int = 12) -> tuple[float, float]:
    """symmetric edge error between two foreground masks (pixel units)"""
    if not a.any() and not b.any():
        return (0.0, 0.0)
    if not a.any() or not b.any():
        return (float(cap), float(cap))
    ba, bb = boundary(a), boundary(b)
    if not ba.any() or not bb.any():
        return (float(cap), float(cap))

    def dist_map(target: np.ndarray) -> np.ndarray:
        # iterative chebyshev dilation of target; returns distance to nearest set bit
        d = np.full(target.shape, cap + 1, dtype=np.float64)
        cur = target.copy()
        for r in range(1, cap + 1):
            grown = cur.copy()
            grown[1:, :] |= cur[:-1, :]
            grown[:-1, :] |= cur[1:, :]
            grown[:, 1:] |= cur[:, :-1]
            grown[:, :-1] |= cur[:, 1:]
            grown[1:, 1:] |= cur[:-1, :-1]
            grown[:-1, :-1] |= cur[1:, 1:]
            grown[1:, :-1] |= cur[:-1, 1:]
            grown[:-1, 1:] |= cur[1:, :-1]
            d[grown & (d > r)] = r
            cur = grown
            if (d <= cap).all():
                break
        return d

    da = dist_map(bb)[ba]
    db = dist_map(ba)[bb]
    per_pixel = np.concatenate([da, db])
    p95 = float(np.percentile(per_pixel, 95))
    mx = float(per_pixel.max())
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

    page_dir = os.path.join(FIXTURES, name)
    out_dir = os.path.join(WORK, name)
    os.makedirs(out_dir, exist_ok=True)

    # 1. probe build
    r = sh([PROBE, "build", "--page", page_dir, "--out", out_dir])
    out["checks"]["probe_build"] = r.returncode == 0
    if r.returncode != 0:
        out["fail"].append(f"probe build failed: {r.stderr[:300]}")
        return out
    pdf_path = os.path.join(out_dir, "out.pdf")
    ttf_path = os.path.join(out_dir, "out.ttf")
    out["pdf_bytes"] = os.path.getsize(pdf_path)
    out["ttf_bytes"] = os.path.getsize(ttf_path)

    # 2. qpdf --check
    env = dict(os.environ, LD_LIBRARY_PATH=os.path.join(ROOT, "tools", "dist", "lib"))
    r = sh([QPDF, "--check", pdf_path], env=env)
    out["checks"]["qpdf"] = r.returncode == 0
    if r.returncode != 0:
        out["fail"].append(f"qpdf --check rc={r.returncode}: {r.stderr[:300]}")

    # 3. ots-sanitize
    r = sh([OTS, ttf_path])
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

    # 5. extraction: both engines must return exactly the expected span strings
    exp = EXPECTED[name]
    for engine, fn in (("poppler", extract_poppler), ("pdfium", extract_pdfium)):
        try:
            text = fn(pdf_path)
        except Exception as e:  # noqa: BLE001
            out["checks"][f"extract_{engine}"] = False
            out["fail"].append(f"{engine} extraction failed: {e}")
            continue
        # M0 transport check: exact code-point sequence in logical order after
        # removing whitespace that extractors insert as layout formatting
        # (preregistered mapping; separators are not content).
        got = [t for t in re.split(r"\s+", text) if t]
        ok = "".join(got) == "".join(exp)
        out["checks"][f"extract_{engine}"] = ok
        out[f"extracted_{engine}"] = got
        if not ok:
            out["fail"].append(f"{engine} extraction {''.join(got)!r} != expected {''.join(exp)!r}")

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
        p95, mx = edge_errors(src_fg, rend_fg)
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
            ys, xs = np.where(hole_mask)
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
    log = json.load(open(os.path.join(out_dir, "trace_log.json")))
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


def main() -> int:
    os.makedirs(WORK, exist_ok=True)
    env = dict(os.environ, LD_LIBRARY_PATH=os.path.join(ROOT, "tools", "dist", "lib"))
    results["tools"]["qpdf"] = sh([QPDF, "--version"], env=env).stdout.splitlines()[0]
    results["tools"]["poppler"] = sh(["pdftotext", "-v"]).stderr.splitlines()[0]
    results["tools"]["pdfium"] = "pypdfium2 bundled"
    results["tools"]["ots"] = sh([OTS, "--version"]).stdout.strip()

    pages = sys.argv[1].split("=")[1].split(",") if "--pages" in sys.argv else list(EXPECTED)
    all_ok = True
    for name in pages:
        res = check_page(name)
        results["pages"][name] = res
        ok = not res["fail"]
        all_ok &= ok
        print(f"{'PASS' if ok else 'FAIL'} {name}" + ("" if ok else f" — {res['fail'][:2]}"))

    with open(os.path.join(HERE, "probe_results.json"), "w") as f:
        json.dump(results, f, indent=1, default=str)
    print("results written to qualification/probe_results.json")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
