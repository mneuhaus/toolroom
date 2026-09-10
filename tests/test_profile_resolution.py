import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/cad-fdm-design/scripts"))
import resolve_profiles as profiles


class ProfileResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, name, **data):
        p = self.root / (name + ".json")
        p.write_text(json.dumps({"name": name, **data}))
        return p

    def resolve(self, path, overrides=None):
        return profiles.resolve(path, profiles.build_index([self.root]), overrides)

    def test_parent_includes_child_and_task_override_order(self):
        self.put("base", speed=10, start_gcode="BASE", temperature=190)
        self.put("machine-start", start_gcode="MACHINE")
        self.put("first", speed=20)
        self.put("second", speed=30, include=["machine-start"])
        p = self.put("actual", inherits="base", include=["first", "second"], speed=40, type="machine")
        rep = self.resolve(p, {"temperature": 210})
        self.assertEqual(rep["values"], {"speed": 40, "start_gcode": "MACHINE", "temperature": 210})
        self.assertEqual(rep["profile"], {"name": "actual", "type": "machine"})
        self.assertEqual(rep["resolution_order"], ["base", "first", "machine-start", "second", "actual"])

    def test_includes_are_ordered(self):
        self.put("a", value=1)
        self.put("b", value=2)
        one = self.put("ab", include=["a", "b"])
        two = self.put("ba", include=["b", "a"])
        self.assertEqual(self.resolve(one)["values"]["value"], 2)
        self.assertEqual(self.resolve(two)["values"]["value"], 1)

    def test_missing_parent_never_yields_partial_profile(self):
        p = self.put("broken", inherits="absent", speed=40)
        with self.assertRaisesRegex(profiles.ProfileError, "Missing"):
            self.resolve(p)

    def test_missing_include_is_error(self):
        p = self.put("broken", include=["absent"])
        with self.assertRaisesRegex(profiles.ProfileError, "Missing"):
            self.resolve(p)

    def test_cycle_crossing_inheritance_and_includes(self):
        p = self.put("a", inherits="b")
        self.put("b", include=["a"])
        with self.assertRaisesRegex(profiles.ProfileError, "cycle"):
            self.resolve(p)

    def test_repeated_shared_ancestor_is_not_a_cycle(self):
        self.put("shared", value=1)
        self.put("a", inherits="shared", a=2)
        self.put("b", inherits="shared", b=3)
        p = self.put("actual", include=["a", "b"])
        self.assertEqual(self.resolve(p)["values"], {"value": 1, "a": 2, "b": 3})

    def test_ambiguous_names_are_not_silently_selected(self):
        self.put("base", value=1)
        (self.root / "duplicate.json").write_text(json.dumps({"name": "base", "value": 2}))
        p = self.put("actual", inherits="base")
        with self.assertRaisesRegex(profiles.ProfileError, "Ambiguous"):
            self.resolve(p)

    def test_bad_include_shape_is_error(self):
        p = self.put("actual", include="not-an-array")
        with self.assertRaisesRegex(profiles.ProfileError, "ordered list"):
            self.resolve(p)

    def test_identity_override_is_rejected(self):
        p = self.put("actual", speed=1)
        with self.assertRaisesRegex(profiles.ProfileError, "identity"):
            self.resolve(p, {"name": "other-machine"})


if __name__ == "__main__":
    unittest.main()
