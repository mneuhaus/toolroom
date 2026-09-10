# OrcaSlicer / Bambu Studio preparation and review

Use when preparing printable CAD outputs or interpreting a slicer/strength
report. Observed in September 2026 with Sparky's A1 / Bambu Studio / PLA Matte
and Alternate Chute's OrcaSlicer / Trident comparison profiles. Recheck the
installed profiles and current user request; none is a global machine/material
default. Some project profiles were assumptions, not confirmed physical printers.

## Preserve the actual machine profile

Bambu profile sets can use ordered `include[]` templates in addition to `inherits`.
An inherits-only flattener produced plausible generic settings while dropping the
A1-specific start sequence. Resolve dependencies recursively, with cycle/missing
file diagnostics: inherited settings, includes in their declared order, the
profile's own settings, then deliberate task overrides. Preserve the slicer's
machine identity/compatibility handling; do not let template metadata select a
different machine. Validate the resolved values against the installed templates.

The shared `fusion-khana/tools/sliceability.py` flattener historically handled
only `inherits`. Check its current implementation before reuse. A tested adapter
for the includes-based Bambu profiles is in
`~/Workspace/cad/spar-key-z-axis/scripts/print-r7/prepare-plate.py`.
Its printer settings belong to that project; reuse the resolution logic, not its
hard-coded machine/material or API-meter values.

Inspect the exported 3MF, not only the UI dropdown: printer/nozzle, filament,
build-plate type, temperatures, real machine-specific start/end G-code, model
count, plate count, outside-bed flags, estimates and preview. Do not insert an
A1 G-code fragment into a different machine's file. Resolve intentional preset
overrides such as the selected bed explicitly.

Do not silently drop a missing inherited preset. Resolve it against the installed
profile tree, preserve the child's overrides, and record any chosen replacement.
Funnel Guide R4's old `Prusa Generic PLA` basis was missing; the recorded fallback
was `Generic PLA @System`. That is a project-specific resolution, not a universal
mapping. A newly confirmed PLA requirement takes precedence over an earlier ASA
comparison profile; it does not also confirm the filament brand or printer.

## Geometry provenance and print orientation

Export the changed parts from the checked CAD revision. Confirm units for the
particular endpoint (the Onshape tessellated-facet coordinates used here were in
meters and required ×1000); do not infer units solely from an STL extension.
Check watertight positive-volume meshes and agreement with native CAD volume
within a documented tessellation tolerance. Store the source revision, transforms,
part IDs and file hashes with the exports.

Use a proper rotation for print orientation (orthonormal, determinant +1), not
an accidental reflection. Translate the resulting lowest surface to bed Z=0
and check the footprint and protrusions. Verify 3MF archive integrity and build
items, not just mesh object count: one object can have multiple instances.
For an identical left/right part, state assembly quantity separately from the
number actually placed on the exported plate.

Pick bed faces using the final geometry, including bosses, registration bars,
recesses and stepped mating faces. A visually flat plate may actually stand on a
small protrusion. Inspect required supports and their removal from fitting faces;
a CAD support/strength heuristic is not a printed-load validation.

Report replacement parts relative to the user's actual printed revision. Count
printed solids independently from reference hardware. Preserve known material,
printer and readiness answers for the authorized task rather than asking again.

## Support enabled is not support generated

An Orca report's `support_used: "true"` can describe an enabled setting even
when the sliced model uses **0 mm³** of support. Inspect the generated extrusion
paths, including support interfaces, and report actual material volume with
units. Respect extrusion modes and exclude travel/retraction from material sums.
Track M82/M83/G92 and retraction debt: positive E used to restore a retract is
not deposited material. Count extrusion on actual XY paths in model layers,
including G2/G3 arcs, and exclude startup/end purge. Cross-check totals against
filament mass and density; do not trust a header unit when those disagree.
Cross-check the layer preview; do not claim zero supports solely from a profile
flag or a geometric overhang score. Time and mass remain slicer estimates for
the recorded printer/material/settings.

## A bridge-labelled path is not its unsupported span

The slicer can label a long solid-fill line above infill as `Bridge`. In Sparky,
an 87.7 mm path crossed supporting gyroid; comparison with the preceding layer
showed gaps under 2.6 mm among the 20 longest flagged paths. That did not prove
all other paths safe or certify the part's strength.

For a suspicious report, locate the layer, object and actual G-code segment.
Inspect support/infill underneath before concluding that the entire line spans
air. A targeted previous-layer coverage check can help; document bead-width,
layer/support-distance assumptions and which paths were sampled. Respect G-code
coordinate/extrusion modes when parsing. Do not globally suppress bridge warnings.
Include the configured support top gap: with 0.2-mm layers and a 0.2-mm gap,
a bridge at Z3.2 can be supported by interface paths at Z2.8 while Z3.0 is
intentionally empty. Count only actual support at that extra gap, not arbitrary
lower model geometry. Inspect interface spacing and direction: a sparse interface
parallel to a long bridge can leave long strips poorly supported. Consider denser
contact layers for stepped fitting surfaces, then reslice and recheck their
removability and coverage. Do not merely increase a verification tolerance.

Sparky R11 used three dense top-interface layers (spacing 0, top gap 0.2 mm).
Its final longest 20 Bridge paths per plate had uncovered segments below 2.77 mm;
these are project observations, not universal bridge limits. The reusable parsing
and targeted coverage example is `spar-key-z-axis/scripts/r11/check-print-paths.py`
in the CAD workspace. The earlier R7 checker did not handle all extrusion modes.

## Print status and review

Preparing or opening a plate, sending a job and observing an active print are
separate events. Report only the event verified. Reuse explicit authorization
already given for the current job; preparation alone does not authorize a new
physical print. If desktop capture is unavailable or the custom UI has no usable
labels, do not guess coordinates or claim a button worked. Finish the reviewable
file and state the specific remaining device/UI limitation.
