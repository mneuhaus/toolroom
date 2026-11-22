from __future__ import annotations

from copy import deepcopy

import pytest

from pruefstand.purpose_capture import bind_native_purposes


HASH = "0" * 64
IDENTITY = {
    "document": "doc-1",
    "microversion": "micro-1",
    "element": "element-1",
    "configuration": "default",
    "part": "part-1",
}


def native_node(
    *,
    node_id="hammer",
    supports=None,
    generated=True,
    entity_count=1.0,
    owner_count=1.0,
    initial_entity_count=1.0,
    owner_ids=None,
    witnesses=None,
):
    if supports is None:
        supports = ["req.stop"]
    if owner_ids is None:
        owner_ids = [IDENTITY["part"]] if owner_count else []
    if witnesses is None:
        witnesses = (
            [
                {
                    "topology_id": "face-1",
                    "bounds_mm": [[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]],
                }
            ]
            if entity_count
            else []
        )
    return {
        "id": node_id,
        "kind": "function",
        "description": "Actuate and stop",
        "supports": supports,
        "generated": generated,
        "operation": "ADD",
        "attribute_name": "purpose.node",
        "initial_entity_count": initial_entity_count,
        "entity_count": entity_count,
        "owner_count": owner_count,
        "owner_ids": owner_ids,
        "witnesses": witnesses,
    }


def capture(*, nodes=None, parts=None, **identity_changes):
    identity = {**IDENTITY, **identity_changes}
    return {
        "schema": "toolroom.native-purpose/1",
        **{f"source_{key}": value for key, value in identity.items()},
        "coverage": "registered R12 purpose nodes",
        "parts": [{"topology_id": identity["part"]}] if parts is None else parts,
        "nodes": [native_node()] if nodes is None else nodes,
    }


def occurrence(*, path=None, **identity_changes):
    return {
        **IDENTITY,
        **identity_changes,
        "path": ["root", "r12"] if path is None else path,
        "transform_m": [
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        ],
    }


def bind(captures=None, occurrences=None, **changes):
    arguments = {
        "captures": [capture()] if captures is None else captures,
        "occurrences": [occurrence()] if occurrences is None else occurrences,
        "assembly_source": {
            "document": "assembly-doc",
            "microversion": "assembly-micro",
            "element": "assembly-element",
            "configuration": "default",
        },
        "assembly_complete": True,
        "requirements": [
            {"id": "req.stop", "active": True, "required_nodes": ["hammer"]}
        ],
        "artifacts": [{"path": "assembly.json", "sha256": HASH}],
    }
    arguments.update(changes)
    return bind_native_purposes(**arguments)


def output_node(snapshot, node_id="hammer"):
    return next(node for node in snapshot["nodes"] if node["id"] == node_id)


def test_exact_identity_and_native_owner_bind_present():
    node = output_node(bind())

    assert node["presence"] == "present"
    assert node["evidence"]["binding_reason"] == "native_witnesses_and_unique_occurrence"
    assert node["evidence"]["owner_ids"] == [IDENTITY["part"]]
    assert node["evidence"]["occurrences"][0]["path"] == ["root", "r12"]


def test_missing_occurrence_in_complete_assembly_is_absent():
    node = output_node(bind(occurrences=[]))

    assert node["presence"] == "absent"
    assert node["evidence"]["binding_reason"] == "no_occurrence_in_complete_assembly"


def test_missing_occurrence_in_incomplete_assembly_is_unknown():
    node = output_node(bind(occurrences=[], assembly_complete=False))

    assert node["presence"] == "unknown"
    assert node["evidence"]["binding_reason"] == "assembly_capture_incomplete"


@pytest.mark.parametrize(
    "identity_change",
    [
        {"microversion": "micro-2"},
        {"configuration": "variant=B"},
    ],
)
def test_changed_source_revision_or_configuration_is_unknown(identity_change):
    node = output_node(bind(occurrences=[occurrence(**identity_change)]))

    assert node["presence"] == "unknown"
    assert node["evidence"]["binding_reason"] == "source_revision_or_configuration_mismatch"


def test_repeated_source_occurrences_need_semantic_namespace():
    occurrences = [
        occurrence(path=["root", "r12-a"]),
        occurrence(path=["root", "r12-b"]),
    ]
    node = output_node(bind(occurrences=occurrences))

    assert node["presence"] == "unknown"
    assert node["evidence"]["binding_reason"] == "multiple_occurrences_require_semantic_namespaces"
    assert len(node["evidence"]["occurrences"]) == 2


def test_duplicate_occurrence_paths_are_invalid_even_for_different_parts():
    occurrences = [
        occurrence(path=["root", "same"]),
        occurrence(path=["root", "same"], part="part-2"),
    ]

    with pytest.raises(ValueError, match="duplicate occurrence path"):
        bind(occurrences=occurrences)


def test_disabled_module_with_zero_counts_and_no_owner_ids_is_absent():
    disabled = native_node(
        generated=False,
        entity_count=0.0,
        owner_count=0.0,
        initial_entity_count=0.0,
        owner_ids=[],
        witnesses=[],
    )
    node = output_node(bind(captures=[capture(nodes=[disabled])]))

    assert node["presence"] == "absent"
    assert node["evidence"]["binding_reason"] == "generator_module_disabled"
    assert node["evidence"]["owner_ids"] == []


def test_generated_module_that_lost_final_witnesses_is_unknown():
    lost = native_node(
        generated=True,
        entity_count=0.0,
        owner_count=0.0,
        initial_entity_count=1.0,
        owner_ids=[],
        witnesses=[],
    )
    node = output_node(bind(captures=[capture(nodes=[lost])]))

    assert node["presence"] == "unknown"
    assert node["evidence"]["binding_reason"] == "generated_module_has_no_unique_final_witnesses"


def test_witness_owned_by_another_part_is_unknown():
    wrong_owner = native_node(owner_ids=["part-other"])
    node = output_node(bind(captures=[capture(nodes=[wrong_owner])]))

    assert node["presence"] == "unknown"
    assert node["evidence"]["owner_ids"] == ["part-other"]


@pytest.mark.parametrize(
    "parts",
    [
        [],
        [{"topology_id": IDENTITY["part"]}, {"topology_id": "part-2"}],
        [{"topology_id": "wrong-part"}],
        [None],
    ],
)
def test_capture_requires_one_explicitly_identified_solid(parts):
    with pytest.raises(ValueError, match="one explicitly identified solid"):
        bind(captures=[capture(parts=parts)])


@pytest.mark.parametrize("field,value", [("entity_count", -1.0), ("owner_count", 1.5), ("initial_entity_count", True)])
def test_malformed_feature_script_counts_are_rejected(field, value):
    bad = native_node()
    bad[field] = value

    with pytest.raises(ValueError, match="nonnegative integer count"):
        bind(captures=[capture(nodes=[bad])])


@pytest.mark.parametrize(
    "bounds",
    [
        [[0.0, 0.0, 0.0]],
        [[0.0, 0.0, 0.0], [1.0, float("inf"), 3.0]],
        [[1.0, 0.0, 0.0], [0.0, 2.0, 3.0]],
    ],
)
def test_malformed_or_reversed_witness_bounds_are_rejected(bounds):
    bad = native_node(
        witnesses=[{"topology_id": "face-1", "bounds_mm": bounds}]
    )

    with pytest.raises(ValueError, match="bounds|finite numbers"):
        bind(captures=[capture(nodes=[bad])])


@pytest.mark.parametrize("owner_ids", [None, "part-1", ["part-1", "part-1"]])
def test_owner_ids_must_be_unique_list_matching_owner_count(owner_ids):
    bad = native_node(owner_ids=[])
    bad["owner_ids"] = owner_ids

    with pytest.raises(ValueError, match="owner"):
        bind(captures=[capture(nodes=[bad])])


def test_duplicate_catalog_ids_are_rejected_by_shared_validation():
    with pytest.raises(ValueError, match="duplicate node id"):
        bind(captures=[capture(), capture()])


def test_undeclared_catalog_support_target_is_rejected_by_shared_validation():
    bad = native_node(supports=["req.not-declared"])

    with pytest.raises(ValueError, match="undeclared targets"):
        bind(captures=[capture(nodes=[bad])])


def test_binding_does_not_mutate_any_input_and_output_is_detached():
    captures = [capture()]
    occurrences = [occurrence()]
    assembly_source = {
        "document": "assembly-doc",
        "microversion": "assembly-micro",
        "element": "assembly-element",
        "configuration": "default",
    }
    requirements = [{"id": "req.stop", "active": True, "required_nodes": ["hammer"]}]
    artifacts = [{"path": "assembly.json", "sha256": HASH}]
    inputs = (captures, occurrences, assembly_source, requirements, artifacts)
    before = deepcopy(inputs)

    result = bind_native_purposes(
        captures,
        occurrences,
        assembly_source=assembly_source,
        assembly_complete=True,
        requirements=requirements,
        artifacts=artifacts,
    )

    assert inputs == before
    result["nodes"][0]["supports"].append("changed")
    result["nodes"][0]["evidence"]["witnesses"][0]["bounds_mm"][0][0] = 99.0
    result["nodes"][0]["evidence"]["occurrences"][0]["path"].append("changed")
    result["source"]["document"] = "changed"
    result["requirements"][0]["active"] = False
    result["artifacts"][0]["path"] = "changed"
    assert inputs == before


def test_external_support_joins_native_dependency_graph_without_mutating_input():
    extra = [{"id": "external.frame", "kind": "function", "description": "Captured beam",
              "supports": ["req.stop"], "presence": "present",
              "evidence": {"source": "separate complete assembly capture"}}]
    before = deepcopy(extra)
    result = bind(captures=[capture(nodes=[native_node(supports=["external.frame"])])],
                  supplemental_nodes=extra)
    assert output_node(result)["supports"] == ["external.frame"]
    extra[0]["presence"] = "absent"
    assert output_node(result, "external.frame") == before[0]


def test_absent_external_support_does_not_create_a_rooted_native_node():
    from pruefstand.purpose import assess_purpose
    result = bind(captures=[capture(nodes=[native_node(supports=["external.frame"])])],
                  supplemental_nodes=[{"id": "external.frame", "kind": "function",
                    "description": "Missing beam", "supports": ["req.stop"],
                    "presence": "absent", "evidence": {"complete_context": True}}])
    report = assess_purpose(result)
    assert next(n for n in report["nodes"] if n["id"] == "hammer")["classification"] == "ORPHAN"


def test_supplemental_node_cannot_replace_native_evidence_with_duplicate_id():
    with pytest.raises(ValueError):
        bind(supplemental_nodes=[{"id": "hammer", "kind": "function", "description": "Spoof",
            "supports": ["req.stop"], "presence": "present", "evidence": {}}])


def test_supplemental_nodes_are_validated_by_the_shared_contract():
    with pytest.raises(ValueError):
        bind(supplemental_nodes={})
    with pytest.raises(ValueError):
        bind(supplemental_nodes=[{"id": "invalid"}])
