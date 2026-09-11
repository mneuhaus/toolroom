"""Native-format fixtures and isolated fake process; no printer or live CAD."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from xml.etree import ElementTree as E

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("print_package", ROOT / "skills/cad-fdm-design/scripts/print_package.py")
pkg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pkg)


def fixture(path, *, omitted=None, shift=0, units="millimeter", outside=False, settings=None):
    ns = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
    model = f'''<model xmlns="{ns}" unit="{units}"><resources>
    <object id="1"><mesh><vertices><vertex x="0" y="0" z="0"/><vertex x="1" y="0" z="0"/><vertex x="0" y="1" z="0"/><vertex x="0" y="0" z="1"/></vertices><triangles><triangle v1="0" v2="2" v3="1"/><triangle v1="0" v2="1" v3="3"/><triangle v1="0" v2="3" v3="2"/><triangle v1="1" v2="2" v3="3"/></triangles></mesh></object>
    <object id="2"><components><component objectid="1" transform="1 0 0 0 1 0 0 0 1 2 0 0"/></components></object></resources>
    <build><item objectid="2" transform="1 0 0 0 1 0 0 0 1 {10+shift} 10 0"/><item objectid="2" transform="1 0 0 0 1 0 0 0 1 320 10 0"/></build></model>'''
    config = E.Element("config"); slices = E.Element("config")
    members = {"3D/3dmodel.model": model, "Metadata/project_settings.config": json.dumps(settings or {})}
    for i in [1, 2]:
        plate = E.SubElement(config, "plate")
        for k, v in {"plater_id": str(i), "gcode_file": f"Metadata/plate_{i}.gcode"}.items():
            E.SubElement(plate, "metadata", key=k, value=v)
        ins = E.SubElement(plate, "model_instance")
        for k, v in {"object_id": "2", "instance_id": str(i-1), "identify_id": str(i)}.items():
            E.SubElement(ins, "metadata", key=k, value=v)
        plate = E.SubElement(slices, "plate")
        for k, v in {"index": str(i), "outside": "true" if outside else "false"}.items():
            E.SubElement(plate, "metadata", key=k, value=v)
        E.SubElement(plate, "object", identify_id=str(i), skipped="false")
        members[f"Metadata/plate_{i}.gcode"] = "; FEATURE: Outer wall\nG1 X10 Y10 E1\n"
        members[f"Metadata/plate_{i}.json"] = json.dumps({"bbox_objects": [{"id": i}]})
    members["Metadata/model_settings.config"] = E.tostring(config)
    members["Metadata/slice_info.config"] = E.tostring(slices)
    with zipfile.ZipFile(path, "w") as z:
        for name, value in members.items():
            if name != omitted:
                z.writestr(name, value)


class PrintPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.source = self.root / "source.3mf"
        fixture(self.source)

    def test_two_plates_and_composed_transform(self):
        result = pkg._inspect(self.source)
        self.assertEqual(result["status"], "no_findings")
        self.assertEqual(len(result["details"]["plates"]), 2)
        self.assertEqual(result["details"]["geometry"]["instances"][0]["positioned_bounds_mm"][0], [12, 10, 0])
        self.assertTrue(result["pending_critical_reviews"])

    def test_second_plate_missing_gcode_is_not_ignored(self):
        fixture(self.source, omitted="Metadata/plate_2.gcode")
        result = pkg._inspect(self.source)
        self.assertEqual(result["status"], "review")
        self.assertTrue(result["details"]["plates"][1]["problems"])

    def test_outside_plate_and_unsupported_units(self):
        fixture(self.source, outside=True)
        self.assertEqual(pkg._inspect(self.source)["status"], "review")
        fixture(self.source, units="inch")
        self.assertEqual(pkg._inspect(self.source)["status"], "incomplete")

    def test_changed_pose_is_detected(self):
        moved = self.root / "moved.3mf"; fixture(moved, shift=1)
        self.assertEqual(pkg._pose_comparison(pkg._inspect(self.source), pkg._inspect(moved))["status"], "fail")

    def setup_build(self, extra=None):
        machine = {"name": "Fixture machine", "type": "machine", "printer_model": "Fixture", **{k: k for k in pkg.ROUTINE_KEYS}}
        process = {"name": "Fixture process", "type": "process", "layer_height": "0.2"}
        filament = {"name": "Fixture filament", "type": "filament", "nozzle_temperature": ["220"]}
        for name, row in [("machine", machine), ("process", process), ("filament", filament)]:
            (self.root / f"{name}.json").write_text(json.dumps(row))
        # A real subprocess logs invocation and supplies a valid native-format result.
        slicer = self.root / "fake-slicer"
        slicer.write_text('''#!/usr/bin/env python3
import sys,json,zipfile
from pathlib import Path
a=sys.argv[1:];root=Path(__file__).parent
with (root/'calls.jsonl').open('a') as f:f.write(json.dumps(a)+'\\n')
if (root/'fail').exists():print('deliberate failure');sys.exit(7)
source=Path(a[-1]);dest=Path(a[a.index('--export-3mf')+1])
with zipfile.ZipFile(source) as z:members={n:z.read(n) for n in z.namelist()}
if '--load-settings' in a:
 settings={}
 for n in ['machine','process']:
  row=json.loads((root/(n+'.json')).read_text());settings.update({k:v for k,v in row.items() if k not in ['name','type']})
  settings['printer_settings_id' if n=='machine' else 'print_settings_id']=row['name']
 row=json.loads((root/'filament.json').read_text());settings.update({k:v for k,v in row.items() if k not in ['name','type']});settings['filament_settings_id']=[row['name']]
 members['Metadata/project_settings.config']=json.dumps(settings).encode()
with zipfile.ZipFile(dest,'w') as z:
 for n,v in members.items():z.writestr(n,v)
''')
        slicer.chmod(0o755)
        request = {"source": "source.3mf", "slicer": "fake-slicer", "profiles": {"machine": "machine.json", "process": "process.json", "filaments": ["filament.json"]}}
        request.update(extra or {})
        path = self.root / "job.json"; path.write_text(json.dumps(request))
        return path

    def test_build_reimport_no_overrides_and_verified_cache(self):
        path = self.setup_build()
        first, directory, reused = pkg._build(path, self.root / "out")
        self.assertEqual(first["status"], "no_findings", first.get("checks"))
        self.assertFalse(reused)
        self.assertFalse(first["dispatched"])
        calls = [json.loads(s) for s in (self.root / "calls.jsonl").read_text().splitlines()]
        self.assertIn("--load-settings", calls[0]); self.assertNotIn("--load-settings", calls[1]); self.assertNotIn("--load-filaments", calls[1])
        self.assertTrue(pkg._build(path, self.root / "out")[2])
        self.assertEqual(len((self.root / "calls.jsonl").read_text().splitlines()), 2)
        (directory / "native.3mf").write_text("damaged")
        with self.assertRaisesRegex(pkg.PackageError, "hash verification"):
            pkg._build(path, self.root / "out")

    def test_cache_invalidates_changed_profiles_and_resources(self):
        resources = self.root / "resources"; resources.mkdir(); resource = resources / "preset.txt"; resource.write_text("v1")
        path = self.setup_build({"resource_paths": ["resources"]})
        _, first, _ = pkg._build(path, self.root / "out")
        resource.write_text("v2")
        _, second, reused = pkg._build(path, self.root / "out")
        self.assertNotEqual(first, second); self.assertFalse(reused)
        profile = self.root / "process.json"; row = json.loads(profile.read_text()); row["layer_height"] = "0.3"; profile.write_text(json.dumps(row))
        _, third, reused = pkg._build(path, self.root / "out")
        self.assertNotEqual(second, third); self.assertFalse(reused)

    def test_slicer_failure_retains_log_without_success_or_retry(self):
        path = self.setup_build(); (self.root / "fail").touch()
        report, directory, _ = pkg._build(path, self.root / "out")
        self.assertEqual(report["status"], "incomplete")
        self.assertIn("deliberate failure", (directory / "logs/native.log").read_text())
        self.assertFalse((directory / "reimport.3mf").exists())

    def test_source_to_native_change_is_not_hidden_by_stable_reimport(self):
        path = self.setup_build(); original = pkg._inspect
        def altered(file):
            result = original(file); result["details"]["geometry"]["pose_signature"] = "modified-by-slicer"
            return result
        with patch.object(pkg, "_inspect", side_effect=altered):
            report, _, _ = pkg._build(path, self.root / "out")
        self.assertEqual(report["status"], "review")
        check = next(c for c in report["checks"] if c["name"] == "authoritative_source_geometry_preserved")
        self.assertEqual(check["status"], "fail")

    def test_profile_names_do_not_hide_wrong_values(self):
        path = self.setup_build(); resolved = pkg._resolve_job(path); expected = pkg._expected_profiles(resolved)
        report, _, _ = pkg._build(path, self.root / "out")
        report["native"]["details"]["project_settings"]["layer_height"] = "0.4"
        checked = pkg._profile_checks(report["native"], report["reimport"], expected)
        self.assertEqual(next(c for c in checked if c["name"] == "resolved_profile_values_applied")["status"], "fail")


if __name__ == "__main__":
    unittest.main()
