"""Source-bound geometry and API checks for the canonical M3 hybrid hole."""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "toolroom/profiles/interfaces/m3-hybrid-hole.json"
SOURCE_DIR = ROOT / "step-feeder/single-step-r10/native/m3-hybrid-source"
SCRIPT_PATH = ROOT / "toolroom/skills/onshape-cad/scripts/m3_hybrid_hole.py"
FS_PATH = ROOT / "toolroom/skills/onshape-cad/lib/m3_hybrid_hole.fs"


class M3HybridHoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib.util

        spec = importlib.util.spec_from_file_location("m3_hybrid_hole", SCRIPT_PATH)
        cls.mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(cls.mod)
        cls.profile = cls.mod.load_profile()

    def test_profile_retains_source_identity_and_hashes(self):
        source = self.profile["source"]
        self.assertEqual(source["document_id"], "725c6d79c4d6edf9a9538d9b")
        self.assertFalse(source["document_id"].startswith("d"))
        self.assertEqual(source["microversion_id"], "dc0b527588bd794f944ac481")
        self.assertEqual(source["part_id"], "JHD")
        for filename, key in [("bodydetails.json", "bodydetails_sha256"), ("parts.json", "parts_sha256")]:
            digest = hashlib.sha256((SOURCE_DIR / filename).read_bytes()).hexdigest()
            self.assertEqual(digest, source[key])

    def test_exact_twelve_arc_loop_closes_and_is_tangent(self):
        arcs = self.profile["contour"]["arcs"]
        self.assertEqual(len(arcs), 12)
        for index, arc in enumerate(arcs):
            points = arc["points"]
            self.assertEqual(len(points), 3)
            center = arc["center"]
            for point in points:
                radius = math.dist(point, center)
                self.assertAlmostEqual(radius, arc["radius"], delta=3e-12)
            end = points[2]
            start = arcs[(index + 1) % len(arcs)]["points"][0]
            self.assertLess(math.dist(end, start), 3e-12)
            # Tangents at each shared endpoint agree, including the reversing
            # source coedges (the tangent continuity is the design invariant).
            c1 = center
            next_arc = arcs[(index + 1) % len(arcs)]
            c2 = next_arc["center"]
            start_vector = (points[0][0] - c1[0], points[0][1] - c1[1])
            mid_vector = (points[1][0] - c1[0], points[1][1] - c1[1])
            direction1 = 1 if start_vector[0] * mid_vector[1] - start_vector[1] * mid_vector[0] > 0 else -1
            next_mid = next_arc["points"][1]
            next_start_vector = (start[0] - c2[0], start[1] - c2[1])
            next_mid_vector = (next_mid[0] - c2[0], next_mid[1] - c2[1])
            direction2 = 1 if next_start_vector[0] * next_mid_vector[1] - next_start_vector[1] * next_mid_vector[0] > 0 else -1
            t1 = (-direction1 * (end[1] - c1[1]), direction1 * (end[0] - c1[0]))
            t2 = (-direction2 * (start[1] - c2[1]), direction2 * (start[0] - c2[0]))
            dot = sum(t1[i] * t2[i] for i in range(2)) / (math.dist(end, c1) * math.dist(start, c2))
            self.assertGreater(dot, 1.0 - 2e-10)

    def test_profile_arcs_are_full_precision_source_edge_values(self):
        bodydetails = json.loads((SOURCE_DIR / "bodydetails.json").read_text(encoding="utf-8"))
        body = next(body for body in bodydetails["bodies"] if body["id"] == "JHD")
        face = next(face for face in body["faces"] if face["id"] == "JHG")
        coedges = next(loop for loop in face["loops"] if loop["type"] == "inner")["coedges"]
        edges = {edge["id"]: edge for edge in body["edges"]}
        for stored, coedge in zip(self.profile["contour"]["arcs"], coedges, strict=True):
            edge = edges[coedge["edgeId"]]
            points = [edge["geometry"][key] for key in ("startPoint", "midPoint", "endPoint")]
            if not coedge["orientation"]:
                points.reverse()
            points_mm = [[point[0] * 1000, point[1] * 1000] for point in points]
            self.assertEqual(stored["id"], coedge["edgeId"])
            for actual, expected in zip(stored["points"], points_mm, strict=True):
                self.assertLess(math.dist(actual, expected), 2e-15)
            self.assertAlmostEqual(stored["radius"], edge["curve"]["radius"] * 1000, delta=2e-15)

    def test_depth_and_source_cross_section(self):
        bodydetails = json.loads((SOURCE_DIR / "bodydetails.json").read_text(encoding="utf-8"))
        body = next(body for body in bodydetails["bodies"] if body["id"] == "JHD")
        bottom = next(face for face in body["faces"] if face["id"] == "JHG")
        source_inner_area_mm2 = math.pi * 3.3**2 - bottom["area"] * 1_000_000
        core = self.mod.hybrid_tool((0, 0, 0), (0, 0, 1), 8.4, entry_relief=False)
        self.assertAlmostEqual(float(core.volume) / 8.4, source_inner_area_mm2, delta=2e-11)
        self.assertAlmostEqual(float(core.bounding_box().max.Z - core.bounding_box().min.Z), 8.4, delta=2e-6)

    def test_build123d_tool_is_valid_and_matches_bounds(self):
        mod = self.mod
        tool = mod.hybrid_tool((10.0, -4.0, 2.5), (0.0, 0.0, 1.0), 8.4, (1.0, 0.0, 0.0))
        self.assertTrue(tool.is_valid)
        self.assertEqual(len(tool.solids()), 1)
        box = tool.bounding_box()
        self.assertAlmostEqual(float(box.min.Z), 2.5, delta=2e-6)
        self.assertAlmostEqual(float(box.max.Z), 10.9, delta=2e-6)
        self.assertLessEqual(float(box.max.X - box.min.X), 4.20001)
        self.assertLessEqual(float(box.max.Y - box.min.Y), 4.20001)

    def test_arbitrary_axis_and_orthogonal_frame(self):
        mod = self.mod
        axis = (1.0, 2.0, 3.0)
        x_dir = (2.0, -1.0, 0.0)
        tool = mod.hybrid_tool((1.0, 2.0, 3.0), axis, 8.4, x_dir, entry_relief=False)
        clearance = mod.clearance_tool((1.0, 2.0, 3.0), axis, 8.4, x_dir)
        self.assertTrue(tool.is_valid)
        self.assertTrue(clearance.is_valid)
        self.assertEqual(len(tool.solids()), 1)
        self.assertEqual(len(clearance.solids()), 1)
        with self.assertRaises(ValueError):
            mod.hybrid_tool((0, 0, 0), axis, 8.4, axis)

    def test_clearance_is_diametral_3_4(self):
        clearance = self.mod.clearance_tool((0, 0, 0), (0, 0, 1), 8.4)
        self.assertAlmostEqual(float(clearance.bounding_box().max.X - clearance.bounding_box().min.X), 3.4, delta=2e-6)
        self.assertAlmostEqual(float(clearance.bounding_box().max.Y - clearance.bounding_box().min.Y), 3.4, delta=2e-6)

    def test_nominal_m3_geometric_mating_and_clearance_coupon(self):
        from build123d import Solid

        screw = Solid.make_cylinder(1.5, 8.4)
        hybrid = self.mod.hybrid_tool((0, 0, 0), (0, 0, 1), 8.4)
        clearance = self.mod.clearance_tool((0, 0, 0), (0, 0, 1), 8.4)
        hybrid_void_overlap = float(hybrid.intersect(screw).volume)
        clearance_void_overlap = float(clearance.intersect(screw).volume)
        self.assertGreater(float(screw.volume) - hybrid_void_overlap, 0.1)
        self.assertAlmostEqual(clearance_void_overlap, float(screw.volume), delta=2e-7)

    def test_generated_fragment_matches_maintained_fragment(self):
        generated = self.mod.render_featurescript(self.profile)
        self.assertEqual(FS_PATH.read_text(encoding="utf-8"), generated)
        self.assertIn("export function m3HybridTool", generated)
        self.assertIn("export function m3HybridHole", generated)
        self.assertIn("export function m3ClearanceTool", generated)
        self.assertNotIn("id ~", generated)
        self.assertIn('"tools": qUnion([result, relief])', generated)
        union_start = generated.index('opBoolean(context, id + "ReliefUnion"')
        union_end = generated.index('});', union_start)
        union_map = generated[union_start:union_end]
        self.assertNotIn('"targets"', union_map)

    def test_native_fixture_is_standalone_and_reproducible(self):
        fragment = self.mod.render_featurescript(self.profile)
        fixture = self.mod.render_compile_fixture(fragment)
        self.assertTrue(fixture.startswith("FeatureScript 3044;"))
        self.assertIn('import(path : "onshape/std/common.fs", version : "3044.0");', fixture)
        self.assertIn(fragment, fixture)
        self.assertIn("function m3CouponBlock", fixture)
        self.assertIn('"M3 hybrid cutter"', fixture)
        self.assertIn('"M3 hybrid coupon"', fixture)
        self.assertIn('"M3 clearance cutter 3.4 mm"', fixture)
        self.assertNotIn("definition.targets", fixture)

    def test_no_claim_of_physical_holding(self):
        text = PROFILE_PATH.read_text(encoding="utf-8").lower()
        self.assertNotIn("holding force", text)
        self.assertIn("explicit non-m3 or clearance exceptions", text)


if __name__ == "__main__":
    unittest.main()
