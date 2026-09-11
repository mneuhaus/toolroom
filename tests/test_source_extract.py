import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).parents[1] / "skills/cad-workflow/scripts/source_extract.py"
SPEC = importlib.util.spec_from_file_location("source_extract", MODULE)
source_extract = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(source_extract)


class SourceExtractTests(unittest.TestCase):
    def snapshot_file(self, root: Path, body: bytes, suffix=".html", **kwargs):
        input_file = root / f"input{suffix}"
        input_file.write_bytes(body)
        output = root / "snapshot"
        return source_extract.snapshot(file=input_file, url=None, out=output, **kwargs), output

    def test_html_removes_script_style_and_navigation(self):
        with tempfile.TemporaryDirectory() as temp:
            metadata, output = self.snapshot_file(Path(temp), b"<html><style>hide</style><nav>links</nav><body><h1>Useful title</h1><script>evil()</script><p>Useful body</p></body></html>")
            self.assertEqual(metadata["status"], "complete")
            text = (output / "text.txt").read_text()
            self.assertIn("Useful title", text)
            self.assertIn("Useful body", text)
            self.assertNotIn("evil", text)
            self.assertNotIn("links", text)

    def test_unicode_offsets_are_text_character_offsets(self):
        with tempfile.TemporaryDirectory() as temp:
            _, output = self.snapshot_file(Path(temp), "αβ clearance ✓".encode())
            result = source_extract.excerpt(snapshot_dir=output, query="clearance", out=Path(temp) / "excerpt.json", max_chars=100)
            item = result["excerpts"][0]
            self.assertEqual(item["start"], 0)
            self.assertEqual(item["text"][3:12], "clearance")
            self.assertEqual(item["text"], "αβ clearance ✓")

    def test_tampered_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            _, output = self.snapshot_file(Path(temp), b"clearance")
            (output / "text.txt").write_text("forged")
            with self.assertRaisesRegex(source_extract.SourceError, "integrity"):
                source_extract.excerpt(snapshot_dir=output, query="forged", out=Path(temp) / "excerpt.json")

    def test_miss_is_explicitly_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            _, output = self.snapshot_file(Path(temp), b"nominal fit")
            result = source_extract.excerpt(snapshot_dir=output, query="clearance", out=Path(temp) / "excerpt.json")
            self.assertEqual(result["status"], "incomplete")
            self.assertEqual(result["reason"], "query_not_found")

    def test_excerpt_has_bounded_output(self):
        with tempfile.TemporaryDirectory() as temp:
            _, output = self.snapshot_file(Path(temp), ("x clearance y " * 100).encode())
            result = source_extract.excerpt(snapshot_dir=output, query="clearance", out=Path(temp) / "excerpt.json", max_chars=80)
            self.assertLessEqual(result["excerpt_char_count"], 80)
            self.assertLessEqual(sum(len(x["text"]) for x in result["excerpts"]), 80)

    def test_small_budget_keeps_the_full_match_or_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            _, output = self.snapshot_file(Path(temp), ("x" * 500 + " clearance after").encode())
            result = source_extract.excerpt(snapshot_dir=output, query="clearance", out=Path(temp) / "excerpt.json", max_chars=12)
            self.assertEqual(result["status"], "complete")
            self.assertIn("clearance", result["excerpts"][0]["text"])
            tiny = source_extract.excerpt(snapshot_dir=output, query="clearance", out=Path(temp) / "tiny.json", max_chars=4)
            self.assertEqual((tiny["status"], tiny["reason"]), ("incomplete", "budget_too_small"))

    def test_unsupported_url_records_state(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "snapshot"
            result = source_extract.snapshot(url="file:///private/example", file=None, out=output)
            self.assertEqual(result["status"], "unsupported")
            self.assertEqual(json.loads((output / "source.json").read_text())["status"], "unsupported")

    def test_oversized_file_records_incomplete_state(self):
        with tempfile.TemporaryDirectory() as temp:
            metadata, output = self.snapshot_file(Path(temp), b"0123456789", max_bytes=5)
            self.assertEqual(metadata["status"], "incomplete")
            self.assertEqual(metadata["reason"], "file_exceeds_max_bytes")
            self.assertFalse((output / "raw.bin").exists())

    def test_binary_and_empty_sources_have_non_complete_states(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binary, binary_output = self.snapshot_file(root, b"%PDF-1.7", suffix=".pdf")
            self.assertEqual((binary["status"], binary["reason"]), ("unsupported", "unsupported_local_file_type"))
            self.assertFalse((binary_output / "raw.bin").exists())
        with tempfile.TemporaryDirectory() as temp:
            empty, _ = self.snapshot_file(Path(temp), b"", suffix=".txt")
            self.assertEqual((empty["status"], empty["reason"]), ("incomplete", "empty_readable_text"))

    def test_unsafe_metadata_path_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, output = self.snapshot_file(root, b"clearance")
            metadata_path = output / "source.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["text_file"] = "../outside.txt"
            metadata_path.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(source_extract.SourceError, "unsafe"):
                source_extract.excerpt(snapshot_dir=output, query="clearance", out=root / "excerpt.json")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, output = self.snapshot_file(root, b"clearance")
            target = root / "elsewhere.txt"
            target.write_text("clearance")
            (output / "text.txt").unlink()
            (output / "text.txt").symlink_to(target)
            with self.assertRaisesRegex(source_extract.SourceError, "regular files"):
                source_extract.excerpt(snapshot_dir=output, query="clearance", out=root / "excerpt.json")

    def test_script_only_html_is_explicitly_dynamic_and_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            metadata, output = self.snapshot_file(Path(temp), b"<html><script src='app.js'></script></html>")
            self.assertEqual(metadata["status"], "incomplete")
            self.assertEqual(metadata["reason"], "dynamic_content_suspected")
            self.assertTrue((output / "raw.bin").exists())


if __name__ == "__main__":
    unittest.main()
