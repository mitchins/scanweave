#!/usr/bin/env python3
"""Regression controls for HIGH reliability findings in qualification tools."""
import importlib.util
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
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
                    with patch.object(module.ImageFont, "truetype", return_value=font):
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
