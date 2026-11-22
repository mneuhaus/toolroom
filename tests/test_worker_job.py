import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("worker_job", ROOT / "skills/cad-workflow/scripts/worker_job.py")
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)


class WorkerJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "source.txt").write_text("Authoritative measurement, revision4:2.5mm")
        self.request = {"schema_version": 1, "id": "fit-source", "role": "research",
                        "objective": "Extract the recorded value with its source.",
                        "constraints": ["No geometry changes."],
                        "inputs": [{"path": "source.txt", "purpose": "authoritative measurement"}],
                        "artifacts": ["evidence.json"], "checks": [
                            {"id": "citation", "owner": "worker", "criterion": "Value has an exact source passage."},
                            {"id": "fit", "owner": "astra", "criterion": "Determine applicability to the fit."}]}
        self.path = self.root / "request.json"
        self.out = self.root / "job"

    def prepare(self):
        self.path.write_text(json.dumps(self.request))
        return job.prepare(self.path, ROOT / "profiles/agents/cad-team.yaml", self.out)

    def result(self, **changes):
        manifest = json.loads((self.out / "job.json").read_text())
        file = self.out / "evidence.json"
        file.write_text('{"value":2.5,"unit":"mm"}')
        value = {"job_sha256": manifest["job_sha256"], "status": "no_findings", "summary": "Value extracted.",
                 "artifacts": [{"path": "evidence.json", "sha256": job.digest(file)}],
                 "checks": [{"id": "citation", "status": "no_findings", "evidence": "evidence.json"}]}
        value.update(changes)
        path = self.out / "result.json"
        path.write_text(json.dumps(value))
        return path

    def test_research_brief_has_fresh_context_and_keeps_critical_review(self):
        report = self.prepare()
        self.assertEqual(report["launch"]["fork_turns"], "none")
        self.assertEqual(report["launch"]["model"], "gpt-5.6-terra")
        checked = job.verify(self.out, self.result())
        self.assertEqual(checked["status"], "review")
        self.assertEqual(checked["pending_astra_checks"], ["fit"])

    def test_critical_role_preserves_highest_quality_selection(self):
        self.request["role"] = "critical"
        launch = self.prepare()["launch"]
        self.assertEqual(launch["model"], "gpt-6-astra")
        self.assertEqual(launch["reasoning_effort"], "highest_available")

    def test_changed_source_invalidates_result(self):
        self.prepare()
        path = self.result()
        (self.root / "source.txt").write_text("Changed revision")
        with self.assertRaisesRegex(ValueError, "input changed"):
            job.verify(self.out, path)

    def test_non_entrypoint_input_remains_bound_and_is_not_rendered(self):
        (self.root / "background.txt").write_text("Bound background source")
        self.request["inputs"].append({"path": "background.txt", "purpose": "background evidence"})
        self.request["entrypoints"] = ["source.txt"]
        self.prepare()
        manifest = json.loads((self.out / "job.json").read_text())
        brief = (self.out / "brief.md").read_text()
        self.assertEqual(manifest["entrypoints"], [str((self.root / "source.txt").resolve())])
        self.assertEqual(len(manifest["inputs"]), 2)
        self.assertIn('"source.txt" — authoritative measurement', brief)
        self.assertNotIn("background.txt", brief)
        self.assertNotIn("background evidence", brief)
        self.assertIn("full authoritative input inventory", brief)

        path = self.result()
        (self.root / "background.txt").write_text("Tampered background source")
        with self.assertRaisesRegex(ValueError, "input changed"):
            job.verify(self.out, path)

    def test_invalid_foreign_and_duplicate_entrypoints_are_rejected(self):
        (self.root / "foreign.txt").write_text("Not declared")
        cases = [
            ([], "nonempty list"),
            ("source.txt", "nonempty list"),
            (["foreign.txt"], "declared input"),
            (["source.txt", "./source.txt"], "Duplicate entrypoint"),
        ]
        for entrypoints, message in cases:
            with self.subTest(entrypoints=entrypoints):
                self.request["entrypoints"] = entrypoints
                with self.assertRaisesRegex(ValueError, message):
                    self.prepare()
                self.assertFalse(self.out.exists())

    def test_default_brief_discovers_all_inputs_and_retains_requirements(self):
        nested = self.root / "reference" / "tables"
        nested.mkdir(parents=True)
        (nested / "limits.csv").write_text("feature,limit\nwall,2.0\n")
        self.request["inputs"].append({"path": "reference/tables/limits.csv", "purpose": "print limits"})
        self.request["constraints"].append("Preserve the complete tolerance rule: 0.20 mm through 0.45 mm.")
        self.prepare()
        manifest = json.loads((self.out / "job.json").read_text())
        brief = (self.out / "brief.md").read_text()
        input_section = brief.split("## Inputs\n\n", 1)[1].split("\n\n## Constraints", 1)[0]

        self.assertNotIn("entrypoints", manifest)
        self.assertIn(json.dumps(str(self.root.resolve())), input_section)
        self.assertIn('"source.txt" — authoritative measurement', input_section)
        self.assertIn('"reference/tables/limits.csv" — print limits', input_section)
        self.assertNotIn(str((self.root / "source.txt").resolve()), input_section)
        self.assertNotIn(manifest["inputs"][0]["sha256"], brief)
        self.assertIn("Preserve the complete tolerance rule: 0.20 mm through 0.45 mm.", brief)
        self.assertIn("citation [worker]: Value has an exact source passage.", brief)
        self.assertIn("fit [astra]: Determine applicability to the fit.", brief)
        self.assertIn(str(job.RESULT_SCHEMA), brief)

    def test_many_input_brief_fits_by_factoring_common_paths_and_hashes(self):
        common = self.root / ("authoritative-source-bundle-" + "x" * 72)
        common.mkdir()
        inputs = []
        for index in range(100):
            path = common / f"source-{index:03d}.txt"
            path.write_text(f"source {index}")
            inputs.append({"path": str(path.relative_to(self.root)), "purpose": f"evidence route {index}"})
        self.request["inputs"] = inputs

        report = self.prepare()
        manifest = json.loads((self.out / "job.json").read_text())
        brief = (self.out / "brief.md").read_text()
        previous_input_rows = "\n\n".join(
            f"- {entry['path']} — {entry['purpose']} (SHA256 {entry['sha256']})"
            for entry in manifest["inputs"]
        )

        self.assertLess(report["characters"], 12000)
        self.assertGreater(len(previous_input_rows), 12000)
        self.assertIn('"source-000.txt" — evidence route 0', brief)
        self.assertIn('"source-099.txt" — evidence route 99', brief)
        self.assertEqual(brief.count(str(common.resolve())), 1)

    def test_unrun_worker_check_cannot_be_success(self):
        self.prepare()
        checked = job.verify(self.out, self.result(checks=[]))
        self.assertEqual(checked["status"], "incomplete")
        self.assertEqual(checked["unfinished_worker_checks"], ["citation"])

    def test_worker_cannot_clear_astra_check(self):
        self.prepare()
        path = self.result(checks=[{"id": "fit", "status": "no_findings", "evidence": "evidence.json"}])
        with self.assertRaisesRegex(ValueError, "Astra-owned"):
            job.verify(self.out, path)

    def test_artifact_binding_detects_changed_evidence(self):
        self.prepare()
        path = self.result()
        (self.out / "evidence.json").write_text("different")
        with self.assertRaisesRegex(ValueError, "changed"):
            job.verify(self.out, path)

    def test_artifact_cannot_escape_job_via_symlink(self):
        self.prepare()
        (self.out / "external").symlink_to(self.root, target_is_directory=True)
        path = self.result(artifacts=[{"path": "external/source.txt", "sha256": job.digest(self.root / "source.txt")}])
        with self.assertRaisesRegex(ValueError, "leaves job"):
            job.verify(self.out, path)

    def test_wrong_job_result_is_rejected(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "different job"):
            job.verify(self.out, self.result(job_sha256="0" * 64))

    def test_overlong_brief_is_not_silently_truncated(self):
        self.request["constraints"] = ["A" * 13000]
        with self.assertRaisesRegex(ValueError, "narrow the job"):
            self.prepare()
        self.assertFalse(self.out.exists())

    def test_existing_job_is_not_overwritten(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
