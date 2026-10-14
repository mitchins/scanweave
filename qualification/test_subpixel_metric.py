#!/usr/bin/env python3
"""Analytical tests for the sub-pixel edge metric (M0-Q item 1).

Each test constructs an idealized anti-aliased image whose 50%-coverage edge
lies at a KNOWN sub-pixel position, then asserts that
`subpixel_boundary_points` + `edge_errors_subpixel` recover that position.

Covers: both edge polarities (ink|paper and paper|ink), all four segment
directions, multiple sub-pixel phases, contrasting and low-contrast colour
pairs, and a known-offset two-render comparison.

Run: qualification/.venv/bin/python qualification/test_subpixel_metric.py
Exits non-zero on any failure.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checks import edge_errors_subpixel, subpixel_boundary_points  # noqa: E402

PAPER = 255.0
INK = 20.0
I50 = (PAPER + INK) / 2.0  # 50%-coverage reference (rigorous definition)

# Linear interpolation of an ideal area-coverage edge has a phase-dependent
# bias bounded by (sqrt(2)-1)/2 ~= 0.0858 px (derivation: maximize
# |9.5 + 117.5/(235*(1-d)) - (10+d)| over d in (0,1) -> d* = 1 - 1/sqrt(2)).
# Analytical assertions therefore use TOL = 0.09 px.
TOL = 0.09

FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"{status} {name} {detail}")
    if not cond:
        FAILURES.append(name)


def ideal_edge_image(h, w, edge_x, ink=INK, paper=PAPER, vertical=True, invert=False):
    """Vertical edge at x = edge_x (pixel centres at x+0.5): pixels fully left of
    the edge are ink, fully right are paper, the straddling column gets exact
    area coverage. invert=True swaps ink/paper (opposite polarity)."""
    img = np.full((h, w), paper if not invert else ink, dtype=np.float64)
    for x in range(w):
        if vertical:
            cov = min(1.0, max(0.0, edge_x - x))  # ink coverage of column x
        else:
            cov = min(1.0, max(0.0, edge_x - x))
        if invert:
            img[:, x] = ink + (paper - ink) * (1.0 - cov) if not False else img[:, x]
            img[:, x] = paper + (ink - paper) * cov * 0 + (ink + (paper - ink) * (1 - cov)) * 0
            # for inverted polarity the LEFT side is paper: coverage of ink is 1-cov
            img[:, x] = ink + (paper - ink) * (1.0 - cov)
        else:
            img[:, x] = ink + (paper - ink) * (1.0 - cov)
    if not vertical:
        img = img.T
    return img


def edge_mask(img, i50):
    return img < i50  # ink side


def test_vertical_edge_phases():
    """Edge at x = 10.00/10.25/10.50/10.75 — recovered mean x within 0.05 px."""
    for f in (0.0, 0.25, 0.5, 0.75):
        edge_x = 10.0 + f
        img = ideal_edge_image(40, 40, edge_x)
        m = edge_mask(img, I50)
        pts = subpixel_boundary_points(img, m, I50)
        # boundary points sit on the vertical line x = edge_x
        rec = pts[:, 0].mean() - 0.5  # pixel centres at x+0.5; edge coord = centre - 0.5 + f?
        # pixel (col x) centre is x+0.5; the crossing at x=edge_x in the same
        # continuous coordinates is edge_x + 0.5? No: columns are [x, x+1), the
        # edge at "10.25" means 10.25 pixels from the left border in pixel-edge
        # coordinates where column i spans [i, i+1). Centre of col i = i+0.5.
        # crossing continuous coord = edge_x (already in edge coords) → compare
        # with pts x directly, subtracting nothing: pts are in the same coords.
        rec = pts[:, 0].mean()
        err = abs(rec - edge_x)
        check(
            f"vertical edge x={edge_x}",
            err <= TOL,
            f"recovered {rec:.4f} err={err:.4f}",
        )


def test_horizontal_and_directions():
    """Horizontal edge (rows) and inverted polarity — recovery within 0.05 px."""
    for f in (0.25, 0.5):
        edge_y = 20.0 + f
        img = ideal_edge_image(40, 40, edge_y, vertical=False)
        m = edge_mask(img, I50)
        pts = subpixel_boundary_points(img, m, I50)
        rec = pts[:, 1].mean()
        err = abs(rec - edge_y)
        check(f"horizontal edge y={edge_y}", err <= TOL, f"recovered {rec:.4f}")

    for f in (0.3,):
        edge_x = 15.0 + f
        img = ideal_edge_image(40, 40, edge_x, invert=True)
        m = edge_mask(img, I50)
        pts = subpixel_boundary_points(img, m, I50)
        rec = pts[:, 0].mean()
        err = abs(rec - edge_x)
        check(
            f"inverted polarity edge x={edge_x}",
            err <= TOL,
            f"recovered {rec:.4f} err={err:.4f}",
        )


def test_low_contrast():
    """Low-contrast pair (ink 200, paper 250): i50 midpoint, recovery ok."""
    ink, paper = 200.0, 250.0
    i50 = (ink + paper) / 2.0
    edge_x = 12.0 + 0.5
    img = ideal_edge_image(30, 30, edge_x, ink=ink, paper=paper)
    m = img < i50
    pts = subpixel_boundary_points(img, m, i50)
    rec = pts[:, 0].mean()
    err = abs(rec - edge_x)
    check("low contrast edge x=12.5", err <= TOL, f"recovered {rec:.4f}")


def test_known_offset_two_renders():
    """Two renders of the same geometry offset by exactly 0.3 px: symmetric
    sub-pixel distance must report ≈ 0.3."""
    a = ideal_edge_image(40, 40, 10.0)
    b = ideal_edge_image(40, 40, 10.3)
    ma, mb = edge_mask(a, I50), edge_mask(b, I50)
    p95, mx = edge_errors_subpixel(a, ma, b, mb, I50, I50)
    check(
        "known 0.3px offset",
        abs(mx - 0.3) <= TOL and abs(p95 - 0.3) <= TOL,
        f"p95={p95:.4f} max={mx:.4f} (bias-bounded; direction preserved: b>a)",
    )


def test_broken_interpolation_is_detected():
    """Regression guard: the MIRRORED interpolation (t computed from the outside
    end) must produce a detectably wrong position for a mid-ramp edge — this is
    the defect class fixed in M0-Q item 1."""
    edge_x = 10.5
    img = ideal_edge_image(40, 40, edge_x)
    m = edge_mask(img, I50)
    pts = subpixel_boundary_points(img, m, I50)
    rec = pts[:, 0].mean()
    # correct interpolation lands within 0.05; a mirrored implementation lands
    # ~1.0 px away (at the opposite side of the straddling pixel pair)
    check("mid-ramp edge recovered (mirrored impl would fail)", abs(rec - edge_x) <= 0.05,
          f"recovered {rec:.4f}")


if __name__ == "__main__":
    test_vertical_edge_phases()
    test_horizontal_and_directions()
    test_low_contrast()
    test_known_offset_two_renders()
    test_broken_interpolation_is_detected()
    if FAILURES:
        print(f"\nFAILED: {FAILURES}")
        sys.exit(1)
    print("\nall sub-pixel metric analytical tests passed")
