from __future__ import annotations

from copy import deepcopy

import pytest

from pruefstand.purpose_coverage import assess_purpose_coverage


HASH = "a" * 64


def expected(item_id, kind):
    return {"id": item_id, "kind": kind, "source": {"path": f"assembly/{item_id}"}}


def review(item_id, decision="explained", nodes=None, reason="reviewed", evidence=None):
    return {
        "id": item_id,
        "decision": decision,
        "purpose_nodes": nodes if nodes is not None else [f"purpose.{item_id}"],
        "reason": reason,
        "evidence": evidence if evidence is not None else [f"evidence:{item_id}"],
    }


def catalog(expected_items=None, reviews=None):
    expected_items = expected_items or [
        expected("motor", "occurrence"),
        expected("drive", "contribution"),
        expected("legacy-cut", "finding"),
    ]
    return {
        "schema": "pruefstand.purpose-coverage/1",
        "source": {
            "microversion": "immutable-revision",
            "assembly_sha256": HASH,
            "generator_sha256": "b" * 64,
        },
        "expected": expected_items,
        "reviews": reviews
        if reviews is not None
        else [
            review("motor"),
            review("drive"),
            review("legacy-cut", "changed", ["purpose.legacy-cut"]),
        ],
    }


def purpose_report(classifications=None):
    if classifications is None:
        classifications = {
            "purpose.motor": "ROOTED",
            "purpose.drive": "ROOTED",
            "purpose.legacy-cut": "ABSENT",
        }
    return {
        "schema": "pruefstand.purpose-report/1",
        "status": "no_findings",
        "nodes": [
            {"id": node_id, "classification": classification, "evidence": {}}
            for node_id, classification in classifications.items()
        ],
        "findings": [],
    }


def item_by_id(report):
    return {item["id"]: item for item in report["items"]}


def test_complete_assembly_group_and_changed_finding_catalog():
    report = assess_purpose_coverage(catalog(), purpose_report())

    assert report["schema"] == "pruefstand.purpose-coverage-report/1"
    assert report["status"] == "no_findings" and report["complete"] is True
    assert report["findings"] == []
    assert report["counts"]["by_kind"] == {
        "contribution": 1,
        "finding": 1,
        "occurrence": 1,
    }
    assert report["counts"]["by_decision"] == {
        "explained": 2,
        "changed": 1,
        "open": 0,
        "missing": 0,
    }
    assert set(item["state"] for item in report["items"]) == {"covered"}
    assert report["scope"]["artifact_bytes"] == "not verified"
    assert report["scope"]["material_necessity"] == "not proved"


def test_hammer_only_reviews_do_not_cover_larger_expected_drive():
    expected_items = [
        expected("hammer", "occurrence"),
        expected("seat", "contribution"),
        expected("neck", "contribution"),
        expected("pocket", "contribution"),
        expected("motor", "occurrence"),
        expected("motor-holder", "contribution"),
    ]
    reviews = [review(item["id"]) for item in expected_items[:4]]
    nodes = {f"purpose.{item['id']}": "ROOTED" for item in expected_items}

    report = assess_purpose_coverage(
        catalog(expected_items, reviews), purpose_report(nodes)
    )

    assert report["status"] == "incomplete" and report["complete"] is False
    assert report["counts"]["by_decision"]["missing"] == 2
    assert {finding["item"] for finding in report["findings"]} == {
        "motor",
        "motor-holder",
    }


@pytest.mark.parametrize("kind", ["occurrence", "contribution"])
def test_new_unreviewed_expected_item_is_incomplete(kind):
    report = assess_purpose_coverage(
        catalog([expected("new", kind)], []), purpose_report({})
    )

    assert report["status"] == "incomplete"
    assert report["findings"] == [
        {"code": "missing_review", "item": "new", "status": "incomplete"}
    ]


def test_open_finding_stays_incomplete_even_with_rooted_node():
    value = catalog(
        [expected("finding", "finding")],
        [review("finding", "open", ["purpose.finding"], evidence=[])],
    )
    report = assess_purpose_coverage(
        value, purpose_report({"purpose.finding": "ROOTED"})
    )

    assert report["status"] == "incomplete"
    assert report["findings"][0]["code"] == "open_review"
    assert item_by_id(report)["finding"]["review"]["decision"] == "open"


def test_changed_finding_may_link_absent_node_with_independent_evidence():
    value = catalog(
        [expected("removed", "finding")],
        [review("removed", "changed", ["purpose.removed"])],
    )
    report = assess_purpose_coverage(
        value, purpose_report({"purpose.removed": "ABSENT"})
    )

    assert report["status"] == "no_findings" and report["complete"] is True


@pytest.mark.parametrize("kind", ["occurrence", "contribution", "finding"])
def test_explained_absent_node_is_incomplete(kind):
    value = catalog([expected("gone", kind)], [review("gone")])
    report = assess_purpose_coverage(
        value, purpose_report({"purpose.gone": "ABSENT"})
    )

    assert report["status"] == "incomplete"
    assert report["findings"][0]["code"] == "linked_purpose_absent"


def test_unknown_is_retained_despite_alternate_rooted_node():
    value = catalog(
        [expected("mixed", "contribution")],
        [review("mixed", nodes=["purpose.good", "purpose.unknown"])],
    )
    report = assess_purpose_coverage(
        value,
        purpose_report({"purpose.good": "ROOTED", "purpose.unknown": "UNKNOWN"}),
    )

    assert report["status"] == "incomplete"
    assert report["findings"] == [
        {
            "code": "linked_purpose_unknown",
            "item": "mixed",
            "status": "incomplete",
            "node": "purpose.unknown",
        }
    ]


def test_orphan_requires_review():
    value = catalog([expected("orphan", "occurrence")], [review("orphan")])
    report = assess_purpose_coverage(
        value, purpose_report({"purpose.orphan": "ORPHAN"})
    )

    assert report["status"] == "review" and report["complete"] is False
    assert item_by_id(report)["orphan"]["state"] == "review"


def test_incomplete_precedes_review_and_all_findings_are_retained():
    value = catalog(
        [expected("mixed", "finding")],
        [review("mixed", nodes=["purpose.orphan", "purpose.unknown"])],
    )
    report = assess_purpose_coverage(
        value,
        purpose_report(
            {"purpose.orphan": "ORPHAN", "purpose.unknown": "UNKNOWN"}
        ),
    )

    assert report["status"] == "incomplete"
    assert [finding["status"] for finding in report["findings"]] == [
        "review",
        "incomplete",
    ]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.update(schema="wrong"), "catalog.schema"),
        (lambda value: value.update(extra=True), "unknown keys"),
        (lambda value: value["source"].update(microversion=""), "microversion"),
        (lambda value: value["source"].update(assembly_sha256="ABC"), "lowercase"),
        (lambda value: value.update(expected=[]), "at least one"),
        (
            lambda value: value["expected"].append(deepcopy(value["expected"][0])),
            "duplicate expected",
        ),
        (lambda value: value["expected"][0].update(kind="assembly"), "kind must be"),
        (lambda value: value["expected"][0].update(source={}), "nonempty descriptive"),
        (lambda value: value["expected"][0].update(extra=True), "unknown keys"),
        (lambda value: value["reviews"].append(deepcopy(value["reviews"][0])), "duplicate review"),
        (lambda value: value["reviews"][0].update(decision="accepted"), "decision must be"),
        (lambda value: value["reviews"][0].update(extra=True), "unknown keys"),
        (
            lambda value: value["reviews"][0].update(
                purpose_nodes=["purpose.motor"] * 2
            ),
            "duplicate",
        ),
        (lambda value: value["reviews"][0].update(evidence=["same", "same"]), "duplicate"),
    ],
)
def test_catalog_schema_failures(mutate, message):
    value = catalog()
    mutate(value)
    with pytest.raises(ValueError, match=message):
        assess_purpose_coverage(value, purpose_report())


def test_non_finite_catalog_value_is_rejected():
    value = catalog()
    value["expected"][0]["source"]["measurement"] = float("inf")
    with pytest.raises(ValueError, match="finite"):
        assess_purpose_coverage(value, purpose_report())


@pytest.mark.parametrize("field", ["reason", "evidence", "purpose_nodes"])
def test_explained_review_requires_reason_evidence_and_nodes(field):
    value = catalog()
    value["reviews"][0][field] = "" if field == "reason" else []
    with pytest.raises(ValueError, match=field):
        assess_purpose_coverage(value, purpose_report())


@pytest.mark.parametrize("field", ["reason", "evidence", "purpose_nodes"])
def test_explained_review_rejects_missing_required_field(field):
    value = catalog()
    value["reviews"][0].pop(field)
    with pytest.raises(ValueError, match="missing required keys"):
        assess_purpose_coverage(value, purpose_report())


def test_open_review_requires_reason():
    value = catalog()
    value["reviews"][0] = review("motor", "open", [], reason="", evidence=[])
    with pytest.raises(ValueError, match="reason"):
        assess_purpose_coverage(value, purpose_report())


def test_changed_decision_is_rejected_for_non_finding_item():
    value = catalog(
        [expected("motor", "occurrence")],
        [review("motor", "changed")],
    )
    with pytest.raises(ValueError, match="only for finding"):
        assess_purpose_coverage(value, purpose_report({"purpose.motor": "ABSENT"}))


def test_extra_review_id_and_unknown_purpose_node_are_rejected():
    value = catalog()
    value["reviews"][0]["id"] = "not-expected"
    with pytest.raises(ValueError, match="not declared"):
        assess_purpose_coverage(value, purpose_report())

    value = catalog()
    value["reviews"][0]["purpose_nodes"] = ["purpose.not-declared"]
    with pytest.raises(ValueError, match="unknown purpose nodes"):
        assess_purpose_coverage(value, purpose_report())


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.update(schema="wrong"), "purpose_report.schema"),
        (lambda value: value.pop("nodes"), "missing required"),
        (lambda value: value["nodes"].append(deepcopy(value["nodes"][0])), "duplicate purpose"),
        (lambda value: value["nodes"][0].update(classification="PRESENT"), "classification"),
        (lambda value: value["nodes"][0].pop("classification"), "id and classification"),
    ],
)
def test_purpose_report_schema_failures(mutate, message):
    value = purpose_report()
    mutate(value)
    with pytest.raises(ValueError, match=message):
        assess_purpose_coverage(catalog(), value)


def test_inputs_are_not_mutated_and_preserved_values_are_copied():
    catalog_value = catalog()
    purpose_value = purpose_report()
    catalog_before = deepcopy(catalog_value)
    purpose_before = deepcopy(purpose_value)

    report = assess_purpose_coverage(catalog_value, purpose_value)

    assert catalog_value == catalog_before
    assert purpose_value == purpose_before
    report["source"]["microversion"] = "changed-output"
    report["items"][0]["source"]["path"] = "changed-output"
    report["items"][0]["review"]["reason"] = "changed-output"
    assert catalog_value == catalog_before
