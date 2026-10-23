"""Synthetic contracts for research fitting; no frozen artifact regeneration."""

import unittest
from unittest.mock import patch

import numpy as np

from qualification.font03 import consensus as c
from qualification.font03 import probe_pdf


def ring():
    yy, xx = np.indices((64, 64))
    r = np.hypot(xx - 32, yy - 34)
    return np.minimum(np.clip(12.5 - r, 0, 1), np.clip(r - 6.5, 0, 1))


class ConsensusContracts(unittest.TestCase):
    def test_identity_transforms_preserve_line_frame(self):
        image = ring()
        np.testing.assert_array_equal(c.warp(image, [0, 0, 1]), image)
        np.testing.assert_array_equal(c.affine_warp(image, [0, 0, 0, 1, 1]), image)
        np.testing.assert_array_equal(c.affine_forward([0, 0, 0, 1, 1]), np.eye(3))

    def test_registration_is_bounded_and_reduces_error(self):
        image = ring()
        moved = c.warp(image, [0.7, -0.4, 1.01])
        params, aligned = c.register(image, moved)
        self.assertLess(
            np.square(aligned - image).sum(), np.square(moved - image).sum()
        )
        self.assertTrue(np.all(np.abs(params[:2]) <= 2))
        self.assertGreaterEqual(params[2], 0.98)
        self.assertLessEqual(params[2], 1.02)

    def test_affine_registration_cannot_use_shear(self):
        image = ring()
        params, _ = c.register_affine(image, image)
        self.assertEqual(len(params), 5)
        np.testing.assert_allclose(params, [0, 0, 0, 1, 1], atol=1e-8)

    def test_huber_fit_limits_one_damaged_impression(self):
        good = ring()
        bad = np.zeros_like(good)
        field, uncertainty = c.robust_template([good, good, good, bad])
        self.assertLess(
            np.abs(field - good).sum(), np.abs((3 * good + bad) / 4 - good).sum()
        )
        self.assertEqual(uncertainty.shape, good.shape)
        self.assertTrue(np.all((field >= 0) & (field <= 1)))

    def test_structural_gate_rejects_dot_to_sliver(self):
        dot, sliver = np.zeros((64, 64)), np.zeros((64, 64))
        dot[30:35, 30:35] = 1
        sliver[24:41, 32:33] = 1
        reasons = c.geometry_rejections(dot, sliver)
        self.assertIn("width", reasons)
        self.assertIn("elongation", reasons)

    def test_counter_change_is_not_hidden_by_area(self):
        image = ring()
        filled = c.ndimage.binary_fill_holes(image > 0.5).astype(float)
        self.assertIn("topology", c.geometry_rejections(image, filled))
        self.assertGreater(
            c.structural_distances(image, filled)["counter_difference"], 0
        )

    def test_empty_ink_abstains(self):
        self.assertEqual(
            c.geometry_rejections(ring(), np.zeros((64, 64))), ["empty_ink"]
        )
        self.assertIsNone(c.structural_distances(ring(), np.zeros((64, 64))))

    def test_complete_link_does_not_chain_or_rewrite_character(self):
        images = [np.full((2, 2), i) for i in range(3)]

        def compare(a, b, limits):
            passes = abs(float(a[0, 0] - b[0, 0])) <= 1
            return passes, np.array([0, 0, 1]), 0.9, []

        with patch.object(c, "compatible", side_effect=compare):
            groups, _ = c.complete_groups(images, ["e", "e", "e"])
            self.assertEqual(groups, [[0, 1], [2]])
            groups, _ = c.complete_groups(images, ["e", "c", "e"])
            self.assertEqual(groups, [[0], [1], [2]])

    def test_directional_success_cannot_admit_an_asymmetric_pair(self):
        first, second = ring(), ring()
        with patch.object(
            c,
            "compatible",
            side_effect=[
                (True, np.array([0, 0, 1]), 0.9, []),
                (False, np.array([0, 0, 1]), 0.7, ["coverage"]),
            ],
        ):
            groups, pairs = c.complete_groups([first, second], ["e", "e"])
        self.assertEqual(groups, [[0], [1]])
        self.assertEqual(pairs[0, 1][2], 0.7)
        self.assertIn("reverse:coverage", pairs[0, 1][3])

    def test_projection_features_are_identical_for_identical_input(self):
        distances = c.structural_distances(ring(), ring())
        self.assertTrue(all(value == 0 for value in distances.values()))

    def test_pdf_helpers_preserve_fixed_coordinates(self):
        m = probe_pdf.matrix([1, 0, 0, 1, 10, 20])
        self.assertEqual(probe_pdf.operands(m), [1, 0, 0, 1, 10, 20])
        np.testing.assert_array_equal(probe_pdf.forward([0, 0, 1]), np.eye(3))
        row = dict(ocr_bbox=[10, 20, 30, 40], line=dict(xheight=16, baseline=40))
        np.testing.assert_array_equal(
            probe_pdf.normalizer(row) @ [20, 40, 1], [32, 48, 1]
        )


class FittingDiagnostics(unittest.TestCase):
    def test_identical_group_has_no_estimated_noise(self):
        image = ring()
        result = c.fit_group([image, image, image], [0, 1, 2])
        np.testing.assert_allclose(result["template"], image, atol=1e-9)
        self.assertLess(result["noise_upper"], 1e-12)
        self.assertEqual(result["medoid"], 0)
        self.assertEqual(len(result["leave_one_out"]), 3)

    def test_signed_distance_arm_retains_counter_and_coverage_bounds(self):
        image = ring()
        result = c.distance_template([image, image, image])
        self.assertEqual(result.shape, image.shape)
        self.assertTrue(np.all((result >= 0) & (result <= 1)))
        self.assertEqual(c.topology(result > 0.5), (1, 1))

    def test_empty_pair_is_not_compatible(self):
        accepted, _, _, reasons = c.compatible(np.zeros((64, 64)), ring())
        self.assertFalse(accepted)
        self.assertIn("empty_ink", reasons)


class ContourDiagnostics(unittest.TestCase):
    def test_contour_identity_has_zero_distance(self):
        from qualification.font03.experiments.evaluate_contours import contour_error

        self.assertEqual(contour_error(ring(), ring()), {"mean": 0.0, "p95": 0.0})

    def test_missing_contour_is_explicitly_unresolved(self):
        from qualification.font03.experiments.evaluate_contours import contour_error

        self.assertIsNone(contour_error(ring(), np.zeros((64, 64))))

    def test_contour_difference_is_symmetric(self):
        from qualification.font03.experiments.evaluate_contours import contour_error

        moved = c.warp(ring(), [1.0, 0.0, 1.0])
        self.assertEqual(contour_error(ring(), moved), contour_error(moved, ring()))


class ResearchEntryPointContracts(unittest.TestCase):
    def test_declared_manifest_sources_are_mandatory(self):
        import tempfile
        from pathlib import Path
        from qualification.font03.research_checks import require_files

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.pdf"
            with self.assertRaises(FileNotFoundError):
                require_files([source])
            source.write_bytes(b"source fixture")
            require_files([source])

    def test_repair_requires_an_actual_competing_cohort(self):
        from qualification.font03.research_checks import repair_margin_supported

        self.assertFalse(repair_margin_supported(None))
        self.assertFalse(repair_margin_supported(0.0149))
        self.assertTrue(repair_margin_supported(0.015))

    def test_failed_validation_cannot_exit_successfully(self):
        from qualification.font03.research_checks import (
            require_construction_verification,
        )
        import copy

        result = dict(
            qpdf=dict(returncode=0),
            ots=dict(returncode=0),
            pdfium=dict(
                extraction_identical=True,
                pages=[dict(page=1, equal=False), dict(page=2, equal=True)],
            ),
            poppler=dict(
                extraction_identical=True,
                pages=[dict(page=1, equal=False), dict(page=2, equal=True)],
            ),
        )
        require_construction_verification(result)
        for engine in ["qpdf", "ots"]:
            bad = copy.deepcopy(result)
            bad[engine]["returncode"] = 1
            with self.assertRaises(RuntimeError):
                require_construction_verification(bad)
        for engine in ["pdfium", "poppler"]:
            bad = copy.deepcopy(result)
            bad[engine]["extraction_identical"] = False
            with self.assertRaises(RuntimeError):
                require_construction_verification(bad)
            bad = copy.deepcopy(result)
            bad[engine]["pages"][1]["equal"] = False
            with self.assertRaises(RuntimeError):
                require_construction_verification(bad)


if __name__ == "__main__":
    unittest.main()
