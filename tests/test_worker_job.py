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
