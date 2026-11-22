# What a check actually establishes

The framework retains several kinds of evidence side by side. One overall green status would hide the different questions they answer.

| Evidence | Establishes | Still unresolved |
| --- | --- | --- |
| Native CAD geometry | Bodies, dimensions, mating faces and affected interfaces | Printing deviations and real load capacity |
| Assembly and motion | Inspected insertion paths, tool corridors and motion poses | Unchecked poses, actual friction and handling |
| Mesh screening | Sampled wall thicknesses, body integrity and a defined print pose | Small missed details and actual extrusion paths |
| Slicer and layers | Material deposition for the specific machine/material profile | Printer condition and real material behaviour |
| Simulation | Behaviour of the defined model under its assumptions | Unmodelled effects and physical calibration |
| Physical experiment | Measurements on the actual manufactured specimen | Other revisions, processes or untested load cases |

## Result states

The shared geometry checkers use `no_findings`, `review` and `incomplete`, with exit codes 0, 1 and 2. “Not run” is a separate documentation state and never a success.

`no_findings` means no issue was found within the documented inspection scope. Failed rays or an interrupted analysis leave the result `incomplete`, even if no thin wall had been found beforehand.

## A traceable report

A report identifies the input file and hash, source and revision, selected orientation, process profile, tool version, actual inspection values, raw findings and limitations. Justified exceptions remain visible. A thin structural plate must not automatically be exempted as a decorative colour layer.

## Choosing and reusing checks

Define the evidence required by the requested deliverable and the changed behaviour. A new joint needs its mating geometry and assembly path assessed; repacking approved meshes needs source/pose preservation and the final print paths checked. Repacking alone does not invalidate a prior mechanical review.

For changed native geometry, inspect feature status, expected solids, geometry validity and mating interference. Bind exports to that revision and record assembly-to-print transforms. For sampled assembly or removal paths, retain the sampling resolution and failed poses; a final-position check cannot replace the path check.

Reuse evidence only while its relevant source, revision, pose, profile and tool assumptions still hold. After a change, rerun the affected checks. Broaden inspection when a failure, changed assumption or unresolved concern warrants it; an extra handoff or renamed copy of identical bytes is not itself a new engineering test.

Assign each critical decision an accountable reviewer. Automated checks, routine preparation and critical review answer different questions; the lead inspects the evidence and findings without automatically repeating the worker's whole execution. Preserve actual failures and missing work. Acceptance of a test-print file may leave physical retention or lifetime unmeasured, and must say so.

## Concrete failure cases from the projects

- A narrow free-standing underside needs an anchor. Small width alone does not make it a printable lip.
- A part that fits only after a quarter-turn does not fit in its declared print pose.
- Enabling support does not prove that support was actually generated.
- A long segment labelled “Bridge” may partly rest on infill; its length is not automatically the unsupported span.
- A bearing can be collision-free in its final pose yet impossible to insert as a complete purchased component.
- A PDF upload may report success even though its binary data changed.

The [checker lab](../../labs/checker-lab/README.md) contains locally generated inputs and actual results from the consolidated mesh checker.
