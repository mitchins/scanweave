#!/usr/bin/env python3
"""Attribute a PDF's stream bytes to pages: each stream reachable from a page is split evenly across the pages reaching it.
Usage: page_attribution.py <pdf> [page...]  -> JSON {page: {total, raster, font, other}}"""
import sys, json, collections, pikepdf
pdf = pikepdf.open(sys.argv[1]); reach = []
def walk(o, seen, acc, kind=None):
    if isinstance(o, pikepdf.Stream) or isinstance(o, pikepdf.Dictionary) or isinstance(o, pikepdf.Array):
        if o.is_indirect:
            if o.objgen in seen: return
            seen.add(o.objgen)
        if isinstance(o, pikepdf.Stream):
            k = 'raster' if o.get('/Subtype') == '/Image' else kind or 'other'
            acc[o.objgen] = (len(o.read_raw_bytes()), k)
        items = o.items() if not isinstance(o, pikepdf.Array) else enumerate(o)
        for key, v in items:
            if key in ('/Parent', '/P'): continue
            nk = 'font' if key in ('/FontFile', '/FontFile2', '/FontFile3', '/ToUnicode', '/CIDSet', '/CIDToGIDMap') else kind
            if key == '/Font': nk = 'font'
            walk(v, seen, acc, nk)
for pg in pdf.pages:
    acc = {}; walk(pg.obj, set(), acc); reach.append(acc)
count = collections.Counter(k for acc in reach for k in acc)
pages = [int(x) for x in sys.argv[2:]] or range(len(pdf.pages)); res = {}
for i in pages:
    t = collections.Counter()
    for k, (n, kind) in reach[i].items(): t[kind] += n / count[k]; t['total'] += n / count[k]
    res[i] = {k: round(v) for k, v in t.items()}
print(json.dumps(res))
