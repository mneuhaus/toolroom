# Existing interfaces, derived variants and identical parts

Use when porting a servo bracket/flap or replacing left/right variants with one
printable part. Lessons from Alternate Chute / SC15, September 2026. Exact
document IDs, dimensions and revision status belong in the project handoff.

## Establish the interface before adapting the silhouette

Read the intended source document/version, current target features and assembled
poses. Save source IDs/revisions and name the functional bodies. Derive/copy
without changing the shared source. A tab name or the first returned solid is
not sufficient identification of a mounting face, core or coupling.

Record hole-axis positions/directions, seating planes, available wall thickness,
servo shaft/coupling geometry and the desired load path in a documented local
frame. Keep full precision for basis vectors; use right-handed rotations for
assembly placement and export. First align the interface, then shape the printed
body. Little extensions added to compensate for the wrong pose can hide both a
gap and misaligned holes.

Preserve the real purchased servo, horn and bearing envelopes. Modify a printed
housing's oversized chamfer if needed; do not remove geometry from the reference
servo to make a test pass. Include both serial-servo plugs and cable access, not
just the case. Apply the [assembly review](../../../knowledge/construction/assembly-review.md)
to the complete installed context.

For “same flap except for the adapter”, use the user's current finished shape,
including the bed face, reinforced section and native edits. Restore the target
coupling's exact functional dimensions from its source. Keep a separate variant
where necessary, and do not replace working assembly instances unless that is
part of the requested change.

## Prove that one part works on both sides

Construct the shared contour around the actual interface symmetry, with clean
end cuts and enough material around countersinks. Intersecting a profile with
its reflection can make both ends alike but can also remove a load-bearing stop;
check the resulting function, not just the symmetric outline. Deburr the final
cut without creating thin tips or tiny notches.

Place **two instances of the same part ID** using the intended proper rotations.
Check both sets of hole axes, seating contacts, insertion/access paths, nearby
clearance and print orientation. A left-hand geometry mirrored into a right-hand
one is not yet proof that a single manufactured part can serve both positions.
For elastic guides also use the [fit and snap review](../../../knowledge/construction/fits-and-retention.md).

Native symmetric curved faces can have different triangulations. Do not require
identical triangle arrays or exactly zero mesh Boolean difference. Use native
geometry where possible; otherwise record tessellation tolerance and localized
surface-distance/volume comparisons. Investigate a discrepancy outside that
tolerance rather than broadly waiving it as “mesh noise.”

## Local geometry diagnostics

- For Manifold cross-sections, check signed area, loop winding, non-emptiness
  and kernel status before extrusion/Boolean debugging. A clockwise outer loop
  yielded an empty cross-section and `InvalidConstruction` in this workflow.
  Normalize the outer contour and hole winding for the API actually used.
- Convex-hull topology can pick up extra near-collinear vertices from numerical
  noise. Apply a documented local tolerance/collinear cleanup if needed; do not
  round the actual Onshape basis or all interface dimensions to fix it.
- A collision flag near coplanar faces needs inspection. Locate it and compare
  mesh intersection, native contacts and tessellation tolerance; a huge reported
  FCL penetration depth was not a reliable physical penetration measurement here.
- Keep local analysis modules from shadowing dependencies: a scratch `inspect.py`
  shadowed Python's standard module and broke NumPy imports. Rename the scratch
  file before treating the resulting import failure as a CAD/library defect.

## Finish the revision coherently

Audit references in all affected assemblies after publication. Onshape may have
already remapped a changed body ID; preserve valid instances and poses. Record
pre-existing legacy failures separately. Update the canonical source, consumed
revision, geometry caches, assembly manifest, variant-aware checks and exports.
Report whether the assembly is merely positioned or has actual motion mates,
and distinguish sampled mechanical travel from servo command angles.

Worked examples: `~/Workspace/cad/alternate-chute-design/system-fix/README.md`,
`mg995-flap/README.md`, `funnel-holder-r4/README.md` and `DOCUMENT_STRUCTURE.md`
within the same project.
