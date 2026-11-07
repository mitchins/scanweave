#!/usr/bin/env python3
"""ACR-06 CP3: where each arm's bytes go, per page.

Every stream reachable from a page is split evenly across the pages that reach it
(shared fonts are amortized). Image streams are classified by how they are drawn: the
content-stream transform (q/Q/cm, form matrices) gives each placed image's area as a
fraction of the page. Classes:
  page_raster   image covering >= 50% of the page (background or whole-page layer)
  patch_raster  smaller placed image (raster fallback crops, exception regions)
  mask          image used as /SMask or /Mask, or an /ImageMask stencil (MRC foreground)
  font          font programs and their CMaps/widths/CIDSets
  content       page and form content streams (text and vector operators)
  other         every other stream
File-structure overhead (xref, dictionaries, non-stream objects) is the file size minus
all stream bytes, attributed to pages by their share of stream bytes.
Usage: bytes.py OUT.json NAME=PDF [NAME=PDF ...]"""
import sys, json, collections
from pathlib import Path
import pikepdf

FONT_KEYS = {"/FontFile", "/FontFile2", "/FontFile3", "/ToUnicode", "/CIDSet", "/CIDToGIDMap", "/W"}


def mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return [a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, e * A + f * C + E, e * B + f * D + F]


def placements(xobj_owner, ctm, out, depth=0):
    """Map image objgen -> list of placed areas (pt^2) by replaying q/Q/cm/Do."""
    if depth > 8:
        return
    res = xobj_owner.get("/Resources", {})
    xobjs = res.get("/XObject", {}) if res is not None else {}
    stack, m = [], list(ctm)
    for operands, op in pikepdf.parse_content_stream(xobj_owner):
        o = str(op)
        if o == "q":
            stack.append(list(m))
        elif o == "Q":
            m = stack.pop() if stack else list(ctm)
        elif o == "cm":
            m = mul([float(v) for v in operands], m)
        elif o == "Do":
            x = xobjs.get(str(operands[0])) if xobjs is not None else None
            if x is None:
                continue
            if x.get("/Subtype") == "/Image":
                out[x.objgen].append(abs(m[0] * m[3] - m[1] * m[2]))
            elif x.get("/Subtype") == "/Form":
                fm = [float(v) for v in x.get("/Matrix", [1, 0, 0, 1, 0, 0])]
                placements(x, mul(fm, m), out, depth + 1)


def classify_page(pdf, pg):
    """objgen -> (bytes, class, detail) for every stream reachable from the page."""
    mb = [float(v) for v in pg.mediabox]
    page_area = (mb[2] - mb[0]) * (mb[3] - mb[1])
    placed = collections.defaultdict(list)
    placements(pg, [1, 0, 0, 1, 0, 0], placed)
    masks = set()
    acc = {}

    def walk(o, seen, kind=None):
        if not isinstance(o, (pikepdf.Stream, pikepdf.Dictionary, pikepdf.Array)):
            return
        if o.is_indirect:
            if o.objgen in seen:
                return
            seen.add(o.objgen)
        if isinstance(o, pikepdf.Stream):
            n = len(o.read_raw_bytes())
            if o.get("/Subtype") == "/Image":
                f = o.get("/Filter")
                f = "+".join(str(v) for v in f) if isinstance(f, pikepdf.Array) else (str(f) if f is not None else "none")
                for key in ("/SMask", "/Mask"):
                    if isinstance(o.get(key), pikepdf.Stream):
                        masks.add(o.get(key).objgen)
                area = max(placed.get(o.objgen, [0.0]) or [0.0])
                if o.get("/ImageMask", False) or o.objgen in masks:
                    cls = "mask"
                elif area >= 0.5 * page_area:
                    cls = "page_raster"
                else:
                    cls = "patch_raster"
                acc[o.objgen] = [n, cls, dict(filter=f, w=int(o.Width), h=int(o.Height), bpc=int(o.get("/BitsPerComponent", 1)), area_frac=round(area / page_area, 4), eff_dpi=round(int(o.Width) * 72 / ((area * (int(o.Width) / max(int(o.Height), 1))) ** 0.5) if area else 0, 1))]
            else:
                cls = kind or ("content" if o.get("/Subtype") == "/Form" else "other")
                acc[o.objgen] = [n, cls, None]
        items = o.items() if not isinstance(o, pikepdf.Array) else enumerate(o)
        for key, v in items:
            if key in ("/Parent", "/P"):
                continue
            nk = kind
            if key in FONT_KEYS or key == "/Font" or key == "/DescendantFonts" or key == "/FontDescriptor":
                nk = "font"
            elif key == "/Contents":
                nk = "content"
            walk(v, seen, nk)

    walk(pg.obj, set())
    for g in masks:  # a mask reached before its parent image was classified
        if g in acc:
            acc[g][1] = "mask"
    return acc


def analyse(path):
    pdf = pikepdf.open(path)
    pages = [classify_page(pdf, pg) for pg in pdf.pages]
    reach = collections.Counter(g for acc in pages for g in acc)
    stream_total = sum(len(o.read_raw_bytes()) for o in pdf.objects if isinstance(o, pikepdf.Stream))
    size = Path(path).stat().st_size
    overhead = max(size - stream_total, 0)
    out = []
    for acc in pages:
        t = collections.Counter(); images = []
        for g, (n, cls, detail) in acc.items():
            t[cls] += n / reach[g]
            if detail is not None:
                detail = dict(detail, bytes=n, cls=cls, shared_by=reach[g]); images.append(detail)
        out.append(dict(bytes={k: round(v) for k, v in t.items()}, images=images))
    attributed = sum(sum(p["bytes"].values()) for p in out) or 1
    for p in out:
        p["bytes"]["structure"] = round(overhead * sum(p["bytes"].values()) / attributed)
    return dict(file_bytes=size, stream_bytes=stream_total, pages=out)


if __name__ == "__main__":
    res = {}
    for arg in sys.argv[2:]:
        name, path = arg.split("=", 1)
        res[name] = dict(path=path, **analyse(path))
        tot = collections.Counter()
        for p in res[name]["pages"]:
            tot.update(p["bytes"])
        res[name]["totals"] = dict(tot)
        print(name, res[name]["file_bytes"], dict(tot))
    Path(sys.argv[1]).write_text(json.dumps(res, indent=1) + "\n")
