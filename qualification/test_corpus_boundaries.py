#!/usr/bin/env python3
"""Synthetic-only controls for corpus containment and diagnostic filename tags."""
import argparse
import builtins
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import corpus_adapter as adapter

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "probe" / "p09_realtext"


class CorpusBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / "corpus"
        self.root.mkdir()
        self.out = self.base / "operator-chosen-output"

    def document(self, identity="receipts/doc", root=None):
        directory = (root or self.root) / identity
        directory.mkdir(parents=True)
        image = directory / "page.png"
        shutil.copyfile(FIXTURE / "p09_realtext.png", image)
        ocr = json.loads((FIXTURE / "p09_realtext.ocr.json").read_text())
        ocr["page_id"] = "page"
        ocr["raster"]["pixel_sha256"] = adapter.pixel_hash_sha256(str(image))[0]
        (directory / "page.ocr.json").write_text(json.dumps(ocr))
        return directory

    def invoke(self, root=None, include=False):
        arguments = ["corpus_adapter.py", "--corpus", str(root or self.root), "--out", str(self.out)]
        if include:
            arguments.append("--include-holdout")
        with patch.object(sys, "argv", arguments), redirect_stdout(io.StringIO()):
            return adapter.main()

    def assert_blocked(self, message="outside corpus root"):
        with self.assertRaisesRegex(adapter.CorpusContainmentError, message):
            self.invoke()
        self.assertFalse((self.out / "document_manifest.json").exists())

    def test_operator_root_symlink_and_arbitrary_output_remain_valid(self):
        self.document()
        alias = self.base / "selected-root"
        alias.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(self.invoke(root=alias), 0)
        manifest = json.loads((self.out / "document_manifest.json").read_text())
        self.assertEqual(manifest["corpus_root"], str(self.root.resolve()))
        self.assertEqual(manifest["documents"][0]["document"], "receipts/doc")

    def test_internal_directory_raster_and_ocr_symlinks_remain_valid(self):
        source = self.document("assets/physical")
        receipts = self.root / "receipts"
        receipts.mkdir()
        (receipts / "directory-alias").symlink_to(source, target_is_directory=True)
        linked = receipts / "file-alias"
        linked.mkdir()
        for name in ("page.png", "page.ocr.json"):
            (linked / name).symlink_to(source / name)
        self.assertEqual(self.invoke(), 0)
        manifest = json.loads((self.out / "document_manifest.json").read_text())
        identities = {document["document"] for document in manifest["documents"]}
        self.assertIn("receipts/directory-alias", identities)
        self.assertIn("receipts/file-alias", identities)

    def test_external_stratum_is_rejected(self):
        external = self.base / "corpus-sibling"
        external.mkdir()
        (self.root / "receipts").symlink_to(external, target_is_directory=True)
        self.assert_blocked()

    def test_external_document_is_rejected(self):
        external = self.base / "external"
        external.mkdir()
        (self.root / "receipts").mkdir()
        (self.root / "receipts" / "doc").symlink_to(external, target_is_directory=True)
        self.assert_blocked()

    def test_external_raster_and_ocr_are_rejected_before_decode(self):
        for name in ("page.png", "page.hocr", "page.ocr.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                self.root = Path(temporary) / "corpus"
                self.root.mkdir()
                directory = self.document()
                target = Path(temporary) / "external"
                target.write_bytes(b"must not be consumed")
                destination = directory / name
                destination.unlink(missing_ok=True)
                destination.symlink_to(target)
                with patch.object(adapter, "pixel_hash_sha256") as decode:
                    self.assert_blocked()
                    decode.assert_not_called()

    def test_dangling_external_symlink_is_not_silently_skipped(self):
        (self.root / "receipts").symlink_to(self.base / "absent-external", target_is_directory=True)
        self.assert_blocked()

    def test_symlink_loop_has_an_explicit_resolution_error(self):
        loop = self.root / "receipts"
        loop.symlink_to(loop)
        self.assert_blocked("cannot resolve corpus entry")

    def test_containment_failure_is_an_intelligible_cli_error(self):
        (self.root / "receipts").symlink_to(self.base, target_is_directory=True)
        result = subprocess.run([sys.executable, str(HERE / "corpus_adapter.py"),
                                 "--corpus", str(self.root), "--out", str(self.out)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("BLOCKED:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_internal_holdout_symlinks_are_sealed_without_decoding(self):
        directory = self.document("receipts_holdout/holdout_doc")
        (directory / "page.hocr").write_text("sealed hOCR bytes: never parsed")
        for name in ("page.png", "page.ocr.json", "page.hocr"):
            target = self.root / name
            shutil.copyfile(directory / name, target)
            (directory / name).unlink()
            (directory / name).symlink_to(target)
        seal = adapter.seal_material(str(self.root), "receipts_holdout/holdout_doc")
        with patch.object(adapter, "pixel_hash_sha256", side_effect=AssertionError("sealed bytes decoded")):
            self.assertEqual(self.invoke(), 0)
        self.assertEqual(json.loads((self.out / "sealed_holdout.json").read_text()), [seal])
        self.assertEqual(json.loads((self.out / "document_manifest.json").read_text())["documents"], [])

    def test_external_holdout_sources_are_rejected_even_during_sealing(self):
        for name in ("page.png", "page.hocr", "page.ocr.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                self.root = Path(temporary) / "corpus"
                self.root.mkdir()
                directory = self.document("receipts_holdout/holdout_doc")
                target = Path(temporary) / "external"
                target.write_bytes(b"external holdout bytes must not be hashed")
                source = directory / name
                source.unlink(missing_ok=True)
                source.symlink_to(target)
                original_open = builtins.open
                def reject_external_read(file, *args, target=target, original_open=original_open, **kwargs):
                    if isinstance(file, (str, Path)) and Path(file).resolve() == target:
                        raise AssertionError("external holdout source was opened")
                    return original_open(file, *args, **kwargs)
                with patch("builtins.open", side_effect=reject_external_read):
                    with self.assertRaisesRegex(adapter.CorpusContainmentError, "outside corpus root"):
                        adapter.seal_material(str(self.root), "receipts_holdout/holdout_doc")
                    self.assert_blocked()

    def test_external_holdout_document_is_rejected(self):
        (self.root / "receipts_holdout").mkdir()
        external = self.base / "external"
        external.mkdir()
        (self.root / "receipts_holdout" / "holdout_doc").symlink_to(external, target_is_directory=True)
        self.assert_blocked()

    def test_direct_seal_call_cannot_escape_by_document_id_or_symlink(self):
        external = self.base / "external"
        external.mkdir()
        (self.root / "alias").symlink_to(external, target_is_directory=True)
        for identity in ("../external", "alias"):
            with self.subTest(identity=identity):
                with self.assertRaisesRegex(adapter.CorpusContainmentError, "outside corpus root"):
                    adapter.seal_material(str(self.root), identity)

    def test_internal_development_alias_to_holdout_requires_authorization(self):
        held = self.document("receipts_holdout/holdout_doc")
        (self.root / "receipts").mkdir()
        (self.root / "receipts" / "alias").symlink_to(held, target_is_directory=True)
        with patch.object(adapter, "pixel_hash_sha256") as decode:
            self.assert_blocked("targets named holdout")
            decode.assert_not_called()
        self.assertEqual(self.invoke(include=True), 0)
        documents = json.loads((self.out / "document_manifest.json").read_text())["documents"]
        self.assertEqual({d["document"] for d in documents},
                         {"receipts/alias", "receipts_holdout/holdout_doc"})

    def test_individual_development_files_cannot_alias_named_holdout(self):
        held = self.document("receipts_holdout/holdout_doc")
        development = self.document()
        for name in ("page.png", "page.ocr.json"):
            with self.subTest(name=name):
                original = (development / name).read_bytes()
                (development / name).unlink()
                (development / name).symlink_to(held / name)
                self.assert_blocked("targets named holdout")
                (development / name).unlink()
                (development / name).write_bytes(original)

    def test_ocr_name_is_not_interpreted_as_a_glob(self):
        directory = self.document()
        (directory / "page.png").rename(directory / "page[1].png")
        # An empty page_id is permitted by the adapter's binding check but not
        # the schema; use p000001 (its documented default) for unusual stems.
        ocr = json.loads((directory / "page.ocr.json").read_text())
        ocr["page_id"] = "p000001"
        (directory / "page[1].ocr.json").write_text(json.dumps(ocr))
        (directory / "page.ocr.json").unlink()
        (directory / "page1.ocr.json").write_text("not the requested OCR")
        self.assertEqual(self.invoke(), 0)


class DiagnosticTagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = HERE / "experiments" / "m1c_r3"
        spec = importlib.util.spec_from_file_location("bounded_diagnostic", directory / "diagnostic.py")
        cls.diagnostic = importlib.util.module_from_spec(spec)
        with patch.object(sys, "path", [str(directory), *sys.path]):
            spec.loader.exec_module(cls.diagnostic)

    def test_rejects_path_tags_in_cli_and_programmatic_entrypoints(self):
        for tag in ("", ".", "..", "../escape", "/absolute", "a/b", "a\\b", "C:\\escape", "C:escape", "a\0b"):
            with self.subTest(tag=tag):
                with self.assertRaises(argparse.ArgumentTypeError):
                    self.diagnostic.output_tag(tag)
                with self.assertRaises(argparse.ArgumentTypeError):
                    self.diagnostic.run("unused-font", "e", 1, "unused-output", tag)
                with tempfile.TemporaryDirectory() as temporary:
                    out = Path(temporary) / "not-created"
                    args = ["diagnostic.py", "--out", str(out), "--tag", tag]
                    with patch.object(sys, "argv", args), redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit) as error:
                            self.diagnostic.main()
                    self.assertEqual(error.exception.code, 2)
                    self.assertFalse(out.exists())

    def test_valid_labels_and_arbitrary_output_are_preserved(self):
        for tag in ("r3-diag", "日本語", "release 1", "a..b", "amount$"):
            self.assertEqual(self.diagnostic.output_tag(tag), tag)
        source = np.zeros((7, 7), dtype=np.float32)
        source[2:5, 2:5] = 1
        observations = (source, [source.copy()], [(0.0, 0.0)], [{}])
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "chosen" / "reports"
            with patch.object(self.diagnostic, "build_observation_set", return_value=observations):
                result, label = self.diagnostic.run("unused", "e", 1, str(out), "日本語")
            self.assertEqual(label, "日本語")
            self.assertEqual(result["A_single"]["metrics"]["iou"], 1.0)
            self.assertTrue((out / label / "source.npy").is_file())
            arguments = ["diagnostic.py", "--out", str(out), "--tag", "release 1", "--ns", "1"]
            with (patch.object(sys, "argv", arguments),
                  patch.object(self.diagnostic, "FONTS", ["unused"]),
                  patch.object(self.diagnostic, "GLYPHS", ["e"]),
                  patch.object(self.diagnostic, "font_hash", return_value="test-font"),
                  patch.object(self.diagnostic, "build_observation_set", return_value=observations),
                  redirect_stdout(io.StringIO())):
                self.assertEqual(self.diagnostic.main(), 0)
            self.assertTrue((out / "diagnostic_full.json").is_file())
            self.assertTrue((out / "release 1_unused_e_n1" / "source.npy").is_file())


if __name__ == "__main__":
    unittest.main()
