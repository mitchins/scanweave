"""Evaluator-only cluster/recovery contracts; synthetic unit sources, no model."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np
from PIL import Image

from font01 import analysis
from font01.observations import CANVAS

INPUTS = Path(__file__).parent/'font01/test_inputs'


class AnalysisTests(unittest.TestCase):
    def test_complete_entry_points_and_leave_target_out_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source'
            source.mkdir()
            (source/'oracle').mkdir()
            rows = [json.loads(line) for line in (INPUTS/'observations.jsonl').read_text().splitlines()]
            rows.append(dict(rows[0], id='unit-third-e'))
            (source/'observations.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
            labels = []
            for row in rows:
                shutil.copy2(INPUTS/row['image'], source/row['image'])
                shutil.copy2(INPUTS/row['image'], source/'oracle'/(row['id']+'-pristine.png'))
                labels.append({'id': row['id'], 'character': row['character'], 'font_sha256': 'unit-face',
                               'severity': 0})
            (source/'oracle/labels.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in labels))
            output = root/'clusters'
            result = analysis.canonical_clusters(source, output, 100.)
            self.assertEqual(result['canonical_template_clusters']['inferred_groups'], 3)
            self.assertIn('NOT ESTABLISHED', result['font_cohort_assignment'])
            recovered = analysis.recovery(source, output)
            self.assertEqual(len(recovered), 6)
            self.assertEqual({row['arm'] for row in recovered}, {'inferred', 'oracle_cohort_control'})
            self.assertTrue(all(row['donor_count'] == 2 for row in recovered))
            self.assertTrue(all(0 <= row['consensus_iou'] <= 1 for row in recovered))
            # A blank evaluator reference produces no invented accuracy value.
            Image.new('L', (20, 20), 255).save(source/'oracle'/(rows[0]['id']+'-pristine.png'))
            self.assertEqual(len(analysis.recovery(source, output)), 4)
            with self.assertRaises(FileExistsError):
                analysis.canonical_clusters(source, output, 100.)

    def test_shape_diagnostic_is_not_a_pdf_score(self):
        image = np.zeros((CANVAS, CANVAS), np.float32)
        image[15:30, 19:24] = 1
        self.assertEqual(analysis.diagnostic_iou(image, image), 1.)
        self.assertEqual(analysis.diagnostic_iou(np.zeros_like(image), np.zeros_like(image)), 0.)


if __name__ == '__main__':
    unittest.main()
