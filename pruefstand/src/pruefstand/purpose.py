"""Validate and assess declared purpose/dependency snapshots.

The graph is deliberately bounded to declarations supplied by the CAD capture.  It
does not infer purpose from geometry and it does not approve physical behaviour or
material removal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Any


SNAPSHOT_SCHEMA = "pruefstand.purpose/1"
REPORT_SCHEMA = "pruefstand.purpose-report/1"
_ROOT_KEYS = {"schema", "source", "artifacts", "requirements", "nodes"}
_REQUIREMENT_KEYS = {"id", "active", "required_nodes", "description"}
_NODE_KEYS = {"id", "kind", "description", "supports", "presence", "evidence"}
_ARTIFACT_KEYS = {"path", "sha256"}
_KINDS = {"function", "material", "interface"}
_PRESENCES = {"present", "absent", "unknown"}
_HASH_LENGTH = 64


def _mapping(value: Any, where: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    return value


def _list(value: Any, where: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{where} must be a list")
    return value


def _keys(value: dict, allowed: set[str], required: set[str], where: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"{where} has unknown keys: {sorted(unknown)}")
    missing = required - set(value)
    if missing:
        raise ValueError(f"{where} is missing required keys: {sorted(missing)}")


def _identifier(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where} must be a nonempty string")
    return value


def _string_list(value: Any, where: str) -> list[str]:
    items = _list(value, where)
    for index, item in enumerate(items):
        _identifier(item, f"{where}[{index}]")
    if len(items) != len(set(items)):
        raise ValueError(f"{where} contains duplicate entries")
    return items


def _validate_snapshot(snapshot: Any) -> dict:
    root = _mapping(snapshot, "snapshot")
    try:
        json.dumps(root, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"snapshot must contain JSON-compatible values: {exc}") from exc
    _keys(root, _ROOT_KEYS, _ROOT_KEYS, "snapshot")
    if root["schema"] != SNAPSHOT_SCHEMA:
        raise ValueError(
            f"snapshot.schema must be {SNAPSHOT_SCHEMA!r}, got {root['schema']!r}"
        )

    source = _mapping(root["source"], "snapshot.source")
    for name in ("microversion", "coverage"):
        if name not in source:
            raise ValueError(f"snapshot.source is missing required key: {name!r}")
        _identifier(source[name], f"snapshot.source.{name}")

    artifacts = _list(root["artifacts"], "snapshot.artifacts")
    if not artifacts:
        raise ValueError("snapshot.artifacts must contain at least one artifact")
    for index, artifact_value in enumerate(artifacts):
        where = f"snapshot.artifacts[{index}]"
        artifact = _mapping(artifact_value, where)
        _keys(artifact, _ARTIFACT_KEYS, _ARTIFACT_KEYS, where)
        _identifier(artifact["path"], f"{where}.path")
        digest = artifact["sha256"]
        if (
            not isinstance(digest, str)
            or len(digest) != _HASH_LENGTH
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise ValueError(f"{where}.sha256 must be 64 lowercase hexadecimal characters")

    requirements = _list(root["requirements"], "snapshot.requirements")
    requirement_ids: set[str] = set()
    for index, requirement_value in enumerate(requirements):
        where = f"snapshot.requirements[{index}]"
        requirement = _mapping(requirement_value, where)
        _keys(
            requirement,
            _REQUIREMENT_KEYS,
            {"id", "active", "required_nodes"},
            where,
        )
        requirement_id = _identifier(requirement["id"], f"{where}.id")
        if requirement_id in requirement_ids:
            raise ValueError(f"duplicate requirement id: {requirement_id!r}")
        requirement_ids.add(requirement_id)
        if type(requirement["active"]) is not bool:
            raise ValueError(f"{where}.active must be a boolean")
        _string_list(requirement["required_nodes"], f"{where}.required_nodes")
        if "description" in requirement and not isinstance(requirement["description"], str):
            raise ValueError(f"{where}.description must be a string")

    nodes = _list(root["nodes"], "snapshot.nodes")
    node_ids: set[str] = set()
    for index, node_value in enumerate(nodes):
        where = f"snapshot.nodes[{index}]"
        node = _mapping(node_value, where)
        _keys(node, _NODE_KEYS, _NODE_KEYS, where)
        node_id = _identifier(node["id"], f"{where}.id")
        if node_id in node_ids:
            raise ValueError(f"duplicate node id: {node_id!r}")
        node_ids.add(node_id)
        if not isinstance(node["kind"], str) or node["kind"] not in _KINDS:
            raise ValueError(f"{where}.kind must be one of {sorted(_KINDS)}")
        if not isinstance(node["description"], str):
            raise ValueError(f"{where}.description must be a string")
        _string_list(node["supports"], f"{where}.supports")
        if not isinstance(node["presence"], str) or node["presence"] not in _PRESENCES:
            raise ValueError(f"{where}.presence must be one of {sorted(_PRESENCES)}")
        _mapping(node["evidence"], f"{where}.evidence")

    overlap = node_ids & requirement_ids
    if overlap:
        raise ValueError(f"node and requirement ids overlap: {sorted(overlap)}")

    declared_targets = node_ids | requirement_ids
    for node in nodes:
        unknown = set(node["supports"]) - declared_targets
        if unknown:
            raise ValueError(
                f"node {node['id']!r} supports undeclared targets: {sorted(unknown)}"
            )
    for requirement in requirements:
        required = requirement["required_nodes"]
        mistaken_requirements = set(required) & requirement_ids
        if mistaken_requirements:
            raise ValueError(
                f"requirement {requirement['id']!r}.required_nodes contains requirement ids: "
                f"{sorted(mistaken_requirements)}"
            )
        undeclared = set(required) - node_ids
        if undeclared:
            raise ValueError(
                f"requirement {requirement['id']!r} requires undeclared nodes: "
                f"{sorted(undeclared)}"
            )
    return root


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_purpose_snapshot(path: str | Path) -> dict:
    """Load a snapshot and verify every declared local artifact byte-for-byte."""
    snapshot_path = Path(path)
    try:
        raw = snapshot_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read purpose snapshot {snapshot_path}: {exc}") from exc
    try:
        snapshot = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"invalid JSON in purpose snapshot {snapshot_path}: {exc}") from exc
    _validate_snapshot(snapshot)

    base = snapshot_path.resolve().parent
    for index, artifact in enumerate(snapshot["artifacts"]):
        declared = artifact["path"]
        candidate = base / declared
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError(f"artifact {declared!r} is missing or unreadable: {exc}") from exc
        try:
            resolved.relative_to(base)
        except ValueError:
            raise ValueError(
                f"snapshot.artifacts[{index}].path escapes the snapshot directory: {declared!r}"
            ) from None
        if not resolved.is_file():
            raise ValueError(f"artifact {declared!r} is not a regular file")
        try:
            actual = _sha256(resolved)
        except OSError as exc:
            raise ValueError(f"cannot read artifact {declared!r}: {exc}") from exc
        if actual != artifact["sha256"]:
            raise ValueError(
                f"artifact hash mismatch for {declared!r}: "
                f"expected {artifact['sha256']}, got {actual}"
            )
    return snapshot


def _present_cycles(nodes: dict[str, dict]) -> list[list[str]]:
    """Return deterministic strongly connected components containing a cycle."""
    present = {node_id for node_id, node in nodes.items() if node["presence"] == "present"}
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def visit(node_id: str) -> None:
        nonlocal index
        indices[node_id] = index
        lowlinks[node_id] = index
        index += 1
        stack.append(node_id)
        on_stack.add(node_id)
        targets = sorted(target for target in nodes[node_id]["supports"] if target in present)
        for target in targets:
            if target not in indices:
                visit(target)
                lowlinks[node_id] = min(lowlinks[node_id], lowlinks[target])
            elif target in on_stack:
                lowlinks[node_id] = min(lowlinks[node_id], indices[target])
        if lowlinks[node_id] != indices[node_id]:
            return
        component: list[str] = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node_id:
                break
        component.sort()
        if len(component) > 1 or component[0] in nodes[component[0]]["supports"]:
            components.append(component)

    for node_id in sorted(present):
        if node_id not in indices:
            visit(node_id)
    return sorted(components)


def _root_path(
    start: str,
    nodes: dict[str, dict],
    active_requirements: set[str],
) -> list[str] | None:
    queue = deque([(start, [start])])
    seen = {start}
    while queue:
        node_id, path = queue.popleft()
        for target in sorted(nodes[node_id]["supports"]):
            if target in active_requirements:
                return [*path, target]
            target_node = nodes.get(target)
            if (
                target_node is not None
                and target_node["presence"] == "present"
                and target not in seen
            ):
                seen.add(target)
                queue.append((target, [*path, target]))
    return None


def _terminal_reasons(
    start: str,
    nodes: dict[str, dict],
    requirements: dict[str, dict],
    cycle_by_node: dict[str, list[str]],
) -> list[dict]:
    reasons: set[tuple[str, str]] = set()
    queue = deque([start])
    seen: set[str] = set()
    while queue:
        node_id = queue.popleft()
        if node_id in seen:
            continue
        seen.add(node_id)
        supports = nodes[node_id]["supports"]
        if not supports:
            reasons.add(("no_supports", node_id))
        for target in supports:
            requirement = requirements.get(target)
            if requirement is not None:
                if not requirement["active"]:
                    reasons.add(("inactive_requirement", target))
                continue
            target_node = nodes[target]
            if target_node["presence"] == "absent":
                reasons.add(("absent_target", target))
            elif target_node["presence"] == "unknown":
                reasons.add(("unknown_target", target))
            else:
                queue.append(target)
    reached_cycles = {tuple(cycle_by_node[node_id]) for node_id in seen if node_id in cycle_by_node}
    for cycle in reached_cycles:
        reasons.add(("cycle_without_root", ",".join(cycle)))
    return [{"code": code, "target": target} for code, target in sorted(reasons)]


def assess_purpose(snapshot: dict) -> dict:
    """Classify all declared nodes and report bounded purpose findings.

    Structural validation is performed here, but artifact bytes are verified only by
    :func:`load_purpose_snapshot` because an in-memory value has no trusted base path.
    """
    snapshot = _validate_snapshot(snapshot)
    nodes = {node["id"]: node for node in snapshot["nodes"]}
    requirements = {requirement["id"]: requirement for requirement in snapshot["requirements"]}
    active_requirements = {
        requirement_id
        for requirement_id, requirement in requirements.items()
        if requirement["active"]
    }
    cycles = _present_cycles(nodes)
    cycle_by_node = {node_id: cycle for cycle in cycles for node_id in cycle}

    classifications: dict[str, str] = {}
    paths: dict[str, list[str]] = {}
    for node_id, node in nodes.items():
        if node["presence"] == "absent":
            classifications[node_id] = "ABSENT"
        elif node["presence"] == "unknown":
            classifications[node_id] = "UNKNOWN"
        else:
            path = _root_path(node_id, nodes, active_requirements)
            if path is not None:
                classifications[node_id] = "ROOTED"
                paths[node_id] = path
            else:
                reasons = _terminal_reasons(node_id, nodes, requirements, cycle_by_node)
                classifications[node_id] = (
                    "UNKNOWN" if any(reason["code"] == "unknown_target" for reason in reasons) else "ORPHAN"
                )

    findings: list[dict] = []
    report_nodes: list[dict] = []
    for node in snapshot["nodes"]:
        node_id = node["id"]
        classification = classifications[node_id]
        entry = {
            "id": node_id,
            "classification": classification,
            "evidence": node["evidence"],
        }
        if classification == "ROOTED":
            entry["path"] = paths[node_id]
        elif classification == "ABSENT":
            entry["reasons"] = [{"code": "declared_absent", "target": node_id}]
        elif node["presence"] == "unknown":
            entry["reasons"] = [{"code": "presence_unknown", "target": node_id}]
            findings.append(
                {"code": "node_presence_unknown", "node": node_id, "status": "incomplete"}
            )
        else:
            reasons = _terminal_reasons(node_id, nodes, requirements, cycle_by_node)
            entry["reasons"] = reasons
            findings.append(
                {
                    "code": "unresolved_purpose" if classification == "UNKNOWN" else "orphan_node",
                    "node": node_id,
                    "status": "incomplete" if classification == "UNKNOWN" else "review",
                    "reasons": reasons,
                }
            )
        report_nodes.append(entry)

    for requirement in snapshot["requirements"]:
        if not requirement["active"]:
            continue
        for node_id in requirement["required_nodes"]:
            presence = nodes[node_id]["presence"]
            if presence == "absent":
                findings.append(
                    {
                        "code": "missing_required_node",
                        "requirement": requirement["id"],
                        "node": node_id,
                        "status": "review",
                    }
                )
            elif presence == "unknown":
                findings.append(
                    {
                        "code": "required_node_unknown",
                        "requirement": requirement["id"],
                        "node": node_id,
                        "status": "incomplete",
                    }
                )

    if not nodes:
        findings.append(
            {
                "code": "empty_scope",
                "status": "incomplete",
                "reason": "the valid scoped capture declares no nodes",
            }
        )

    cycle_reports = []
    for cycle in cycles:
        rooted = any(classifications[node_id] == "ROOTED" for node_id in cycle)
        cycle_reports.append({"nodes": cycle, "rooted": rooted})

    statuses = {finding["status"] for finding in findings}
    status = "incomplete" if "incomplete" in statuses else "review" if "review" in statuses else "no_findings"
    class_counts = Counter(classifications.values())
    counts = {
        "nodes": len(nodes),
        "requirements": len(requirements),
        "findings": len(findings),
        "cycles": len(cycles),
        "ABSENT": class_counts["ABSENT"],
        "ROOTED": class_counts["ROOTED"],
        "ORPHAN": class_counts["ORPHAN"],
        "UNKNOWN": class_counts["UNKNOWN"],
    }
    return {
        "schema": REPORT_SCHEMA,
        "status": status,
        "nodes": report_nodes,
        "findings": findings,
        "cycles": cycle_reports,
        "coverage": snapshot["source"]["coverage"],
        "scope": {
            "dependencies": "declared dependencies only",
            "geometry_and_physical_function": "not proved",
            "material_removal_approval": "not granted",
        },
        "counts": counts,
    }


def _incomplete_report(error: Exception) -> dict:
    return {
        "schema": REPORT_SCHEMA,
        "status": "incomplete",
        "nodes": [],
        "findings": [{"code": "invalid_input", "status": "incomplete", "reason": str(error)}],
        "cycles": [],
        "coverage": "unavailable: invalid input",
        "scope": {
            "dependencies": "declared dependencies only",
            "geometry_and_physical_function": "not proved",
            "material_removal_approval": "not granted",
        },
        "counts": {
            "nodes": 0,
            "requirements": 0,
            "findings": 1,
            "cycles": 0,
            "ABSENT": 0,
            "ROOTED": 0,
            "ORPHAN": 0,
            "UNKNOWN": 0,
        },
    }


def _write_report(report: dict, output: str | None) -> None:
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(rendered)
    else:
        Path(output).write_text(rendered, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", help="purpose snapshot JSON")
    parser.add_argument("--output", help="write the purpose report JSON to this path")
    args = parser.parse_args(argv)
    try:
        report = assess_purpose(load_purpose_snapshot(args.snapshot))
    except (ValueError, OSError) as exc:
        report = _incomplete_report(exc)
    _write_report(report, args.output)
    return {"no_findings": 0, "review": 1, "incomplete": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
