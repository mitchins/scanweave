"""Small deterministic checks of the frozen FONT-02 evaluation contract."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from qualification.font02.rendered_reuse import (
    coverage_metrics,
    evaluate,
    pristine_region,
    renderer_outcome,
    summarize_pair,
    verify_freeze,
)


class RenderedReuseTests(unittest.TestCase):
    def test_identical_coverage_is_safe(self):
        """Identical native-coordinate samples must have zero measured degradation."""
        image = np.eye(7)
        metrics = coverage_metrics(image, image)
        self.assertEqual(metrics, {"mse": 0.0, "iou": 1.0, "area": 0.0})
        self.assertEqual(renderer_outcome(metrics, metrics), {"safe": True, "material": False})

    def test_dot_to_sliver_is_not_preserved(self):
        """Reject shape distortion even when total foreground area remains unchanged."""
        source = np.zeros((12, 12))
        source[4:8, 4:8] = 1
        sliver = np.zeros_like(source)
        sliver[2:10, 5:7] = 1
        baseline = coverage_metrics(source, source)
        result = renderer_outcome(baseline, coverage_metrics(source, sliver))
        self.assertFalse(result["safe"])
        self.assertTrue(result["material"])

    def test_mismatched_geometry_rejected(self):
        """Refuse accidental comparison of differently shaped evaluation regions."""
        with self.assertRaises(ValueError):
            coverage_metrics(np.zeros((2, 3)), np.zeros((3, 2)))

    def test_both_renderers_required(self):
        """A single good renderer cannot conceal a second-renderer regression."""
        record = {"renderer": "pdfium", "source_gate": True, "safe": True, "material": False}
        with self.assertRaises(ValueError):
            summarize_pair("a", "b", [record])
        other = {**record, "renderer": "poppler", "safe": False, "material": True}
        result = summarize_pair("a", "b", [record, other])
        self.assertFalse(result["safe"])
        self.assertTrue(result["material"])

    def test_frozen_source_artifacts_cannot_change(self):
        """Detect modified source decisions before consulting pristine references."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frozen = {}
            for suffix, key in [
                ("source-decisions.json", "decision_sha256"),
                ("rendered-coverage.npz", "coverage_sha256"),
            ]:
                (root / f"test-{suffix}").write_bytes(b"frozen")
                frozen[key] = hashlib.sha256(b"frozen").hexdigest()
            (root / "test-pre-oracle-freeze.json").write_text(json.dumps(frozen))
            self.assertEqual(verify_freeze(root, "test"), frozen)
            (root / "test-source-decisions.json").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                verify_freeze(root, "test")


    def test_nonfinite_coverage_rejected(self):
        """Nonfinite arrays must not silently produce an ambiguous outcome."""
        with self.assertRaises(ValueError):
            coverage_metrics(np.ones((1, 1)), np.array([[np.nan]]))

    def test_complete_frozen_evaluation(self):
        """Exercise a frozen two-renderer split and reject invalid oracle geometry."""
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            oracle = root / "test" / "oracle"
            oracle.mkdir(parents=True)
            image = np.zeros((2, 2), dtype=np.uint8)
            Image.fromarray(image).save(oracle / "target-pristine.png")
            rows = {"records": [{"id": "target", "public_bbox": [0, 0, 2, 2]}]}
            (root / "test-sources.json").write_text(json.dumps(rows))
            records = [{"target": "target", "donor": "donor", "renderer": engine,
                        "source_gate": True, "bounds": [0, 0, 2, 2]}
                       for engine in ["pdfium", "poppler"]]
            (root / "test-source-decisions.json").write_text(json.dumps({"records": records}))
            maps = {f"{engine}-target-{kind}": np.ones((2, 2))
                    for engine in ["pdfium", "poppler"] for kind in ["baseline", "donor"]}
            np.savez(root / "test-rendered-coverage.npz", **maps)
            frozen = {key: hashlib.sha256((root / f"test-{suffix}").read_bytes()).hexdigest()
                      for suffix, key in [("source-decisions.json", "decision_sha256"),
                                          ("rendered-coverage.npz", "coverage_sha256")]}
            (root / "test-pre-oracle-freeze.json").write_text(json.dumps(frozen))
            result = evaluate(root, root, "test")
            self.assertEqual(result["summary"], {"pairs": 1, "accepted": 1, "safe": 1,
                                                  "material": 0, "ambiguous": 0})
            with self.assertRaises(ValueError):
                pristine_region(root / "test", "target", rows["records"][0], [1, 0, 2, 2])
            with self.assertRaises(ValueError):
                pristine_region(root / "test", "target", {"public_bbox": [0, 0, 3, 2]}, [0, 0, 3, 2])


if __name__ == "__main__":
    unittest.main()
