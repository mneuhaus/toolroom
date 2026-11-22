from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from pruefstand.purpose import assess_purpose, load_purpose_snapshot


EMPTY_HASH = hashlib.sha256(b"").hexdigest()


def snapshot(nodes=None, requirements=None):
    return {
        "schema": "pruefstand.purpose/1",
        "source": {"microversion": "immutable-source", "coverage": "declared nodes only"},
        "artifacts": [{"path": "assembly.json", "sha256": EMPTY_HASH}],
        "requirements": requirements
        if requirements is not None
        else [{"id": "req.stop", "active": True, "required_nodes": ["hammer"]}],
        "nodes": nodes
        if nodes is not None
        else [
            node("hammer", "function", ["req.stop"]),
            node("seat", "material", ["hammer"]),
            node("neck", "material", ["seat"]),
            node("pocket", "interface", ["hammer"]),
        ],
    }


def node(node_id, kind, supports, presence="present", evidence=None):
    return {
        "id": node_id,
        "kind": kind,
        "description": node_id,
        "supports": supports,
        "presence": presence,
        "evidence": evidence or {},
    }


def by_id(report):
    return {item["id"]: item for item in report["nodes"]}


def write_snapshot(directory: Path, value: dict, artifact=b"") -> Path:
    (directory / "assembly.json").write_bytes(artifact)
    value = deepcopy(value)
    value["artifacts"][0]["sha256"] = hashlib.sha256(artifact).hexdigest()
    path = directory / "purpose.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_rooted_hammer_seat_neck_chain_preserves_evidence():
    value = snapshot()
    value["nodes"][2]["evidence"] = {"faces": ["snapshot-face"]}
    report = assess_purpose(value)

    assert report["status"] == "no_findings"
    assert {key: item["classification"] for key, item in by_id(report).items()} == {
        "hammer": "ROOTED",
        "seat": "ROOTED",
        "neck": "ROOTED",
        "pocket": "ROOTED",
    }
    assert by_id(report)["neck"]["path"] == ["neck", "seat", "hammer", "req.stop"]
    assert by_id(report)["neck"]["evidence"] == {"faces": ["snapshot-face"]}
    assert "physical_pass" not in report


def test_removed_hammer_orphans_dependents_and_is_missing_required():
    value = snapshot()
    value["nodes"][0]["presence"] = "absent"
    report = assess_purpose(value)

    assert report["status"] == "review"
    assert by_id(report)["hammer"]["classification"] == "ABSENT"
    assert {by_id(report)[name]["classification"] for name in ("seat", "neck", "pocket")} == {
        "ORPHAN"
    }
    assert any(item["code"] == "missing_required_node" for item in report["findings"])


def test_requirement_deactivation_orphans_exclusive_present_nodes():
    value = snapshot()
    value["requirements"][0]["active"] = False
    report = assess_purpose(value)

    assert report["status"] == "review"
    assert {item["classification"] for item in report["nodes"]} == {"ORPHAN"}
    assert not any(item["code"] == "missing_required_node" for item in report["findings"])


def test_shared_neck_is_rooted_by_second_live_purpose():
    value = snapshot(
        nodes=[
            node("hammer", "function", ["req.stop"], "absent"),
            node("seat", "material", ["hammer"]),
            node("neck", "material", ["seat", "latch"]),
            node("latch", "function", ["req.latch"]),
        ],
        requirements=[
            {"id": "req.stop", "active": True, "required_nodes": ["hammer"]},
            {"id": "req.latch", "active": True, "required_nodes": ["latch"]},
        ],
    )
    report = assess_purpose(value)

    assert by_id(report)["neck"]["classification"] == "ROOTED"
    assert by_id(report)["neck"]["path"] == ["neck", "latch", "req.latch"]
    assert by_id(report)["seat"]["classification"] == "ORPHAN"


def test_fully_removed_inactive_module_has_no_orphan():
    value = snapshot(
        nodes=[
            node("hammer", "function", ["req.stop"], "absent"),
            node("seat", "material", ["hammer"], "absent"),
        ],
        requirements=[{"id": "req.stop", "active": False, "required_nodes": ["hammer"]}],
    )
    report = assess_purpose(value)

    assert report["status"] == "no_findings"
    assert {item["classification"] for item in report["nodes"]} == {"ABSENT"}
    assert report["findings"] == []


def test_unknown_mapping_and_upstream_dependency_are_incomplete_never_orphan():
    value = snapshot(
        nodes=[
            node("hammer", "function", ["req.stop"], "unknown"),
            node("seat", "material", ["hammer"]),
            node("neck", "material", ["seat"]),
        ]
    )
    report = assess_purpose(value)

    assert report["status"] == "incomplete"
    assert {item["classification"] for item in report["nodes"]} == {"UNKNOWN"}
    assert all(item["classification"] != "ORPHAN" for item in report["nodes"])
    assert {item["code"] for item in report["findings"]} >= {
        "node_presence_unknown",
        "required_node_unknown",
        "unresolved_purpose",
    }


def test_rooted_and_unrooted_cycles_are_recorded_without_recursion():
    value = snapshot(
        nodes=[
            node("a", "material", ["b"]),
            node("b", "function", ["a", "req.live"]),
            node("x", "material", ["y"]),
            node("y", "interface", ["x"]),
        ],
        requirements=[{"id": "req.live", "active": True, "required_nodes": ["b"]}],
    )
    report = assess_purpose(value)

    assert report["status"] == "review"
    assert by_id(report)["a"]["classification"] == "ROOTED"
    assert by_id(report)["b"]["classification"] == "ROOTED"
    assert by_id(report)["x"]["classification"] == "ORPHAN"
    assert by_id(report)["y"]["classification"] == "ORPHAN"
    assert report["cycles"] == [
        {"nodes": ["a", "b"], "rooted": True},
        {"nodes": ["x", "y"], "rooted": False},
    ]
    assert by_id(report)["x"]["reasons"] == [
        {"code": "cycle_without_root", "target": "x,y"}
    ]


def test_node_upstream_of_unrooted_cycle_names_cycle_as_cause():
    value = snapshot(
        nodes=[
            node("upstream", "material", ["x"]),
            node("x", "material", ["y"]),
            node("y", "interface", ["x"]),
        ],
        requirements=[],
    )
    report = assess_purpose(value)

    assert by_id(report)["upstream"]["classification"] == "ORPHAN"
    assert by_id(report)["upstream"]["reasons"] == [
        {"code": "cycle_without_root", "target": "x,y"}
    ]


def test_unknown_support_target_is_invalid():
    value = snapshot()
    value["nodes"][0]["supports"] = ["not.declared"]
    with pytest.raises(ValueError, match="undeclared targets"):
        assess_purpose(value)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.update(schema="wrong"), "snapshot.schema"),
        (lambda value: value["source"].update(microversion=""), "microversion"),
        (lambda value: value["artifacts"][0].update(sha256="ABC"), "lowercase hexadecimal"),
        (lambda value: value["nodes"].append(deepcopy(value["nodes"][0])), "duplicate node id"),
        (lambda value: value["nodes"][0].update(kind="fastener"), "kind must be"),
        (lambda value: value["nodes"][0].update(kind=["material"]), "kind must be"),
        (lambda value: value["nodes"][0].update(presence="maybe"), "presence must be"),
        (lambda value: value["nodes"][0].update(extra=True), "unknown keys"),
        (lambda value: value["nodes"][0].update(supports=["req.stop", "req.stop"]), "duplicate"),
        (lambda value: value["requirements"][0].update(required_nodes=["req.stop"]), "requirement ids"),
    ],
)
def test_schema_failures(mutate, message):
    value = snapshot()
    mutate(value)
    with pytest.raises(ValueError, match=message):
        assess_purpose(value)


def test_empty_scoped_capture_is_incomplete():
    report = assess_purpose(snapshot(nodes=[], requirements=[]))

    assert report["status"] == "incomplete"
    assert report["counts"]["nodes"] == 0
    assert report["findings"] == [
        {
            "code": "empty_scope",
            "status": "incomplete",
            "reason": "the valid scoped capture declares no nodes",
        }
    ]


def test_loader_verifies_bytes_and_rejects_tampering(tmp_path):
    path = write_snapshot(tmp_path, snapshot(), artifact=b"native capture")
    assert load_purpose_snapshot(path)["source"]["microversion"] == "immutable-source"

    (tmp_path / "assembly.json").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_purpose_snapshot(path)


def test_loader_rejects_parent_traversal(tmp_path):
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"")
    value = snapshot()
    value["artifacts"][0]["path"] = "../outside.json"
    path = snapshot_dir / "purpose.json"
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="escapes"):
        load_purpose_snapshot(path)


def test_loader_rejects_symlink_escape(tmp_path):
    snapshot_dir = tmp_path / "snapshot"
    snapshot_dir.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"")
    (snapshot_dir / "assembly.json").symlink_to(outside)
    path = snapshot_dir / "purpose.json"
    path.write_text(json.dumps(snapshot()), encoding="utf-8")

    with pytest.raises(ValueError, match="escapes"):
        load_purpose_snapshot(path)


@pytest.mark.parametrize(("presence", "expected_code"), [("absent", "missing_required_node"), ("unknown", "required_node_unknown")])
def test_json_cli_preserves_required_node_states(tmp_path, presence, expected_code):
    value = snapshot()
    value["nodes"][0]["presence"] = presence
    path = write_snapshot(tmp_path, value)
    output = tmp_path / "report.json"

    completed = subprocess.run(
        [sys.executable, "-m", "pruefstand.purpose", str(path), "--output", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    report = json.loads(output.read_text(encoding="utf-8"))

    assert completed.returncode == (1 if presence == "absent" else 2)
    assert by_id(report)["hammer"]["classification"] == presence.upper()
    assert any(item["code"] == expected_code for item in report["findings"])


def test_invalid_cli_writes_incomplete_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not JSON", encoding="utf-8")
    output = tmp_path / "report.json"

    completed = subprocess.run(
        [sys.executable, "-m", "pruefstand.purpose", str(bad), "--output", str(output)],
        check=False,
    )
    report = json.loads(output.read_text(encoding="utf-8"))

    assert completed.returncode == 2
    assert report["status"] == "incomplete"
    assert report["findings"][0]["code"] == "invalid_input"
