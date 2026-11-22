import hashlib
import json

import pytest

from fsocct.corpus import run_corpus
from fsocct.syntax import FSError


@pytest.fixture
def corpus(tmp_path):
    source = tmp_path / "source.fs"
    source.write_text("""
        function box(c,id) {
            fCuboid(c,id,{corner1:vector(0,0,0)*millimeter,corner2:vector(1,2,3)*millimeter});
        }
        export const good=defineFeature(function(c,id,d) {box(c,id+"box");});
        export const recovered=defineFeature(function(c,id,d) {
            try silent {fCuboid(c,id+"bad",{corner1:vector(0,0,0)*millimeter,corner2:vector(0,0,0)*millimeter});}
            box(c,id+"box");
        });
        export const bad=defineFeature(function(c,id,d) {unimplemented();});
    """)
    data = {
        "sources": [
            {"file": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
        ],
        "cases": [
            {"id": name, "source": source.name, "feature": name}
            for name in ("good", "recovered", "bad")
        ],
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(data))
    return manifest, data


def test_batch_distinguishes_valid_recovered_failed_and_removes_stale_reports(corpus, tmp_path):
    manifest, _ = corpus
    output = tmp_path / "output"
    output.mkdir()
    stale = output / "bad.json"
    stale.write_text('{"previous":"success"}')
    summary = run_corpus(manifest, output)
    assert [c["status"] for c in summary["cases"]] == ["passed", "recovered", "failed"]
    assert summary["passed"] == 1 and summary["recovered"] == 1 and summary["complete"]
    assert summary["cases"][0]["volume_mm3"] == pytest.approx(6)
    assert summary["cases"][1]["recovered_operations"][0]["id"] == ["recovered", "bad"]
    assert "Unknown symbol" in summary["cases"][2]["error"]
    assert not stale.exists()
    assert "kernel.py" in summary["implementation_sha256"]
    assert json.loads((output / "summary.json").read_text()) == summary


def test_batch_timeout_does_not_prevent_next_case(corpus, tmp_path):
    manifest, data = corpus
    data["cases"] = [
        {"id": "timeout", "source": "source.fs", "feature": "good", "timeout": 0.001},
        data["cases"][0],
    ]
    manifest.write_text(json.dumps(data))
    summary = run_corpus(manifest, tmp_path / "output")
    assert [c["status"] for c in summary["cases"]] == ["timeout", "passed"]
    assert "0.001s" in summary["cases"][0]["error"]
    assert not (tmp_path / "output/timeout.json").exists()


def test_batch_rejects_changed_source_and_unknown_selection(corpus, tmp_path):
    manifest, _ = corpus
    with pytest.raises(FSError, match="Unknown corpus"):
        run_corpus(manifest, tmp_path / "output", selected=["typo"])
    (tmp_path / "source.fs").write_text("changed")
    with pytest.raises(FSError, match="hash mismatch"):
        run_corpus(manifest, tmp_path / "output")
    assert not (tmp_path / "output").exists()
