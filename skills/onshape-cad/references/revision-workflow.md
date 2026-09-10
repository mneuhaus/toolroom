# FeatureScript revisions and local verification

Observed with Sparky and Alternate Chute / SC15 in September 2026.
All API paths below are relative to the session bridge required by onshape-bridge.

## Source upload and consumed revision

1. Read the live source and feature parameters at the start of an edit session;
   preserve existing changes and the prior checked revision before editing.
2. Upload the Feature Studio contents, then get its feature specifications.
3. If the Part Studio custom feature uses a namespace pinned to a microversion,
   update the existing feature to `e<featureStudioId>::m<sourceMicroversionId>`
   returned by the new specification. Preserve its feature ID and current
   parameters unless the task changes them. A successful contents upload alone
   does not prove the Part Studio consumed the source.
4. Verify feature status, expected solids and affected geometry. Reuse the
   returned data; avoid repeatedly fetching the whole feature tree. Batch
   related geometric measurements into a purposeful FS evaluation.
5. Audit assembly references after identity/topology changes, then save the
   checked revision. A cached part ID without its microversion is not a valid
   geometry-cache key.

## Preserve the user's native work

Compare the live feature tree/source with the last checked baseline before
regeneration. A Part Studio may now contain user-created sketches/extrusions
after the original generated feature. Preserve their order, parameters, queries
and intended geometry. Editing the old generator and rebuilding the studio
would erase that work. Prefer an update to the affected existing feature or a
separate finishing feature after the retained base when appropriate.

For a derivative part, derive the **finished current body**, pin the source
revision and change only the requested interface. Alternate Chute's MG995 flap
retained the user's SC15 print face and section while restoring the original
MG995 coupling. A checked historical two-feature source was no longer the live
flap design. See [retrofits and variants](retrofit-and-variants.md).

Onshape can change serialized query-node IDs and import namespaces during
regeneration/renaming. Compare the actual feature definitions and constraints,
not only raw JSON equality. Record the final consumed revision and update active
generators, caches and checks together so a later rebuild does not restore an
obsolete part or use rigid-only checks for an elastic revision.

## Boolean and helper-body pitfalls

For the tested `opBoolean` intersection pattern, use the participating bodies
in `tools: qUnion([body, clippingBody])`. Subtraction uses separate targets/tools;
when the same clipping body is needed again, deliberately preserve it for that
operation. After intersection, reacquire the output query (for example from
`qCreatedBy(intersectionId, EntityType.BODY)`) and assert its expected cardinality;
do not assume the input query still resolves the surviving solid.

This also applies after subtraction/union, even with `makeRobustQuery`.
R4's tongue slots invalidated a previously resolved target. Separate the
topology-changing operations, reacquire the intended survivor after each, and
assert cardinality before the next cut. Select by feature provenance and part
role. `qEverything` is safe only in a deliberately isolated one-solid context
after helper tools are gone; it must not capture unrelated hardware bodies.

When the source compiles but a feature reports `CANNOT_RESOLVE_ENTITIES`, inspect
the failing operation/stage and target query. Fix that stage rather than
rebuilding the entire studio or silently skipping the cut.

Size split cutters to the complete intended envelope, including tabs/cams added
later. Sparky's cutter ended before an extended cam and left a real disconnected
piece. Count and locate residual solids; a tiny numerical fragment and a missed
structural piece require different responses. Any fragment cleanup should be
localized to an understood operation and magnitude, never a global small-body
filter that could remove hardware or intentional details.

Operation IDs form a hierarchy. Do not append fresh child operations to a
finalized operation branch. Queries on a parent ID can include sketch/tool
children; deleting that whole query and then deleting its sketch again can
produce a misleading deletion error. Keep helper-solid and sketch queries
separate and delete each only once.

`HTTP 200` is not a successful FS evaluation when `result` is null and notices
contain parse/runtime errors. Those evaluations consumed rate budget in this
workflow. Use small diagnostic stages and available local examples before
repeating remote attempts. The parser also tokenizes `?[` as an operator; put a
space before an array literal used as a ternary branch (`condition ? [[...]] : ...`).

## Artifacts and budgets

Preserve meter baselines from the current session; do not hard-code an old total.
Source edits and verification use different rate-limit buckets. Keep a budget
for final verification and use offline report checks after local-only changes.
Store states, caches and logs as described by the project-layout reference.

For a STEP export, save the translation job, wait for `DONE`, download its
external result as binary through the bridge, and validate the returned format.
For native renders, choose the camera for the task: in Sparky's +Y-toward-laser
frame `back` looked from the laser side. This is a coordinate-frame observation,
not a universal definition of front/back for every project.
