import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/cad-design-system/scripts"))
import check_mesh as checker


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "box.stl"
        trimesh.creation.box(extents=[20, 20, 5]).export(self.path)

    def test_thick_box_completes(self):
        rep = checker.analyse(str(self.path), {})
        self.assertTrue(rep["clean"])
        self.assertEqual(rep["status"], "no_findings")

    def test_failed_thickness_is_incomplete_and_cli_exits_two(self):
        out = Path(self.tmp.name) / "report.json"
        with patch.object(trimesh.proximity, "thickness", side_effect=RuntimeError("probe failure")):
            with contextlib.redirect_stdout(io.StringIO()):
                rc = checker.main([str(self.path), "--json", str(out)])
        rep = json.loads(out.read_text())
        self.assertEqual(rc, 2)
        self.assertFalse(rep["clean"])
        self.assertEqual(rep["status"], "incomplete")
        self.assertIn("probe failure", rep["analysis_errors"][0])

    def test_zero_valid_measurements_is_incomplete(self):
        with patch.object(trimesh.proximity, "thickness", return_value=np.full(20, np.nan)):
            rep = checker.analyse(str(self.path), {}, samples=20)
        self.assertFalse(rep["clean"])
        self.assertEqual(rep["status"], "incomplete")

    def test_actual_thin_wall_remains_a_finding(self):
        trimesh.creation.box(extents=[20, 20, 0.6]).export(self.path)
        rep = checker.analyse(str(self.path), {}, samples=2000)
        self.assertFalse(rep["clean"])
        self.assertTrue(any("thin region" in p for p in rep["problems"]))

    def test_narrow_floating_underside_is_not_accepted_as_a_lip(self):
        base = trimesh.creation.box(extents=[20, 20, 2])
        island = trimesh.creation.box(extents=[1, 10, 1])
        island.apply_translation([30, 0, 6])
        trimesh.util.concatenate([base, island]).export(self.path)
        rep = checker.analyse(str(self.path), {})
        self.assertTrue(any(r["severity"] == "error" and "floating underside" in r["verdict"] for r in rep["overhangs"]["regions"]))
        self.assertFalse(rep["clean"])

    def test_rectangle_raster_preserves_span(self):
        m = trimesh.creation.box(extents=[20, 10, 2])
        faces = np.flatnonzero(m.face_normals[:, 2] < -0.99)
        _, _, _, width = checker.region_raster(m, faces)
        self.assertAlmostEqual(width, 10, delta=0.21)

    def test_load_failure_is_incomplete(self):
        out = Path(self.tmp.name) / "report.json"
        with patch.object(checker.trimesh, "load", side_effect=ValueError("bad mesh")):
            with contextlib.redirect_stderr(io.StringIO()):
                rc = checker.main([str(self.path), "--json", str(out)])
        self.assertEqual(rc, 2)
        self.assertFalse(json.loads(out.read_text())["clean"])


if __name__ == "__main__":
    unittest.main()
