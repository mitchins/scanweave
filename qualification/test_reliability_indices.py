#!/usr/bin/env python3
"""Regression controls for HIGH reliability findings in qualification tools."""
import importlib.util
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    with patch.object(sys, "path", [str(path.parent), *sys.path]):
        spec.loader.exec_module(module)
    return module


class IndexRegressionTests(unittest.TestCase):
    def test_boundary_coordinates_include_empty_and_disconnected_masks(self):
        module = load_module("visual_indices", HERE / "characterize_visuals.py")
        masks = [np.zeros((5, 7), dtype=bool), np.ones((5, 7), dtype=bool)]
        disconnected = np.zeros((5, 7), dtype=bool)
        disconnected[1, 2] = disconnected[3, 5] = True
        masks.append(disconnected)
        for mask in masks:
            with self.subTest(mask=mask.tolist()):
                expected = []
                for y, x in np.ndindex(mask.shape):
                    interior = all(mask[(y + dy) % mask.shape[0], (x + dx) % mask.shape[1]]
                                   for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                    if mask[y, x] and not interior:
                        expected.append([x + 0.5, y + 0.5])
                np.testing.assert_array_equal(module.boundary_points_mask(mask),
                                              np.array(expected).reshape(-1, 2))

    def test_rendered_ink_crop_and_blank_glyph_are_unchanged(self):
        font = ImageFont.load_default(size=16)
        for directory in ("m1c", "m1c_r2"):
            module = load_module("crop_" + directory,
                                 HERE / "experiments" / directory / "run_ablation.py"
                                 if directory == "m1c" else HERE / "experiments" / directory / "run.py")
            for glyph in ("8", "g", " "):
                with self.subTest(directory=directory, glyph=glyph):
                    with patch.object(ImageFont, "truetype", return_value=font):
                        actual, origin = module.render_glyph("unused-font", glyph, 300)
                    px = int(8 * 300 / 72)
                    pad = px * 2
                    left, top, right, bottom = font.getbbox(glyph)
                    image = Image.new("L", (max(1, right-left)+pad*2,
                                             max(1, bottom-top)+pad*2), 255)
                    ImageDraw.Draw(image).text((pad-left, pad-top), glyph, font=font, fill=0)
                    samples = (255.0-np.asarray(image, dtype=np.float32))/255.0
                    positions = [(y, x) for y, x in np.ndindex(samples.shape) if samples[y, x] > 0]
                    if positions:
                        ys, xs = zip(*positions)
                        x0, x1, y0, y1 = min(xs), max(xs)+1, min(ys), max(ys)+1
                    else:
                        y0, x0 = 0, 0
                        y1, x1 = samples.shape
                    self.assertEqual(tuple(origin), (x0, y0))
                    np.testing.assert_array_equal(actual, samples[y0:y1, x0:x1])

    def test_embedded_outline_bounds_are_measured_from_actual_ink(self):
        module = load_module("outline_indices", HERE / "characterize_visuals.py")
        font = ImageFont.load_default(size=16)
        with patch.object(ImageFont, "truetype", return_value=font):
            result = module.char_c_outline_ground_truth()["p02_wronglabel"]
        expected = Image.new("L", (200, 200), 255)
        ImageDraw.Draw(expected).text((10, 10), "8", font=font, fill=0)
        ink = [(y, x) for y, x in np.ndindex((200, 200)) if expected.getpixel((x, y)) < 128]
        ys, xs = zip(*ink)
        self.assertEqual(result["outline_render_ink"], len(ink))
        self.assertEqual(result["bbox"], [min(xs), min(ys), max(xs), max(ys)])

    def test_oracle_indices_preserve_source_coordinates(self):
        module = load_module("oracle_indices", HERE / "experiments" / "m1gx" / "trial.py")
        pixels = np.full((20, 20), 255, dtype=np.uint8)
        pixels[6:9, 7:11] = 90
        record = {"text": "e", "bbox": [0, 0, 20, 20]}
        self.assertEqual(module.oracle_ink_box(pixels, record), [7, 6, 11, 9])
        self.assertEqual(module.oracle_ink_box(np.full_like(pixels, 255), record), [5, 5, 15, 15])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "oracle").mkdir()
            Image.fromarray(pixels).save(root / "oracle" / "page00.png")
            fontpath = root / "rectangle.ttf"
            builder = FontBuilder(1000, isTTF=True)
            builder.setupGlyphOrder([".notdef", "e"])
            builder.setupCharacterMap({ord("e"): "e"})
            empty = TTGlyphPen(None)
            glyph = TTGlyphPen(None)
            glyph.moveTo((0, 0))
            glyph.lineTo((10, 0))
            glyph.lineTo((10, 10))
            glyph.lineTo((0, 10))
            glyph.closePath()
            builder.setupGlyf({".notdef": empty.glyph(), "e": glyph.glyph()})
            builder.setupHorizontalMetrics({".notdef": (600, 0), "e": (600, 0)})
            builder.setupHorizontalHeader(ascent=800, descent=-200)
            builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
            builder.setupNameTable({"familyName": "Index test", "styleName": "Regular"})
            builder.setupPost()
            builder.setupMaxp()
            builder.save(fontpath)
            with patch.object(module, "BASE", root):
                paths = module.oracle_paths(0, {"font": str(fontpath), "records": [record]}, 20, 20)
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0][1], ["1.6800 2.6400 m", "2.6400 2.6400 l",
                                            "2.6400 3.3600 l", "1.6800 3.3600 l", "h"])

    def test_oracle_bounds_do_not_require_optional_donor_tracing_package(self):
        with patch.dict(sys.modules, {"skimage": None}):
            module = load_module("oracle_without_skimage", HERE / "experiments" / "m1gx" / "trial.py")
            # Existing index/accounting helpers stay usable without installing a
            # tracing package. Actual donor tracing still requires that package.
            with self.assertRaises(ModuleNotFoundError):
                module.trace_donor(np.zeros((4, 4, 3)), [0, 0, 4, 4], 128)


class ReferenceRunnerTests(unittest.TestCase):
    runner = HERE / "clearscan_competitive" / "reference-runner.sh"

    def test_bash_syntax(self):
        subprocess.run(["bash", "-n", str(self.runner)], check=True, capture_output=True)

    def test_actual_late_runner_conditions(self):
        # Execute the actual changed condition expressions without driving Wine.
        # These are developer-owned shell source, never document/CLI data.
        conditions = re.findall(r"\[\[.*?\]\]", self.runner.read_text())
        cases = [
            ('[[ "$TITLE" = "Adobe Acrobat Pro" ]]', "TITLE",
             [("Adobe Acrobat Pro", 0), ("Adobe*", 1), ("", 1)]),
            ('[[ "$STYLE" = "clearscan" ]]', "STYLE",
             [("clearscan", 0), ("clear*", 1), ("searchable-exact", 1)]),
            ('[[ "$CURRENT_SIZE" = "$LAST_SIZE" ]]', "CURRENT_SIZE",
             [("120", 0), ("12*", 1), ("121", 1)]),
            ('[[ "$STABLE" -ge 2 ]]', "STABLE",
             [("0", 1), ("1", 1), ("2", 0), ("10", 0)]),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "runner-condition.sh"
            for condition, variable, values in cases:
                self.assertIn(condition, conditions)
                actual = conditions[conditions.index(condition)]
                script.write_text("if " + actual + "; then exit 0; else exit 1; fi\n")
                for value, status in values:
                    with self.subTest(condition=condition, value=value):
                        environment = dict(os.environ, LAST_SIZE="120")
                        environment[variable] = value
                        result = subprocess.run(["bash", str(script)], env=environment,
                                                capture_output=True, text=True)
                        self.assertEqual(result.returncode, status, result.stderr)

    def test_rejects_missing_arguments_and_missing_input(self):
        result = subprocess.run(["bash", str(self.runner)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("usage:", result.stderr)
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run(["bash", str(self.runner), str(Path(temporary)/"absent.pdf"),
                                     str(Path(temporary)/"output.pdf")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("input not found:", result.stderr)

    def test_rejects_unknown_style_with_space_and_glob_in_filename(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "input [*] -document.pdf"
            source.write_bytes(b"test input; no Acrobat invocation")
            result = subprocess.run(["bash", str(self.runner), str(source),
                                     str(Path(temporary)/"output.pdf"), "invalid"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("unknown output style:", result.stderr)


if __name__ == "__main__":
    unittest.main()
