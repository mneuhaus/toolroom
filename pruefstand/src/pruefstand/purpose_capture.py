"""Bind final native purpose witnesses to a frozen assembly, entirely offline.

The initial adapter supports one solid per captured Part Studio and at most one
occurrence per semantic catalog. Multiple occurrences need explicit instance
namespaces; this adapter reports unknown instead of silently choosing one.
"""
from __future__ import annotations

from copy import deepcopy
import math

from .purpose import assess_purpose


_IDENTITY = ("document", "microversion", "element", "configuration", "part")


def _nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _count(value, label):
    # FeatureScript serializes integer counts as JSON floating-point numbers.
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or value != int(value):
        raise ValueError(f"{label} must be a nonnegative integer count")
    return int(value)


def _finite_numbers(values, length, label):
    if not isinstance(values, list) or len(values) != length or any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for v in values
    ):
        raise ValueError(f"{label} must contain {length} finite numbers")


def _identity(value, prefix=""):
    if not isinstance(value, dict):
        raise ValueError("source identity must be an object")
    return tuple(_nonempty(value.get(prefix + k), prefix + k) for k in _IDENTITY)


def _validate_occurrence(occurrence):
    _identity(occurrence)
    path = occurrence.get("path")
    if not isinstance(path, list) or not path:
        raise ValueError("occurrence.path must be a nonempty instance path")
    for member in path:
        _nonempty(member, "occurrence.path member")
    _finite_numbers(occurrence.get("transform_m"), 16, "occurrence.transform_m")


def bind_native_purposes(
    captures: list[dict],
    occurrences: list[dict],
    *,
    assembly_source: dict,
    assembly_complete: bool,
    requirements: list[dict],
    artifacts: list[dict],
    supplemental_nodes: list[dict] | None = None,
) -> dict:
    """Return a ``pruefstand.purpose/1`` snapshot; do not perform any API access.

    Captures use ``toolroom.native-purpose/1`` from capture-purpose.fs, enriched
    with ``source_document/microversion/element/configuration/part`` by capture.
    Occurrences have those five identity fields without ``source_``, a full
    ``path`` and a 16-number ``transform_m``. Artifact byte verification remains
    the responsibility of ``load_purpose_snapshot`` after writing the result.
    ``supplemental_nodes`` may describe separately evidenced purchased parts or
    external supports. Their presence/evidence is supplied by the caller, not
    inferred from the native captures. All nodes share one validated namespace.
    """
    if not isinstance(captures, list) or not isinstance(occurrences, list):
        raise ValueError("captures and occurrences must be lists")
    if not isinstance(assembly_source, dict) or type(assembly_complete) is not bool:
        raise ValueError("assembly_source must be an object and assembly_complete a boolean")
    for key in ("document", "microversion", "element", "configuration"):
        _nonempty(assembly_source.get(key), "assembly_source." + key)
    paths = set()
    for occurrence in occurrences:
        _validate_occurrence(occurrence)
        path = tuple(occurrence["path"])
        if path in paths:
            raise ValueError(f"duplicate occurrence path: {path}")
        paths.add(path)

    nodes = []
    for capture in captures:
        if not isinstance(capture, dict) or capture.get("schema") != "toolroom.native-purpose/1":
            raise ValueError("unsupported native purpose capture")
        identity = _identity(capture, "source_")
        _nonempty(capture.get("coverage"), "native coverage")
        if not isinstance(capture.get("nodes"), list) or not isinstance(capture.get("parts"), list):
            raise ValueError("native nodes and parts must be lists")
        if len(capture["parts"]) != 1 or not isinstance(capture["parts"][0], dict) or capture["parts"][0].get("topology_id") != identity[-1]:
            raise ValueError("this adapter requires one explicitly identified solid per capture")
        # A changed revision/configuration of the same source part is unresolved,
        # not evidence that the semantic module was removed.
        possible = [o for o in occurrences if (o["document"], o["element"], o["part"]) == (identity[0], identity[2], identity[4])]
        exact = [o for o in possible if _identity(o) == identity]
        for node in capture["nodes"]:
            if not isinstance(node, dict) or type(node.get("generated")) is not bool:
                raise ValueError("native node.generated must be a boolean")
            count = _count(node.get("entity_count"), "entity_count")
            owners = _count(node.get("owner_count"), "owner_count")
            initial = _count(node.get("initial_entity_count"), "initial_entity_count")
            owner_ids = node.get("owner_ids")
            if not isinstance(owner_ids, list) or len(owner_ids) != owners:
                raise ValueError("native owner_ids disagrees with owner_count")
            for owner_id in owner_ids:
                _nonempty(owner_id, "owner_ids member")
            if len(set(owner_ids)) != owners:
                raise ValueError("duplicate native owner IDs")
            witnesses = node.get("witnesses")
            if not isinstance(witnesses, list) or len(witnesses) != count:
                raise ValueError("native witness list disagrees with entity_count")
            witness_ids = set()
            for witness in witnesses:
                if not isinstance(witness, dict):
                    raise ValueError("native witness must be an object")
                wid = _nonempty(witness.get("topology_id"), "witness.topology_id")
                if wid in witness_ids:
                    raise ValueError("duplicate native topology witness")
                witness_ids.add(wid)
                bounds = witness.get("bounds_mm")
                if not isinstance(bounds, list) or len(bounds) != 2:
                    raise ValueError("witness.bounds_mm must contain min/max corners")
                for corner in bounds:
                    _finite_numbers(corner, 3, "witness.bounds_mm corner")
                if any(a > b for a, b in zip(*bounds)):
                    raise ValueError("witness bounds are reversed")
            if not assembly_complete:
                presence, reason = "unknown", "assembly_capture_incomplete"
            elif len(possible) > 1:
                presence, reason = "unknown", "multiple_occurrences_require_semantic_namespaces"
            elif possible and not exact:
                presence, reason = "unknown", "source_revision_or_configuration_mismatch"
            elif not possible:
                presence, reason = "absent", "no_occurrence_in_complete_assembly"
            elif not node["generated"]:
                presence, reason = ("absent", "generator_module_disabled") if count == owners == initial == 0 else ("unknown", "disabled_module_has_witnesses")
            elif count > 0 and owner_ids == [identity[-1]] and initial > 0:
                presence, reason = "present", "native_witnesses_and_unique_occurrence"
            else:
                presence, reason = "unknown", "generated_module_has_no_unique_final_witnesses"
            nodes.append({
                "id": node.get("id"), "kind": node.get("kind"),
                "description": node.get("description"), "supports": deepcopy(node.get("supports")),
                "presence": presence,
                "evidence": {
                    "binding_reason": reason,
                    "native_source": dict(zip(_IDENTITY, identity)),
                    "generated": node["generated"], "operation": node.get("operation"),
                    "attribute_name": node.get("attribute_name"),
                    "initial_entity_count": initial, "entity_count": count, "owner_count": owners,
                    "owner_ids": deepcopy(owner_ids),
                    "witnesses": deepcopy(witnesses), "occurrences": deepcopy(possible),
                    "binding_scope": "Surviving native boundary/body witnesses; not an exact material partition",
                },
            })
    if supplemental_nodes is not None:
        if not isinstance(supplemental_nodes, list):
            raise ValueError("supplemental_nodes must be a list")
        nodes.extend(deepcopy(supplemental_nodes))
    snapshot = {
        "schema": "pruefstand.purpose/1",
        "source": {**deepcopy(assembly_source), "assembly_complete": assembly_complete,
                   "coverage": "Explicitly registered nodes in the supplied single-occurrence catalogs only"},
        "artifacts": deepcopy(artifacts), "requirements": deepcopy(requirements), "nodes": nodes,
    }
    assess_purpose(snapshot)  # Shared structural validation, including target IDs.
    return snapshot
