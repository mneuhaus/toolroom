#!/usr/bin/env python3
"""Build and inspect deterministic native Bambu 3MF print packages.

The tool deliberately stops at file preparation.  It never dispatches a print and
its automated result never substitutes for layer, fit, or assembly review.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any
import xml.etree.ElementTree as ET
import zipfile


REPORT_VERSION = 1
ROUTINE_KEYS = (
    "machine_start_gcode",
    "machine_end_gcode",
    "layer_change_gcode",
    "time_lapse_gcode",
    "change_filament_gcode",
)
PENDING_REVIEWS = (
    "critical actual-layer and deposited-path review",
    "critical physical fit review",
    "critical physical assembly review",
)


class PackageError(RuntimeError):
    """A deterministic input, slicer, or package validation error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _read_json(path: Path, description: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageError(f"cannot read {description} JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise PackageError(f"{description} JSON must be an object: {path}")
    return data


def _check(name: str, status: str, evidence: Any, scope: str) -> dict[str, Any]:
    if status not in {"pass", "fail", "incomplete"}:
        raise ValueError(status)
    return {"name": name, "status": status, "scope": scope, "evidence": evidence}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attr_local(element: ET.Element, name: str) -> str | None:
    for key, value in element.attrib.items():
        if _local_name(key) == name:
            return value
    return None


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _descendants(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element.iter() if _local_name(child.tag) == name]


def _metadata(element: ET.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    for child in _children(element, "metadata"):
        key = child.get("key")
        value = child.get("value")
        if key is not None and value is not None:
            result[key] = value
    return result


def _matrix(text: str | None) -> tuple[tuple[float, ...], ...]:
    values = [float(value) for value in (text or "1 0 0 0 1 0 0 0 1 0 0 0").split()]
    if len(values) != 12 or not all(math.isfinite(value) for value in values):
        raise PackageError(f"unsupported 3MF transform: {text!r}")
    # 3MF stores a row-vector affine transform: the final three values translate.
    return (
        (values[0], values[1], values[2], 0.0),
        (values[3], values[4], values[5], 0.0),
        (values[6], values[7], values[8], 0.0),
        (values[9], values[10], values[11], 1.0),
    )


def _multiply(left: tuple[tuple[float, ...], ...], right: tuple[tuple[float, ...], ...]):
    return tuple(
        tuple(sum(left[row][k] * right[k][column] for k in range(4)) for column in range(4))
        for row in range(4)
    )


def _transform(point: tuple[float, float, float], matrix):
    vector = (*point, 1.0)
    return tuple(sum(vector[k] * matrix[k][column] for k in range(4)) for column in range(3))


def _flat_matrix(matrix) -> list[float]:
    values = [matrix[row][column] for row in range(4) for column in range(3)]
    return [round(value, 9) for value in values]


def _zip_member_path(current: str, reference: str | None) -> str:
    if not reference:
        return current
    raw = reference.replace("\\", "/")
    if raw.startswith("/"):
        candidate = PurePosixPath(raw[1:])
    else:
        candidate = PurePosixPath(current).parent / raw
    normalized = PurePosixPath(os.path.normpath(str(candidate)))
    if str(normalized).startswith("../") or str(normalized) == "..":
        raise PackageError(f"3MF component path escapes archive: {reference}")
    return str(normalized)


def _geometry_report(archive: zipfile.ZipFile) -> dict[str, Any]:
    """Resolve standard 3MF components into effective, positioned mesh instances."""
    errors: list[str] = []
    instances: list[dict[str, Any]] = []
    models: dict[str, tuple[ET.Element, dict[str, ET.Element]]] = {}

    def model(member: str):
        if member in models:
            return models[member]
        if member not in archive.namelist():
            raise PackageError(f"missing referenced 3MF model member: {member}")
        root = ET.fromstring(archive.read(member))
        if _local_name(root.tag) != "model":
            raise PackageError(f"3MF member is not a model: {member}")
        if root.get("unit", "millimeter") != "millimeter":
            raise PackageError(f"unsupported units in {member}; normalize explicitly to millimeters")
        resources = next(iter(_children(root, "resources")), None)
        if resources is None:
            raise PackageError(f"3MF model has no resources: {member}")
        objects = {obj.get("id", ""): obj for obj in _children(resources, "object")}
        models[member] = (root, objects)
        return models[member]

    def walk(member: str, object_id: str, effective, active: tuple[tuple[str, str], ...]):
        key = (member, object_id)
        if key in active:
            raise PackageError(f"cyclic 3MF component graph at {member} object {object_id}")
        _, objects = model(member)
        obj = objects.get(object_id)
        if obj is None:
            raise PackageError(f"missing 3MF object {object_id} in {member}")
        meshes = _children(obj, "mesh")
        components_nodes = _children(obj, "components")
        if len(meshes) + len(components_nodes) != 1:
            raise PackageError(
                f"object {object_id} in {member} must contain exactly one mesh or components node"
            )
        if meshes:
            vertices_node = next(iter(_children(meshes[0], "vertices")), None)
            triangles_node = next(iter(_children(meshes[0], "triangles")), None)
            if vertices_node is None or triangles_node is None:
                raise PackageError(f"mesh {object_id} in {member} lacks vertices or triangles")
            vertices = []
            for vertex in _children(vertices_node, "vertex"):
                point = tuple(float(vertex.get(axis, "nan")) for axis in "xyz")
                if not all(math.isfinite(value) for value in point):
                    raise PackageError(f"mesh {object_id} contains an invalid vertex")
                vertices.append(point)
            triangles = []
            for triangle in _children(triangles_node, "triangle"):
                indices = tuple(int(triangle.get(axis, "-1")) for axis in ("v1", "v2", "v3"))
                if any(index < 0 or index >= len(vertices) for index in indices):
                    raise PackageError(f"mesh {object_id} contains an invalid triangle")
                triangles.append(indices)
            if not vertices or not triangles:
                raise PackageError(f"mesh {object_id} is empty")
            positioned = [_transform(vertex, effective) for vertex in vertices]
            rounded = [[round(value, 7) for value in vertex] for vertex in positioned]
            payload = {"vertices": rounded, "triangles": triangles}
            bounds = [
                [round(min(vertex[axis] for vertex in positioned), 7) for axis in range(3)],
                [round(max(vertex[axis] for vertex in positioned), 7) for axis in range(3)],
            ]
            instances.append(
                {
                    "root_object_id": active[0][1] if active else object_id,
                    "mesh_object_id": object_id,
                    "model_member": member,
                    "effective_transform": _flat_matrix(effective),
                    "positioned_bounds_mm": bounds,
                    "positioned_mesh_sha256": _canonical_hash(payload),
                    "vertex_count": len(vertices),
                    "triangle_count": len(triangles),
                }
            )
            return
        for component in _children(components_nodes[0], "component"):
            child_id = component.get("objectid")
            if not child_id:
                raise PackageError(f"component in {member} object {object_id} lacks objectid")
            child_member = _zip_member_path(member, _attr_local(component, "path"))
            child_effective = _multiply(_matrix(component.get("transform")), effective)
            walk(child_member, child_id, child_effective, (*active, key))
        if not _children(components_nodes[0], "component"):
            raise PackageError(f"empty components node in {member}")

    try:
        root, _ = model("3D/3dmodel.model")
        builds = _children(root, "build")
        if len(builds) != 1:
            raise PackageError("root 3MF model must have exactly one build")
        items = _children(builds[0], "item")
        if not items:
            raise PackageError("root 3MF build has no items")
        for item in items:
            object_id = item.get("objectid")
            if not object_id:
                raise PackageError("root 3MF build item lacks objectid")
            walk("3D/3dmodel.model", object_id, _matrix(item.get("transform")), ())
    except (ET.ParseError, ValueError, PackageError) as exc:
        errors.append(str(exc))
    return {
        "analysis_complete": not errors,
        "errors": errors,
        "mesh_instance_count": len(instances),
        "instances": instances,
        "pose_signature": _canonical_hash(sorted(row["positioned_mesh_sha256"] for row in instances))
        if not errors
        else None,
    }


def _inspect(path: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    details: dict[str, Any] = {}
    try:
        with zipfile.ZipFile(path) as archive:
            corrupt = archive.testzip()
            checks.append(
                _check(
                    "3mf_archive_integrity",
                    "pass" if corrupt is None else "fail",
                    {"first_corrupt_member": corrupt},
                    "all ZIP members",
                )
            )
            names = archive.namelist()
            duplicate_names = sorted(name for name, count in Counter(names).items() if count > 1)
            checks.append(
                _check(
                    "unique_archive_members",
                    "pass" if not duplicate_names else "fail",
                    {"duplicates": duplicate_names},
                    "3MF archive member names",
                )
            )
            geometry = _geometry_report(archive)
            details["geometry"] = geometry
            checks.append(
                _check(
                    "effective_mesh_poses",
                    "pass" if geometry["analysis_complete"] else "incomplete",
                    {
                        "mesh_instance_count": geometry["mesh_instance_count"],
                        "pose_signature": geometry["pose_signature"],
                        "errors": geometry["errors"],
                    },
                    "standard 3MF build items, component transforms, vertices, and triangles",
                )
            )

            required = {"Metadata/model_settings.config", "Metadata/project_settings.config", "Metadata/slice_info.config"}
            missing = sorted(required - set(names))
            checks.append(
                _check(
                    "native_metadata_present",
                    "pass" if not missing else "fail",
                    {"missing": missing},
                    "Bambu model, project, and per-plate slice metadata",
                )
            )
            if missing:
                details["plates"] = []
                details["project_settings"] = None
            else:
                project = json.loads(archive.read("Metadata/project_settings.config"))
                if not isinstance(project, dict):
                    raise PackageError("project settings must be a JSON object")
                details["project_settings"] = project
                model_settings = ET.fromstring(archive.read("Metadata/model_settings.config"))
                slice_info = ET.fromstring(archive.read("Metadata/slice_info.config"))
                model_plates = _children(model_settings, "plate")
                slice_plates = _children(slice_info, "plate")
                slice_by_index = {_metadata(plate).get("index"): plate for plate in slice_plates}
                plate_rows = []
                model_ids = [_metadata(p).get("plater_id") for p in model_plates]
                all_ok = (bool(model_plates) and len(model_plates) == len(slice_plates)
                          and len(set(model_ids)) == len(model_ids)
                          and set(model_ids) == set(slice_by_index))
                assigned_roots = []
                for sequence, plate in enumerate(model_plates, 1):
                    meta = _metadata(plate)
                    plate_id = meta.get("plater_id")
                    expected_ids = [
                        _metadata(instance).get("identify_id")
                        for instance in _children(plate, "model_instance")
                    ]
                    assigned_roots.extend(_metadata(i).get("object_id") for i in _children(plate, "model_instance"))
                    slice_plate = slice_by_index.get(plate_id)
                    reasons: list[str] = []
                    if not plate_id:
                        reasons.append("missing plater_id")
                    if slice_plate is None:
                        reasons.append("missing matching slice_info plate")
                        slice_objects: list[ET.Element] = []
                        slice_meta: dict[str, str] = {}
                    else:
                        slice_meta = _metadata(slice_plate)
                        slice_objects = _children(slice_plate, "object")
                    if slice_meta.get("outside") != "false":
                        reasons.append(f"outside flag is {slice_meta.get('outside')!r}")
                    skipped = [obj.get("identify_id") for obj in slice_objects if obj.get("skipped") != "false"]
                    if skipped:
                        reasons.append(f"objects missing skipped=false: {skipped}")
                    actual_ids = [obj.get("identify_id") for obj in slice_objects]
                    if (not expected_ids or None in expected_ids or len(set(expected_ids)) != len(expected_ids)
                            or Counter(expected_ids) != Counter(actual_ids)):
                        reasons.append(f"object identifiers differ: expected {expected_ids}, got {actual_ids}")
                    gcode = meta.get("gcode_file")
                    if not gcode or gcode not in names or not archive.getinfo(gcode).file_size:
                        reasons.append(f"missing or empty plate G-code: {gcode!r}")
                    plate_json = f"Metadata/plate_{plate_id or sequence}.json"
                    bbox_count = None
                    if plate_json not in names:
                        reasons.append(f"missing per-plate JSON: {plate_json}")
                    else:
                        plate_data = json.loads(archive.read(plate_json))
                        bbox = plate_data.get("bbox_objects") if isinstance(plate_data, dict) else None
                        if not isinstance(bbox, list):
                            reasons.append(f"invalid bbox_objects in {plate_json}")
                        else:
                            bbox_count = len(bbox)
                            if bbox_count != len(expected_ids):
                                reasons.append(
                                    f"per-plate object count differs: model={len(expected_ids)}, json={bbox_count}"
                                )
                    if gcode and gcode in names:
                        md5_member = gcode + ".md5"
                        if md5_member in names:
                            expected_md5 = archive.read(md5_member).decode(errors="replace").strip().lower()
                            actual_md5 = hashlib.md5(archive.read(gcode), usedforsecurity=False).hexdigest()
                            if expected_md5 != actual_md5:
                                reasons.append("G-code MD5 differs from sidecar")
                    plate_rows.append(
                        {
                            "plate_id": plate_id,
                            "model_instance_count": len(expected_ids),
                            "slice_object_count": len(slice_objects),
                            "bbox_object_count": bbox_count,
                            "outside": slice_meta.get("outside"),
                            "skipped_identify_ids": skipped,
                            "gcode_file": gcode,
                            "problems": reasons,
                        }
                    )
                    all_ok = all_ok and not reasons
                build_root = ET.fromstring(archive.read("3D/3dmodel.model"))
                built_ids = [item.get("objectid") for b in _children(build_root, "build") for item in _children(b, "item")]
                if Counter(assigned_roots) != Counter(built_ids):
                    checks.append(_check("build_items_assigned_to_plates", "fail",
                                         {"build": built_ids, "assigned": assigned_roots}, "every build item appears on a plate"))
                    all_ok = False
                details["plates"] = plate_rows
                checks.append(
                    _check(
                        "all_plates_sliced_and_consistent",
                        "pass" if all_ok else "fail",
                        {"model_plate_count": len(model_plates), "slice_plate_count": len(slice_plates), "plates": plate_rows},
                        "every model plate, G-code member, slice object, outside/skipped flag, and plate JSON count",
                    )
                )
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError, ValueError, json.JSONDecodeError, PackageError) as exc:
        checks.append(_check("3mf_read", "fail", {"error": str(exc)}, "requested 3MF file"))

    statuses = {check["status"] for check in checks}
    status = "review" if "fail" in statuses else "incomplete" if "incomplete" in statuses else "no_findings"
    return {
        "schema_version": REPORT_VERSION,
        "operation": "inspect",
        "status": status,
        "automated_scope": "archive, native metadata, plate consistency, and standard 3MF effective mesh poses",
        "checks": checks,
        "details": details,
        "pending_critical_reviews": list(PENDING_REVIEWS),
        "dispatched": False,
    }


def _resolve_job(job_path: Path) -> dict[str, Any]:
    job = _read_json(job_path, "job")
    allowed = {"source", "slicer", "profiles", "timeout_seconds", "resource_paths"}
    extra = sorted(set(job) - allowed)
    if extra:
        raise PackageError(f"unsupported job keys: {extra}")
    profiles = job.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != {"machine", "process", "filaments"}:
        raise PackageError("profiles must contain exactly machine, process, and filaments")
    filaments = profiles["filaments"]
    if not isinstance(filaments, list) or not filaments or not all(isinstance(item, str) for item in filaments):
        raise PackageError("profiles.filaments must be a non-empty array of paths")
    if not isinstance(job.get("source"), str) or not isinstance(job.get("slicer"), str):
        raise PackageError("source and slicer must be paths")
    if not isinstance(profiles["machine"], str) or not isinstance(profiles["process"], str):
        raise PackageError("machine and process must be paths")
    base = job_path.parent.resolve()

    def resolve(value: str) -> Path:
        path = Path(value)
        return (base / path).resolve() if not path.is_absolute() else path.resolve()

    timeout = job.get("timeout_seconds", 900)
    if not isinstance(timeout, int) or timeout < 1 or timeout > 7200:
        raise PackageError("timeout_seconds must be an integer from 1 through 7200")
    resolved = {
        "source": resolve(job["source"]),
        "slicer": resolve(job["slicer"]),
        "machine": resolve(profiles["machine"]),
        "process": resolve(profiles["process"]),
        "filaments": [resolve(path) for path in filaments],
        "timeout_seconds": timeout,
        "job": job_path.resolve(),
        "resource_paths": [resolve(text) for text in job.get("resource_paths", [])],
    }
    for name in ("source", "slicer", "machine", "process"):
        path = resolved[name]
        if not path.is_file():
            raise PackageError(f"{name} is not a file: {path}")
    for path in resolved["filaments"]:
        if not path.is_file():
            raise PackageError(f"filament is not a file: {path}")
    if resolved["source"].suffix.lower() != ".3mf":
        raise PackageError("source must be an authoritative posed .3mf")
    return resolved


def _inputs(resolved: dict[str, Any]) -> dict[str, dict[str, str]]:
    paths = {
        "job": resolved["job"],
        "source": resolved["source"],
        "slicer": resolved["slicer"],
        "machine": resolved["machine"],
        "process": resolved["process"],
        "tool": Path(__file__).resolve(),
    }
    paths.update({f"filament_{index}": path for index, path in enumerate(resolved["filaments"], 1)})
    resources = list(resolved["resource_paths"])
    exe = resolved["slicer"]
    if exe.parent.name == "MacOS" and (exe.parent.parent / "Resources").is_dir():
        resources.append(exe.parent.parent / "Resources")
    for i, path in enumerate(resources):
        if path.is_file():
            paths[f"resource_{i}"] = path
        elif path.is_dir():
            for file in sorted(path.rglob("*")):
                if file.is_file():
                    paths[f"resource_{i}/{file.relative_to(path)}"] = file
        else:
            raise PackageError(f"slicer resource is missing: {path}")
    return {name: {"path": str(path), "sha256": _sha256(path)} for name, path in sorted(paths.items())}


def _artifact_hashes(directory: Path) -> dict[str, str]:
    return {
        str(path.relative_to(directory)): _sha256(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.name != "artifacts.json"
    }


def _verify_cache(directory: Path) -> dict[str, Any]:
    manifest_path = directory / "artifacts.json"
    manifest = _read_json(manifest_path, "artifact manifest")
    expected = manifest.get("sha256")
    if not isinstance(expected, dict):
        raise PackageError(f"invalid artifact manifest: {manifest_path}")
    actual = _artifact_hashes(directory)
    if actual != expected:
        raise PackageError(f"immutable cached package failed hash verification: {directory}")
    return manifest


def _run(command: list[str], log_path: Path, timeout: int) -> None:
    started = time.monotonic()
    # Native slicers can emit result.json in cwd; isolate that side effect.
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False, cwd=log_path.parent)
        log_path.write_text(
            json.dumps({"command": command, "returncode": completed.returncode, "elapsed_seconds": time.monotonic()-started}, indent=2)
            + "\n\n--- stdout ---\n"
            + completed.stdout
            + "\n--- stderr ---\n"
            + completed.stderr
        )
    except subprocess.TimeoutExpired as exc:
        decode = lambda value: value.decode(errors="replace") if isinstance(value, bytes) else (value or "")
        log_path.write_text(
            json.dumps({"command": command, "timeout_seconds": timeout}, indent=2)
            + "\n\n--- stdout ---\n"
            + decode(exc.stdout)
            + "\n--- stderr ---\n"
            + decode(exc.stderr)
        )
        raise PackageError(f"slicer timed out after {timeout}s; see {log_path.name}") from exc
    if completed.returncode:
        raise PackageError(f"slicer exited {completed.returncode}; see {log_path.name}")


def _expected_profiles(resolved: dict[str, Any]) -> dict[str, Any]:
    machine = _read_json(resolved["machine"], "machine profile")
    process = _read_json(resolved["process"], "process profile")
    filaments = [_read_json(path, "filament profile") for path in resolved["filaments"]]
    for expected_type, row, path in [
        ("machine", machine, resolved["machine"]),
        ("process", process, resolved["process"]),
        *[("filament", row, path) for row, path in zip(filaments, resolved["filaments"])],
    ]:
        if row.get("type") != expected_type or not row.get("name"):
            raise PackageError(f"resolved profile lacks type={expected_type!r} and name: {path}")
        if row.get("include"):
            raise PackageError(f"profile has unresolved includes: {path}")
    missing_routines = [key for key in ROUTINE_KEYS if not machine.get(key)]
    if missing_routines:
        raise PackageError(f"resolved machine profile lacks native routines: {missing_routines}")
    return {"machine": machine, "process": process, "filaments": filaments}


def _profile_checks(native: dict[str, Any], reimport: dict[str, Any], profiles: dict[str, Any]):
    checks = []
    native_settings = native.get("details", {}).get("project_settings")
    reimport_settings = reimport.get("details", {}).get("project_settings")
    if not isinstance(native_settings, dict) or not isinstance(reimport_settings, dict):
        return [
            _check(
                "profiles_preserved_on_reimport",
                "fail",
                {"reason": "project settings unavailable"},
                "native and no-override reimport project settings",
            )
        ]
    expected_identity = {
        "printer_settings_id": profiles["machine"]["name"],
        "print_settings_id": profiles["process"]["name"],
        "filament_settings_id": [row["name"] for row in profiles["filaments"]],
    }
    identity_diff = {
        key: {"expected": value, "actual": native_settings.get(key)}
        for key, value in expected_identity.items()
        if native_settings.get(key) != value
    }
    checks.append(
        _check(
            "resolved_profile_identity_applied",
            "pass" if not identity_diff else "fail",
            {"expected": expected_identity, "differences": identity_diff},
            "native export profile identifiers",
        )
    )
    # Profile names alone do not prove that task-specific values were applied.
    ignored = {"name", "type", "from", "inherits", "include", "version", "setting_id", "instantiation",
               "compatible_printers", "compatible_printers_condition", "compatible_prints", "compatible_prints_condition"}
    expected_values = {}
    for row in [profiles["machine"], profiles["process"]]:
        expected_values.update({k: v for k, v in row.items() if k not in ignored})
    for k in set().union(*(row.keys() for row in profiles["filaments"])) - ignored:
        vals = [row.get(k) for row in profiles["filaments"]]
        expected_values[k] = [v for value in vals for v in (value if isinstance(value, list) else [value])]
    differences = {k: {"expected": v, "actual": native_settings.get(k)}
                   for k, v in expected_values.items() if native_settings.get(k) != v}
    checks.append(_check("resolved_profile_values_applied", "fail" if differences else "pass", differences,
                         "resolved task values including temperatures, layer settings and material; normalization differences require review"))
    routine_diff = {
        key: {
            "expected_sha256": hashlib.sha256(profiles["machine"][key].encode()).hexdigest(),
            "actual_sha256": hashlib.sha256(str(native_settings.get(key, "")).encode()).hexdigest(),
        }
        for key in ROUTINE_KEYS
        if native_settings.get(key) != profiles["machine"][key]
    }
    checks.append(
        _check(
            "native_machine_routines_intact",
            "pass" if not routine_diff else "fail",
            {"routine_sha256_differences": routine_diff},
            "five resolved native machine G-code routines in the native export",
        )
    )
    differing_keys = sorted(
        key for key in set(native_settings) | set(reimport_settings) if native_settings.get(key) != reimport_settings.get(key)
    )
    checks.append(
        _check(
            "profiles_preserved_on_reimport",
            "pass" if not differing_keys else "fail",
            {"differing_project_setting_keys": differing_keys},
            "complete project settings from native export versus no-override reimport",
        )
    )
    return checks


def _pose_comparison(native: dict[str, Any], reimport: dict[str, Any]):
    left = native.get("details", {}).get("geometry", {})
    right = reimport.get("details", {}).get("geometry", {})
    if not left.get("analysis_complete") or not right.get("analysis_complete"):
        return _check(
            "effective_mesh_poses_preserved_on_reimport",
            "incomplete",
            {"native_errors": left.get("errors", []), "reimport_errors": right.get("errors", [])},
            "standard 3MF component graph and positioned mesh vertices",
        )
    equal = left.get("pose_signature") == right.get("pose_signature")
    return _check(
        "effective_mesh_poses_preserved_on_reimport",
        "pass" if equal else "fail",
        {
            "native": left.get("pose_signature"),
            "reimport": right.get("pose_signature"),
            "native_instance_count": left.get("mesh_instance_count"),
            "reimport_instance_count": right.get("mesh_instance_count"),
        },
        "effective transformed vertices and triangle topology for every mesh instance",
    )


def _build(job_path: Path, out_root: Path) -> tuple[dict[str, Any], Path, bool]:
    resolved = _resolve_job(job_path)
    inputs = _inputs(resolved)
    key = _canonical_hash({name: row["sha256"] for name, row in inputs.items()})
    destination = out_root.resolve() / key
    out_root.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        manifest = _verify_cache(destination)
        report = _read_json(destination / "report.json", "cached report")
        if manifest.get("cache_key") != key:
            raise PackageError(f"cached package key mismatch: {destination}")
        return report, destination, True

    stage = Path(tempfile.mkdtemp(prefix=f".{key[:12]}-", dir=out_root.resolve()))
    (stage / "logs").mkdir()
    report: dict[str, Any] = {
        "schema_version": REPORT_VERSION,
        "operation": "build",
        "status": "incomplete",
        "cache_key": key,
        "inputs": inputs,
        "checks": [],
        "pending_critical_reviews": list(PENDING_REVIEWS),
        "dispatched": False,
    }
    try:
        profiles = _expected_profiles(resolved)
        with zipfile.ZipFile(resolved["source"]) as archive:
            source_geometry = _geometry_report(archive)
        if not source_geometry["analysis_complete"]:
            raise PackageError(f"source geometry analysis incomplete: {source_geometry['errors']}")
        native_path = stage / "native.3mf"
        reimport_path = stage / "reimport.3mf"
        settings = f"{resolved['machine']};{resolved['process']}"
        filaments = ";".join(str(path) for path in resolved["filaments"])
        native_command = [
            str(resolved["slicer"]), "--arrange", "0", "--orient", "0", "--slice", "0",
            "--load-settings", settings, "--load-filaments", filaments,
            "--export-3mf", str(native_path), str(resolved["source"]),
        ]
        _run(native_command, stage / "logs/native.log", resolved["timeout_seconds"])
        if not native_path.is_file():
            raise PackageError("native slicer command succeeded without producing native.3mf")
        reimport_command = [
            str(resolved["slicer"]), "--arrange", "0", "--orient", "0", "--slice", "0",
            "--export-3mf", str(reimport_path), str(native_path),
        ]
        _run(reimport_command, stage / "logs/reimport.log", resolved["timeout_seconds"])
        if not reimport_path.is_file():
            raise PackageError("reimport slicer command succeeded without producing reimport.3mf")
        native_report = _inspect(native_path)
        reimport_report = _inspect(reimport_path)
        report["native"] = native_report
        report["reimport"] = reimport_report
        report["checks"] = [
            _check(
                "native_export",
                "pass" if native_report["status"] == "no_findings" else native_report["status"].replace("review", "fail"),
                {"status": native_report["status"]},
                "native profile-loaded slice/export",
            ),
            _check(
                "no_override_reimport",
                "pass" if reimport_report["status"] == "no_findings" else reimport_report["status"].replace("review", "fail"),
                {"status": reimport_report["status"]},
                "reimport/reslice with no settings or filament overrides",
            ),
            *_profile_checks(native_report, reimport_report, profiles),
            _pose_comparison(native_report, reimport_report),
        ]
        source_check = _pose_comparison({"details": {"geometry": source_geometry}}, native_report)
        source_check["name"] = "authoritative_source_geometry_preserved"
        source_check["scope"] = "source posed 3MF compared with native output; exact topology/pose signature, conservative on reindexing"
        report["checks"].append(source_check)
        if _inputs(resolved) != inputs:
            raise PackageError("inputs changed during slicer run; result is not bound to the current source")
        statuses = {check["status"] for check in report["checks"]}
        report["status"] = "review" if "fail" in statuses else "incomplete" if "incomplete" in statuses else "no_findings"
    except Exception as exc:
        report["status"] = "incomplete"
        report["checks"].append(
            _check("build_completed", "fail", {"error": str(exc)}, "profile preflight and two native slicer runs")
        )
        report["error"] = str(exc)
    report["artifacts"] = {
        name: name for name in ("native.3mf", "reimport.3mf", "logs/native.log", "logs/reimport.log") if (stage / name).is_file()
    }
    (stage / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    manifest = {"cache_key": key, "sha256": _artifact_hashes(stage)}
    (stage / "artifacts.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    try:
        stage.rename(destination)
    except FileExistsError:
        shutil.rmtree(stage)
        _verify_cache(destination)
        report = _read_json(destination / "report.json", "cached report")
        return report, destination, True
    return report, destination, False


def _write_inspection(source: Path, out_root: Path) -> tuple[dict[str, Any], Path, bool]:
    source = source.resolve()
    if not source.is_file():
        raise PackageError(f"3MF does not exist: {source}")
    source_hash = _sha256(source)
    key = _canonical_hash({"source": source_hash, "tool": _sha256(Path(__file__).resolve())})
    destination = out_root.resolve() / key
    out_root.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        _verify_cache(destination)
        return _read_json(destination / "report.json", "cached report"), destination, True
    stage = Path(tempfile.mkdtemp(prefix=f".{key[:12]}-", dir=out_root.resolve()))
    report = _inspect(source)
    report["source"] = {"path": str(source), "sha256": source_hash}
    report["cache_key"] = key
    (stage / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (stage / "artifacts.json").write_text(
        json.dumps({"cache_key": key, "sha256": _artifact_hashes(stage)}, indent=2, sort_keys=True) + "\n"
    )
    try:
        stage.rename(destination)
    except FileExistsError:
        shutil.rmtree(stage)
        _verify_cache(destination)
        return _read_json(destination / "report.json", "cached report"), destination, True
    return report, destination, False


def _print_summary(report: dict[str, Any], directory: Path, reused: bool) -> None:
    summary = {
        "status": report["status"],
        "report": str(directory / "report.json"),
        "artifacts": report.get("artifacts", {}),
        "cache": "reused" if reused else "created",
    }
    print(json.dumps(summary, separators=(",", ":"), sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="inspect an existing native 3MF")
    inspect_parser.add_argument("file", type=Path)
    inspect_parser.add_argument("--out", required=True, type=Path)
    build_parser = subparsers.add_parser("build", help="slice and verify an authoritative posed 3MF")
    build_parser.add_argument("job", type=Path)
    build_parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            report, destination, reused = _write_inspection(args.file, args.out)
        else:
            report, destination, reused = _build(args.job, args.out)
        _print_summary(report, destination, reused)
        return {"no_findings": 0, "review": 1, "incomplete": 2}[report["status"]]
    except PackageError as exc:
        print(json.dumps({"status": "incomplete", "error": str(exc)}, separators=(",", ":")), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
