"""Assess whether a declared catalog has complete purpose-review coverage.

The checker only relates declared catalog rows to classifications in an existing
purpose report.  It does not inspect artifact bytes, infer necessity from geometry,
or approve physical behaviour or material removal.
"""
from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from typing import Any


CATALOG_SCHEMA = "pruefstand.purpose-coverage/1"
PURPOSE_REPORT_SCHEMA = "pruefstand.purpose-report/1"
REPORT_SCHEMA = "pruefstand.purpose-coverage-report/1"

_ROOT_KEYS = {"schema", "source", "expected", "reviews"}
_EXPECTED_KEYS = {"id", "kind", "source"}
_REVIEW_KEYS = {"id", "decision", "purpose_nodes", "reason", "evidence"}
_KINDS = {"occurrence", "contribution", "finding"}
_DECISIONS = {"explained", "changed", "open"}
_CLASSIFICATIONS = {"ABSENT", "ROOTED", "ORPHAN", "UNKNOWN"}
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


def _json_compatible(value: Any, where: str) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{where} must contain JSON-compatible finite values: {exc}") from exc


def _hash(value: Any, where: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != _HASH_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{where} must be 64 lowercase hexadecimal characters")
    return value


def _validate_catalog(value: Any) -> tuple[dict, list[dict], dict[str, dict]]:
    catalog = _mapping(value, "catalog")
    _json_compatible(catalog, "catalog")
    _keys(catalog, _ROOT_KEYS, _ROOT_KEYS, "catalog")
    if catalog["schema"] != CATALOG_SCHEMA:
        raise ValueError(
            f"catalog.schema must be {CATALOG_SCHEMA!r}, got {catalog['schema']!r}"
        )

    source = _mapping(catalog["source"], "catalog.source")
    for name in ("microversion", "assembly_sha256", "generator_sha256"):
        if name not in source:
            raise ValueError(f"catalog.source is missing required key: {name!r}")
    _identifier(source["microversion"], "catalog.source.microversion")
    _hash(source["assembly_sha256"], "catalog.source.assembly_sha256")
    _hash(source["generator_sha256"], "catalog.source.generator_sha256")

    expected = _list(catalog["expected"], "catalog.expected")
    if not expected:
        raise ValueError("catalog.expected must contain at least one item")
    expected_ids: set[str] = set()
    for index, raw_item in enumerate(expected):
        where = f"catalog.expected[{index}]"
        item = _mapping(raw_item, where)
        _keys(item, _EXPECTED_KEYS, _EXPECTED_KEYS, where)
        item_id = _identifier(item["id"], f"{where}.id")
        if item_id in expected_ids:
            raise ValueError(f"duplicate expected id: {item_id!r}")
        expected_ids.add(item_id)
        if not isinstance(item["kind"], str) or item["kind"] not in _KINDS:
            raise ValueError(f"{where}.kind must be one of {sorted(_KINDS)}")
        descriptive_source = _mapping(item["source"], f"{where}.source")
        if not descriptive_source:
            raise ValueError(f"{where}.source must be a nonempty descriptive object")

    reviews = _list(catalog["reviews"], "catalog.reviews")
    reviews_by_id: dict[str, dict] = {}
    for index, raw_review in enumerate(reviews):
        where = f"catalog.reviews[{index}]"
        review = _mapping(raw_review, where)
        _keys(review, _REVIEW_KEYS, _REVIEW_KEYS, where)
        review_id = _identifier(review["id"], f"{where}.id")
        if review_id in reviews_by_id:
            raise ValueError(f"duplicate review id: {review_id!r}")
        if review_id not in expected_ids:
            raise ValueError(f"review id is not declared in catalog.expected: {review_id!r}")
        reviews_by_id[review_id] = review

        decision = review["decision"]
        if not isinstance(decision, str) or decision not in _DECISIONS:
            raise ValueError(f"{where}.decision must be one of {sorted(_DECISIONS)}")
        purpose_nodes = _string_list(review["purpose_nodes"], f"{where}.purpose_nodes")
        reason = review["reason"]
        if not isinstance(reason, str):
            raise ValueError(f"{where}.reason must be a string")
        evidence = _string_list(review["evidence"], f"{where}.evidence")
        if not reason.strip():
            raise ValueError(f"{where}.reason must be nonempty")
        if decision in {"explained", "changed"}:
            if not purpose_nodes:
                raise ValueError(f"{where}.purpose_nodes must be nonempty for {decision!r}")
            if not evidence:
                raise ValueError(f"{where}.evidence must be nonempty for {decision!r}")

    kinds_by_id = {item["id"]: item["kind"] for item in expected}
    for review_id, review in reviews_by_id.items():
        if review["decision"] == "changed" and kinds_by_id[review_id] != "finding":
            raise ValueError("decision 'changed' is permissible only for finding items")

    return catalog, expected, reviews_by_id


def _validate_purpose_report(value: Any) -> dict[str, str]:
    report = _mapping(value, "purpose_report")
    _json_compatible(report, "purpose_report")
    if report.get("schema") != PURPOSE_REPORT_SCHEMA:
        raise ValueError(
            "purpose_report.schema must be "
            f"{PURPOSE_REPORT_SCHEMA!r}, got {report.get('schema')!r}"
        )
    if "nodes" not in report:
        raise ValueError("purpose_report is missing required key: 'nodes'")

    classifications: dict[str, str] = {}
    for index, raw_node in enumerate(_list(report["nodes"], "purpose_report.nodes")):
        where = f"purpose_report.nodes[{index}]"
        node = _mapping(raw_node, where)
        if "id" not in node or "classification" not in node:
            raise ValueError(f"{where} must contain id and classification")
        node_id = _identifier(node["id"], f"{where}.id")
        if node_id in classifications:
            raise ValueError(f"duplicate purpose node id: {node_id!r}")
        classification = node["classification"]
        if not isinstance(classification, str) or classification not in _CLASSIFICATIONS:
            raise ValueError(
                f"{where}.classification must be one of {sorted(_CLASSIFICATIONS)}"
            )
        classifications[node_id] = classification
    return classifications


def _finding(code: str, item_id: str, status: str, **details: Any) -> dict:
    return {"code": code, "item": item_id, "status": status, **details}


def assess_purpose_coverage(catalog: dict, purpose_report: dict) -> dict:
    """Validate and assess declared catalog coverage against purpose classifications.

    The function is pure: it performs no I/O and does not mutate either input.
    """
    catalog, expected, reviews_by_id = _validate_catalog(catalog)
    classifications = _validate_purpose_report(purpose_report)

    for review_id, review in reviews_by_id.items():
        unknown = set(review["purpose_nodes"]) - set(classifications)
        if unknown:
            raise ValueError(
                f"review {review_id!r} references unknown purpose nodes: {sorted(unknown)}"
            )

    findings: list[dict] = []
    items: list[dict] = []
    kind_counts = Counter(item["kind"] for item in expected)
    decision_counts = Counter(review["decision"] for review in reviews_by_id.values())
    decision_counts["missing"] = len(expected) - len(reviews_by_id)

    for expected_item in expected:
        item_id = expected_item["id"]
        kind = expected_item["kind"]
        review = reviews_by_id.get(item_id)
        item_findings: list[dict] = []

        if review is None:
            item_findings.append(_finding("missing_review", item_id, "incomplete"))
        elif review["decision"] == "open":
            item_findings.append(_finding("open_review", item_id, "incomplete"))
        else:
            for node_id in review["purpose_nodes"]:
                classification = classifications[node_id]
                if classification == "UNKNOWN":
                    item_findings.append(
                        _finding(
                            "linked_purpose_unknown",
                            item_id,
                            "incomplete",
                            node=node_id,
                        )
                    )
                elif classification == "ORPHAN":
                    item_findings.append(
                        _finding("linked_purpose_orphan", item_id, "review", node=node_id)
                    )
                elif classification == "ABSENT" and review["decision"] != "changed":
                    item_findings.append(
                        _finding(
                            "linked_purpose_absent",
                            item_id,
                            "incomplete",
                            node=node_id,
                        )
                    )

        statuses = {finding["status"] for finding in item_findings}
        state = (
            "incomplete"
            if "incomplete" in statuses
            else "review"
            if "review" in statuses
            else "covered"
        )
        entry = {
            "id": item_id,
            "kind": kind,
            "state": state,
            "source": deepcopy(expected_item["source"]),
            "review": deepcopy(review) if review is not None else None,
        }
        items.append(entry)
        findings.extend(item_findings)

    statuses = {finding["status"] for finding in findings}
    status = (
        "incomplete"
        if "incomplete" in statuses
        else "review"
        if "review" in statuses
        else "no_findings"
    )
    state_counts = Counter(item["state"] for item in items)
    return {
        "schema": REPORT_SCHEMA,
        "source": deepcopy(catalog["source"]),
        "status": status,
        "complete": status == "no_findings",
        "counts": {
            "expected": len(expected),
            "reviewed": len(reviews_by_id),
            "findings": len(findings),
            "by_kind": {kind: kind_counts[kind] for kind in sorted(_KINDS)},
            "by_decision": {
                decision: decision_counts[decision]
                for decision in ["explained", "changed", "open", "missing"]
            },
            "by_state": {
                state: state_counts[state]
                for state in ["covered", "review", "incomplete"]
            },
        },
        "items": items,
        "findings": findings,
        "scope": {
            "coverage": "declared expected items and supplied reviews only",
            "purpose": "linked node classifications from the supplied purpose report only",
            "artifact_bytes": "not verified",
            "geometry_and_physical_function": "not proved",
            "material_necessity": "not proved",
            "automatic_deletion": "not performed",
        },
    }
