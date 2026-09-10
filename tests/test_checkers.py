# /// script
# dependencies = ["numpy", "scipy", "trimesh", "pyyaml", "rtree", "build123d"]
# ///
"""Regression tests for incomplete analysis, body integrity and explicit inlays."""
from pathlib import Path
import contextlib
import io
import json
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import trimesh
from build123d import Align, Box, export_step

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/cad-design-system/scripts'))
import check_mesh
import check_step
import style_tile

MFG = {'id': 'regression', 'build_volume': [250, 250, 256],
       'walls': {'hard_min': .84, 'min_thickness': 1.26},
       'expected_components': 1, 'require_bed_contact': True}


class CheckerRegression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)

    def mesh(self, ext=(12, 12, 3), shift=(0, 0, 0)):
        m = trimesh.creation.box(extents=ext)
        m.apply_translation(np.asarray(shift) + [0, 0, ext[2]/2])
        return m

    def run_mesh(self, mesh, mfg=MFG):
        dest = self.path/'fixture.stl'
        mesh.export(dest)
        return check_mesh.analyse(str(dest), mfg, samples=384)

    def test_closed_box(self):
        rep = self.run_mesh(self.mesh())
        self.assertTrue(rep['analysis_complete'])
        self.assertTrue(rep['clean'], rep['problems'])

    def test_thin_plate(self):
        rep = self.run_mesh(self.mesh((12, 12, .4)))
        self.assertTrue(rep['analysis_complete'])
        self.assertFalse(rep['clean'])
        self.assertTrue(rep['thickness']['regions'])

    def test_reversed_closed_shell(self):
        m = self.mesh(); m.invert()
        rep = self.run_mesh(m)
        self.assertTrue(rep['watertight'])
        self.assertFalse(rep['positive_volume'])
        self.assertFalse(rep['clean'])

    def test_disconnected_bodies(self):
        rep = self.run_mesh(trimesh.util.concatenate([self.mesh(), self.mesh(shift=(20, 0, 0))]))
        self.assertEqual(rep['connected_components'], 2)
        self.assertFalse(rep['clean'])

    def test_bed_offset(self):
        rep = self.run_mesh(self.mesh(shift=(0, 0, 1)))
        self.assertFalse(rep['bounds']['on_bed'])
        self.assertFalse(rep['clean'])

    def test_oriented_fit_not_hypothetical_rotation(self):
        rep = self.run_mesh(self.mesh((16, 9, 3)), {**MFG, 'build_volume': [10, 20, 10]})
        self.assertFalse(rep['bounds']['fits_build_volume'])
        self.assertTrue(rep['bounds']['fits_after_z_quarter_turn'])
        self.assertFalse(rep['clean'])

    def test_ray_exception_is_incomplete(self):
        with patch.object(trimesh.proximity, 'thickness', side_effect=RuntimeError('fixture failure')):
            rep = self.run_mesh(self.mesh())
        self.assertFalse(rep['analysis_complete'])
        self.assertFalse(rep['clean'])
        self.assertIn('fixture failure', str(rep['analysis_errors']))

    def test_zero_valid_rays_is_incomplete(self):
        with patch.object(trimesh.proximity, 'thickness', return_value=np.full(384, np.nan)):
            rep = self.run_mesh(self.mesh())
        self.assertEqual(rep['status'], 'incomplete')
        self.assertFalse(rep['clean'])

    def test_support_query_failure_propagates(self):
        m = self.mesh()
        faces = np.flatnonzero(m.face_normals[:, 2] < -.99)
        with patch.object(trimesh.Trimesh, 'contains', side_effect=RuntimeError('fixture support failure')):
            with self.assertRaisesRegex(RuntimeError, 'support classification failed'):
                check_mesh.classify_horizontal(m, faces)

    def test_cli_failure_code_and_json(self):
        fixture = self.path/'fixture.stl'; self.mesh().export(fixture)
        report = self.path/'report.json'
        with patch.object(check_mesh, 'analyse', side_effect=RuntimeError('fixture error')):
            with contextlib.redirect_stderr(io.StringIO()):
                code = check_mesh.main([str(fixture), '--json', str(report)])
        self.assertEqual(code, 2)
        self.assertFalse(json.loads(report.read_text())['analysis_complete'])

    def step_fixture(self, dimensions):
        path = self.path/'fixture.step'
        export_step(Box(*dimensions, align=(Align.MIN, Align.MIN, Align.MIN)), path)
        return str(path)

    def test_step_does_not_auto_exempt_thin_structural_solid(self):
        rep = check_step.analyse(self.step_fixture((12, 12, .3)), {},
                                 {**MFG, 'text': {'inlay_depth': .4}}, samples=384)
        self.assertFalse(rep['solids'][0]['inlay'])
        self.assertFalse(rep['clean'])

    def test_explicit_inlay_uses_build_axis(self):
        rep = check_step.analyse(self.step_fixture((12, .3, 6)), {}, MFG,
                                 up_name='+Y', samples=384, inlay_indices=(0,), inlay_max_height=.4)
        self.assertAlmostEqual(rep['solids'][0]['build_height'], .3, places=5)
        self.assertTrue(rep['solids'][0]['mesh']['thickness']['skipped'])
        self.assertTrue(rep['solids'][0]['mesh']['positive_volume'])

    def test_empty_step_rejected(self):
        with patch.object(check_step, 'import_step', return_value=SimpleNamespace(solids=lambda: [])):
            with self.assertRaisesRegex(ValueError, 'no solid'):
                check_step.analyse('empty.step', {}, MFG)

    def test_step_mesh_error_propagates(self):
        with patch.object(trimesh.proximity, 'thickness', side_effect=RuntimeError('fixture ray failure')):
            rep = check_step.analyse(self.step_fixture((12, 12, 3)), {}, MFG, samples=384)
        self.assertFalse(rep['analysis_complete'])
        self.assertFalse(rep['clean'])

    def test_generic_tile_rejects_custom_thread_claim(self):
        with self.assertRaisesRegex(ValueError, 'dedicated coupon'):
            style_tile.build({'fasteners': {'method': 'exact native crush-rib profile'}}, MFG, None)


if __name__ == '__main__':
    unittest.main()
