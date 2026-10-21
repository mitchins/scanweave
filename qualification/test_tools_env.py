"""Historical comparison inputs are intentional; scratch files are private."""
import ast
import os
import runpy
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools_env import comparison_binary, comparison_environment

ROOT = Path(__file__).parent


class ComparisonTools(unittest.TestCase):
    def test_missing_and_relative_historical_paths_fail(self):
        for value in (None, '', 'relative/build'):
            env = {} if value is None else {'SCANWEAVE_BASELINE_BIN': value}
            with patch.dict(os.environ, env, clear=True), self.assertRaises(RuntimeError):
                comparison_binary('SCANWEAVE_BASELINE_BIN')

    def test_explicit_distinct_executable_arms(self):
        with tempfile.TemporaryDirectory() as folder:
            before, after = (Path(folder) / name for name in ('before', 'after'))
            for binary in (before, after):
                binary.write_text('#!/bin/sh\nexit 0\n')
                binary.chmod(0o700)
            with patch.dict(os.environ, {'SCANWEAVE_BASELINE_BIN': str(before),
                                         'SCANWEAVE_BIN': str(after)}, clear=True):
                self.assertEqual(comparison_binary('SCANWEAVE_BASELINE_BIN'), str(before))
                self.assertEqual(comparison_binary('SCANWEAVE_BIN'), str(after))
                before.chmod(0o600)
                with self.assertRaises(RuntimeError):
                    comparison_binary('SCANWEAVE_BASELINE_BIN')
                before.unlink()
                with self.assertRaises(RuntimeError):
                    comparison_binary('SCANWEAVE_BASELINE_BIN')

    def test_actual_historical_scripts_fail_before_measurement_without_overrides(self):
        original_resolve = Path.resolve
        for name in ('tonal_raster/baseline.py', 'tonal_raster/check_controls.py',
                     'real_convergence/runtime_control.py'):
            source = ROOT / name
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder) / 'qualification' / source.parent.name
                root.mkdir(parents=True)

                def resolve(path, *args, source=source, root=root, **kwargs):
                    if path == source:
                        return root / source.name
                    return original_resolve(path, *args, **kwargs)

                with patch.object(Path, 'resolve', resolve), patch.object(
                        sys, 'path', list(sys.path)), patch.dict(os.environ, {}, clear=True):
                    with self.assertRaisesRegex(RuntimeError, 'absolute historical executable'):
                        runpy.run_path(str(source))
                self.assertFalse(list(root.rglob('*.pdf')))
                self.assertFalse(list(root.rglob('*.json')))

    def test_actual_packaging_imports_use_explicit_environment(self):
        original_resolve = Path.resolve
        for name in ('pdf_packaging/run_corpus.py', 'pdf_packaging/run_groups.py'):
            source = ROOT / name
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder) / 'qualification' / source.parent.name
                root.mkdir(parents=True)
                (root / 'corpus.json').write_text('[]')

                def resolve(path, *args, source=source, root=root, **kwargs):
                    if path == source:
                        return root / source.name
                    return original_resolve(path, *args, **kwargs)

                environment = {'PATH': '/caller/bin', 'LD_LIBRARY_PATH': '/caller/lib'}
                with patch.object(Path, 'resolve', resolve), patch.object(
                        sys, 'path', list(sys.path)), patch.dict(
                        os.environ, environment, clear=True), patch(
                        'subprocess.run', side_effect=AssertionError('Unexpected converter')):
                    module = runpy.run_path(str(source))
                self.assertEqual(module['env']['LD_LIBRARY_PATH'], '/caller/lib')
                self.assertEqual(module['env']['PATH'],
                                 str(Path(sys.executable).parent) + ':/caller/bin')
                self.assertEqual(module['env']['OMP_THREAD_LIMIT'], '1')

    def test_environment_preserves_explicit_dependencies(self):
        original = {'PATH': '/caller/bin', 'LD_LIBRARY_PATH': '/caller/lib', 'EXTRA': 'yes'}
        with patch.dict(os.environ, original, clear=True):
            env = comparison_environment('/chosen/venv/bin')
            self.assertEqual(env['PATH'], '/chosen/venv/bin:/caller/bin')
            self.assertEqual(env['LD_LIBRARY_PATH'], '/caller/lib')
            self.assertEqual(env['OMP_THREAD_LIMIT'], '1')
            self.assertEqual(dict(os.environ), original)
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(comparison_environment('/chosen/bin')['PATH'], '/chosen/bin')

    def test_private_scratch_lifetime_in_actual_utilities(self):
        # Exercise each actual context-manager configuration in isolation, including
        # an exception path. No corpus/PDF generation is necessary for this bound.
        for name in ('tonal_raster/check_synthetic_renders.py',
                     'pr_closure/evaluate_repair.py', 'n1_experiments.py'):
            tree = ast.parse((ROOT / name).read_text())
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Attribute)
                     and isinstance(n.func.value, ast.Name)
                     and n.func.value.id == 'tempfile'
                     and n.func.attr == 'TemporaryDirectory']
            self.assertTrue(calls, name)
            for call in calls:
                self.assertNotIn('dir', [k.arg for k in call.keywords])
                options = {item.arg: ast.literal_eval(item.value) for item in call.keywords}
                paths = []
                def fail_inside_scratch(options=options, paths=paths):
                    with tempfile.TemporaryDirectory(**options) as first:
                        paths.append(Path(first))
                        with tempfile.TemporaryDirectory(**options) as second:
                            paths.append(Path(second))
                            self.assertNotEqual(first, second)
                            self.assertEqual(Path(first).stat().st_mode & 0o777, 0o700)
                            raise RuntimeError('control failure')

                with self.assertRaisesRegex(RuntimeError, 'control failure'):
                    fail_inside_scratch()
                self.assertTrue(all(not p.exists() for p in paths))


if __name__ == '__main__':
    unittest.main()
