# Purpose dependency reports

`pruefstand.purpose` checks whether each declared, present CAD node has a declared
path to an active requirement. It is an offline consistency check for metadata
emitted with generated geometry. It does not infer intent from shape.

## Snapshot

The input schema is `pruefstand.purpose/1`. A snapshot contains an immutable source
microversion, an explicit coverage statement, at least one locally hashed capture
artifact, requirements, and semantic nodes. Node edges point from a contributing
node to the node or requirement it supports. Node IDs remain semantic identifiers;
snapshot topology IDs belong in the free-form `evidence` object.

```json
{
  "schema": "pruefstand.purpose/1",
  "source": {"microversion": "immutable-source", "coverage": "declared nodes only"},
  "artifacts": [{"path": "assembly.json", "sha256": "64 lowercase hex characters"}],
  "requirements": [{"id": "req.stop", "active": true, "required_nodes": ["hammer"]}],
  "nodes": [
    {
      "id": "hammer",
      "kind": "function",
      "description": "Actuate and stop",
      "supports": ["req.stop"],
      "presence": "present",
      "evidence": {"occurrence": "path", "faces": ["snapshot-id"]}
    },
    {
      "id": "seat",
      "kind": "material",
      "description": "Locate hammer",
      "supports": ["hammer"],
      "presence": "present",
      "evidence": {}
    }
  ]
}
```

Kinds are `function`, `material`, and `interface`. Presence is `present`, `absent`,
or `unknown`. An absent feature stays in the catalog with `presence: "absent"`.
Requirements may include a descriptive `description`; source and evidence objects
may carry further descriptive metadata. Other unknown schema keys are rejected.

`load_purpose_snapshot(path)` validates the schema and verifies each artifact hash.
Artifact paths must resolve within the snapshot directory, including through
symlinks. `assess_purpose(snapshot)` validates an in-memory snapshot but cannot claim
that artifact bytes were verified because it has no trusted snapshot directory.

## Classification

Every node receives one classification:

- `ABSENT`: explicitly absent from the captured geometry or assembly.
- `ROOTED`: at least one path through present nodes reaches an active requirement.
- `ORPHAN`: present, but every declared path ends at an absent node, an inactive
  requirement, a dead end, or an unrooted cycle.
- `UNKNOWN`: its own presence is unknown, or every known live route fails while at
  least one possible route crosses an unknown node.

Dependencies are alternatives for justification: one rooted path is enough.
Inactive requirements provide no root. Present cycles are reported; a cycle is
rooted only when it has a present path to an active requirement. Required nodes of
active requirements produce separate findings when absent or unknown.

The report schema is `pruefstand.purpose-report/1`. It retains source evidence,
root paths or causal reasons, findings, cycles, coverage, scope, and counts. Status
precedence is `incomplete`, then `review`, then `no_findings`. Unknown state and an
empty scoped node catalog are incomplete. Known orphans and absent required nodes
need review.

## Command line

Run the checker from the Prüfstand project:

```sh
uv run python -m pruefstand.purpose purpose.json --output purpose-report.json
```

Without `--output`, JSON is written to standard output. Exit codes are 0 for
`no_findings`, 1 for `review`, and 2 for `incomplete`. Invalid JSON, schema errors,
unsafe artifact paths, missing artifacts, and hash mismatches produce an incomplete
JSON report and exit 2. Library calls raise `ValueError` for those errors.

The result covers declared dependencies only. A rooted path does not prove geometry,
physical function, strength, requirement satisfaction, or permission to remove
material.

## Generate the declarations with FeatureScript

Include [purpose.fs](../featurescript/purpose.fs) after your standard-library imports.
Register a semantic node at the operation that creates its geometry. Keep requirements
in an independent project specification. Prefix IDs with the functional module or
instance namespace; duplicate IDs fail regeneration instead of merging accidentally.

```javascript
declarePurpose(context, {
    "id" : "drive.seat", "kind" : "material",
    "description" : "Locate the hammer and transfer its load",
    "supports" : ["drive.hammer"], "generated" : true
}, qOwnedByBody(seat, EntityType.FACE));
```

The helper records the declaration in a context variable and attaches a separately
named attribute for each purpose. Register additive faces before union, and cut
interface faces after their Boolean operation. A generated node with no initial
geometry fails regeneration. A deliberately disabled module registers the same
catalog with `generated: false` and `qNothing()`; it does not silently disappear.

Place exclusively owned additions and cuts in the same generator function and guard
the whole group with one enable condition. That ownership prevents a disabled
function from leaving its local support geometry behind. The graph then catches a
different failure: a consumer removed later from the assembly while its support
still exists. Shared supports need multiple purpose edges and an explicit shared
owner; do not delete them just because one consumer disappears. Geometric material,
interfaces such as pockets, and whole functional components are separate node kinds.
An aesthetic purpose can be an independently declared requirement too.

Execute [capture-purpose.fs](../featurescript/capture-purpose.fs) once per immutable
source Part Studio through the project's approved adapter. It is an API evaluation
lambda, not an additional modeling feature. Use a versioned API that your decoder
supports. The validated prototype uses `/api/v8/partstudios/.../featurescript` with
`{"script": "..."}`; `queries: {}` was rejected by an unversioned endpoint. Check
FeatureScript error notices as well as HTTP status. Cache the raw response, decoded
capture, script hash, source and complete assembly before running tests.

The final capture contains surviving topology IDs, owner body IDs and local bounding
boxes. These IDs are witnesses for that microversion, not permanent semantic names.
Named attributes may propagate across splits and unions; a surviving face can span
more than the original added material. This is a boundary witness, **not an exact
volume partition**. If a generated node loses its witnesses, report unknown.
Onshape documents the attribute propagation and API query conversion in its
[FeatureScript library](https://cad.onshape.com/FsDoc/library.html#module-attributes.fs)
and [evaluation guide](https://onshape-public.github.io/docs/api-adv/fs/).

## Bind the native capture to actual occurrences

`pruefstand.purpose_capture.bind_native_purposes` is an offline adapter. Supply decoded
native captures enriched with `source_document`, `source_microversion`,
`source_element`, `source_configuration` and `source_part`. Supply flattened assembly
occurrences with those identity fields without the `source_` prefix, a full `path`
and a 16-number `transform_m`. Also supply `assembly_source`, `assembly_complete`,
independent `requirements` and hashed local `artifacts`.

The first adapter deliberately supports one solid per captured Part Studio and a
single occurrence per semantic catalog. Exact source identity, one occurrence and
surviving witnesses owned by that solid establish presence. A complete assembly
with no such source part establishes absence. An incomplete assembly, changed
revision/configuration, multiple occurrences or unresolved final ownership produces
unknown. Hidden instances still exist. Suppression or selection must not be confused
with a complete assembly capture. Multiple instances need separately scoped semantic
catalogs and explicit cross-instance dependencies before extending this adapter.

Write the returned snapshot, then use `load_purpose_snapshot` to verify artifact
bytes and `assess_purpose` to obtain the report. A pytest requirement can simply
assert `report["status"] == "no_findings"` for this metadata check; keep geometric
clearance, motion and physical function tests alongside it. For a native mutation
fixture that removes a consumer, assert its specific orphan and missing-required-node
findings instead of accepting any failure.

### Native qualification

The R12 hammer-mount prototype qualified this route on three complete native assembly
captures: normal 37-part drive, deliberately missing hammer with retained mount,
and a disabled mount/hammer control. The finished rotor retained 5 neck, 2 seat and
4 pocket face witnesses, and the hammer retained one body witness. The missing
hammer produced three orphan nodes and one missing required node; the deliberately
disabled inactive module produced no orphan. The latter is a test fixture, not an
approved nonfunctional design. Other parts remain outside the declared scope.

Project source and raw evidence: `distributor-printed-layer/bottom-drive-purpose-2026-09-19`
in the originating CAD workspace. Its measured dimensions and design authority stay
there; the generic helper and checker do not infer manufacturing suitability.

## Full assembly coverage and external supports

Use [purpose coverage](purpose-coverage.md) alongside reachability. A rooted graph can contain only a small subset of an assembly; it does not establish that every occurrence, generator contribution or raw finding was reviewed. Build the expected census independently from the captured assembly and reviewed generator, then bind it to source/artifact hashes. Keep unresolved findings open even when their parent feature has a declared function.

`bind_native_purposes(..., supplemental_nodes=[...])` permits separately evidenced purchased occurrences and external supports to join the same graph. The caller owns their presence/evidence; this parameter does not infer them from native witnesses. Duplicate IDs and malformed nodes are rejected by the shared contract. A support connects toward its beneficiary: a motor web supports its motor plate, whose purpose depends on the motor. An external beam contact alone must not justify the web after the motor function is removed. Labels likewise depend on the labelled component.

Body attributes establish ownership of a reviewed source cohort, not an exact material partition. Do not present all-body attributes as independent face/volume witnesses for every contributing operation.
